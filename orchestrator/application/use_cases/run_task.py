from __future__ import annotations

from pydantic import ValidationError

from orchestrator.application.dto.run_task_command import RunTaskCommand
from orchestrator.config.task_loader import TaskLoader
from orchestrator.domain.enums import Decision, RunStatus
from orchestrator.domain.models.quality_report import QualityReport
from orchestrator.domain.models.rule_proposal import RuleProposal
from orchestrator.domain.models.run_state import RunState
from orchestrator.domain.services.exceptions import MalformedReview, SafetyViolation
from orchestrator.domain.services.quality_gate import QualityGate
from orchestrator.domain.services.review_validator import ReviewValidator
from orchestrator.domain.services.rule_proposal_service import RuleProposalService
from orchestrator.domain.services.safety_policy import SafetyPolicy
from orchestrator.ports.agent_port import AgentPort
from orchestrator.ports.check_runner_port import CheckRunnerPort
from orchestrator.ports.diff_provider_port import DiffProviderPort
from orchestrator.ports.state_repository_port import StateRepositoryPort
from orchestrator.infrastructure.exceptions import InfrastructureError
from orchestrator.infrastructure.logging.phase_logger import PhaseLogger
from orchestrator.report.final_report_writer import FinalReportWriter
from orchestrator.report.rule_proposal_writer import RuleProposalWriter


class RunTaskUseCase:
    def __init__(
        self,
        task_loader: TaskLoader,
        safety_policy: SafetyPolicy,
        state_repository: StateRepositoryPort,
        agent: AgentPort,
        check_runner: CheckRunnerPort,
        review_validator: ReviewValidator,
        quality_gate: QualityGate,
        diff_provider: DiffProviderPort,
        final_report_writer: FinalReportWriter,
        rule_proposal_service: RuleProposalService | None = None,
        rule_proposal_writer: RuleProposalWriter | None = None,
        phase_logger: PhaseLogger | None = None,
    ):
        self.task_loader = task_loader
        self.safety_policy = safety_policy
        self.state_repository = state_repository
        self.agent = agent
        self.check_runner = check_runner
        self.review_validator = review_validator
        self.quality_gate = quality_gate
        self.diff_provider = diff_provider
        self.final_report_writer = final_report_writer
        self.rule_proposal_service = rule_proposal_service or RuleProposalService()
        self.rule_proposal_writer = rule_proposal_writer or RuleProposalWriter()
        self.phase_logger = phase_logger or PhaseLogger()

    def execute(self, command: RunTaskCommand) -> RunState:
        task = self.task_loader.load(command.task_path)
        state = self.state_repository.create_run(task)
        self._log_phase(state, "init", "start", task_path=command.task_path)

        try:
            self._log_phase(state, "safety", "start")
            permission, reason = self.safety_policy.precheck(task)
            state.artifacts["permission"] = permission.value
            if reason:
                state.artifacts["permission_reason"] = reason
            self.state_repository.save_state(state)
            self._log_phase(state, "safety", "end", permission=permission.value, reason=reason)
        except SafetyViolation as exc:
            state.status = RunStatus.HALTED
            state.set_phase("safety")
            reason = f"Safety precheck failed: {exc}"
            self._log_phase(state, "safety", "halt", reason=reason)
            proposal = self.rule_proposal_service.from_halt_reason(state, reason, source="safety_precheck")
            self._write_report(state, reason, rule_proposal=proposal)
            return state

        last_report: QualityReport | None = None
        while state.can_attempt():
            state.next_attempt()
            state.set_phase("code")
            self._log_phase(state, "code", "start")
            self.state_repository.save_state(state)
            try:
                self.agent.run_coder(task, state)
                self._log_phase(state, "code", "end")
            except InfrastructureError as exc:
                state.status = RunStatus.HALTED
                state.set_phase("code")
                reason = f"Agent coder failed: {exc}"
                self._log_phase(state, "code", "halt", reason=reason)
                proposal = self.rule_proposal_service.from_halt_reason(state, reason, source="agent_coder_failure")
                self._write_report(state, reason, rule_proposal=proposal)
                return state

            state.set_phase("hard_checks")
            self._log_phase(state, "hard_checks", "start")
            self.state_repository.save_state(state)
            if hasattr(self.check_runner, "state"):
                self.check_runner.state = state
            hard_result = self.check_runner.run_all(task)
            self.state_repository.save_hard_check(state, hard_result)
            self._log_phase(state, "hard_checks", "end", passed=hard_result.passed, score=hard_result.score)

            if not hard_result.passed:
                if self.quality_gate.should_halt_hard_check(hard_result, state):
                    state.status = RunStatus.HALTED
                    proposal = self.rule_proposal_service.from_hard_check_failure(state, hard_result)
                    self._log_phase(state, "hard_checks", "halt", reason=proposal.reason)
                    self._write_report(state, proposal.reason, rule_proposal=proposal)
                    return state
                state.status = RunStatus.RETRYING
                state.set_phase("fix")
                self._log_phase(state, "fix", "start", reason=hard_result.first_failure_reason())
                try:
                    self.agent.run_fixer(task, state, hard_result)
                    self._log_phase(state, "fix", "end")
                except InfrastructureError as exc:
                    state.status = RunStatus.HALTED
                    state.set_phase("fix")
                    reason = f"Agent fixer failed: {exc}"
                    self._log_phase(state, "fix", "halt", reason=reason)
                    proposal = self.rule_proposal_service.from_halt_reason(state, reason, source="agent_fixer_failure")
                    self._write_report(state, reason, rule_proposal=proposal)
                    return state
                continue

            state.set_phase("review")
            self._log_phase(state, "review", "start")
            self.state_repository.save_state(state)
            try:
                review, retry_count = self._run_review_with_retry(task, state)
                self._log_phase(state, "review", "end", retry_count=retry_count)
            except MalformedReview as exc:
                state.status = RunStatus.HALTED
                state.set_phase("review")
                reason = f"Agent reviewer failed: {exc}"
                self._log_phase(state, "review", "halt", reason=reason)
                proposal = self.rule_proposal_service.from_malformed_review(
                    state,
                    reason,
                    task.max_review_json_retries,
                )
                self._write_report(state, reason, rule_proposal=proposal)
                return state
            except InfrastructureError as exc:
                state.status = RunStatus.HALTED
                state.set_phase("review")
                reason = f"Agent reviewer failed: {exc}"
                self._log_phase(state, "review", "halt", reason=reason)
                proposal = self.rule_proposal_service.from_halt_reason(state, reason, source="agent_reviewer_failure")
                self._write_report(state, reason, rule_proposal=proposal)
                return state
            self.state_repository.save_review(state, review)

            self._log_phase(state, "quality_gate", "start")
            diff_stats = self.diff_provider.get_diff_stats(task)
            last_report = self.quality_gate.evaluate(task, state, hard_result, review, diff_stats, retry_count)
            self.state_repository.save_quality_report(state, last_report)
            self._log_phase(
                state,
                "quality_gate",
                "end",
                decision=last_report.decision,
                passed=last_report.passed,
                quality_score=last_report.quality_score,
            )

            if last_report.passed:
                state.status = RunStatus.DONE
                state.set_phase("done")
                self._log_phase(state, "done", "end", reason=last_report.reason)
                self._write_report(state, last_report.reason, last_report)
                return state

            if last_report.decision == Decision.HALT:
                state.status = RunStatus.HALTED
                state.set_phase("halt")
                proposal = self.rule_proposal_service.from_quality_report(state, last_report)
                self._log_phase(state, "halt", "end", reason=last_report.reason)
                self._write_report(state, last_report.reason, last_report, proposal)
                return state

            state.status = RunStatus.RETRYING
            state.set_phase("fix")
            self._log_phase(state, "fix", "start", reason=last_report.reason)
            try:
                self.agent.run_fixer(task, state, last_report)
                self._log_phase(state, "fix", "end")
            except InfrastructureError as exc:
                state.status = RunStatus.HALTED
                state.set_phase("fix")
                reason = f"Agent fixer failed: {exc}"
                self._log_phase(state, "fix", "halt", reason=reason)
                proposal = self.rule_proposal_service.from_halt_reason(state, reason, source="agent_fixer_failure")
                self._write_report(state, reason, rule_proposal=proposal)
                return state

        state.status = RunStatus.HALTED
        state.set_phase("halt")
        proposal = self.rule_proposal_service.from_halt_reason(state, "max_attempts_exceeded")
        self._log_phase(state, "halt", "end", reason="max_attempts_exceeded")
        self._write_report(state, "max_attempts_exceeded", last_report, proposal)
        return state

    def _run_review_with_retry(self, task, state) -> tuple[object, int]:
        raw_output = self.agent.run_reviewer(task, state)
        for retry_count in range(task.max_review_json_retries + 1):
            try:
                review = self.review_validator.parse_and_validate(raw_output, task)
                return review, retry_count
            except (MalformedReview, ValidationError):
                self.state_repository.save_malformed_review(state, retry_count + 1, raw_output)
                if retry_count == task.max_review_json_retries:
                    raise
                repair_prompt = self.review_validator.build_repair_prompt(task.task_id)
                self._log_phase(state, "review", "retry", retry_count=retry_count + 1)
                raw_output = self.agent.run_reviewer(task, state, repair_prompt=repair_prompt)
        raise MalformedReview("review_json_malformed")

    def _write_report(
        self,
        state: RunState,
        reason: str,
        quality_report: QualityReport | None = None,
        rule_proposal: RuleProposal | None = None,
    ) -> None:
        if rule_proposal:
            proposal_content = self.rule_proposal_writer.render(rule_proposal)
            self.state_repository.write_rule_proposal(state, rule_proposal, proposal_content)
        content = self.final_report_writer.render(state, reason, quality_report)
        self.state_repository.write_final_report(state, content)

    def _log_phase(self, state: RunState, phase: str, event: str, **fields: object) -> None:
        self.phase_logger.info(state, phase, event, **fields)
