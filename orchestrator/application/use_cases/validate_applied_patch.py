from __future__ import annotations

from pydantic import ValidationError

from orchestrator.config.task_loader import TaskLoader
from orchestrator.domain.enums import RunStatus
from orchestrator.domain.models.quality_report import QualityReport
from orchestrator.domain.models.run_state import RunState
from orchestrator.domain.services.exceptions import MalformedReview
from orchestrator.domain.services.quality_gate import QualityGate
from orchestrator.domain.services.review_validator import ReviewValidator
from orchestrator.infrastructure.exceptions import InfrastructureError
from orchestrator.infrastructure.git.static_diff_provider import StaticDiffProvider
from orchestrator.infrastructure.logging.phase_logger import PhaseLogger
from orchestrator.ports.agent_port import AgentPort
from orchestrator.ports.check_runner_port import CheckRunnerPort
from orchestrator.ports.diff_provider_port import DiffProviderPort
from orchestrator.ports.state_repository_port import StateRepositoryPort
from orchestrator.report.final_report_writer import FinalReportWriter


class ValidateAppliedPatchUseCase:
    """Run post-approval validation without invoking coder/fixer again."""

    def __init__(
        self,
        task_loader: TaskLoader,
        state_repository: StateRepositoryPort,
        agent: AgentPort,
        check_runner: CheckRunnerPort,
        review_validator: ReviewValidator,
        quality_gate: QualityGate,
        final_report_writer: FinalReportWriter,
        diff_provider: DiffProviderPort | None = None,
        phase_logger: PhaseLogger | None = None,
    ):
        self.task_loader = task_loader
        self.state_repository = state_repository
        self.agent = agent
        self.check_runner = check_runner
        self.review_validator = review_validator
        self.quality_gate = quality_gate
        self.diff_provider = diff_provider or StaticDiffProvider()
        self.final_report_writer = final_report_writer
        self.phase_logger = phase_logger or PhaseLogger()

    def execute(self, task_path) -> RunState:
        task = self.task_loader.load(task_path)
        state = self.state_repository.create_run(task)
        state.artifacts["validation_mode"] = "post_apply_rerun_task"
        self._log_phase(state, "init", "start", task_path=task_path, validation_mode="post_apply_rerun_task")

        state.next_attempt()
        state.set_phase("hard_checks")
        self._log_phase(state, "hard_checks", "start")
        self.state_repository.save_state(state)
        if hasattr(self.check_runner, "state"):
            self.check_runner.state = state
        hard_result = self.check_runner.run_all(task)
        self.state_repository.save_hard_check(state, hard_result)
        self._log_phase(state, "hard_checks", "end", passed=hard_result.passed, score=hard_result.score)

        if not hard_result.passed:
            state.status = RunStatus.HALTED
            state.set_phase("halt")
            reason = hard_result.first_failure_reason() or "hard checks failed"
            state.artifacts["validation_reason"] = reason
            self._log_phase(state, "halt", "end", reason=reason)
            self._write_report(state, reason)
            return state

        state.set_phase("review")
        self._log_phase(state, "review", "start")
        self.state_repository.save_state(state)
        try:
            review, retry_count = self._run_review_with_retry(task, state)
            self._log_phase(state, "review", "end", retry_count=retry_count)
        except (MalformedReview, InfrastructureError) as exc:
            state.status = RunStatus.HALTED
            state.set_phase("review")
            reason = f"post-apply reviewer failed: {exc}"
            state.artifacts["validation_reason"] = reason
            self._log_phase(state, "review", "halt", reason=reason)
            self._write_report(state, reason)
            return state
        self.state_repository.save_review(state, review)

        state.set_phase("quality_gate")
        self._log_phase(state, "quality_gate", "start")
        diff_stats = self.diff_provider.get_diff_stats(task)
        report = self.quality_gate.evaluate(task, state, hard_result, review, diff_stats, retry_count)
        self.state_repository.save_quality_report(state, report)
        self._log_phase(
            state,
            "quality_gate",
            "end",
            decision=report.decision,
            passed=report.passed,
            quality_score=report.quality_score,
        )

        state.status = RunStatus.DONE if report.passed else RunStatus.HALTED
        state.set_phase("done" if report.passed else "halt")
        state.artifacts["validation_reason"] = report.reason
        self._log_phase(state, state.current_phase, "end", reason=report.reason)
        self._write_report(state, report.reason, report)
        return state

    def _run_review_with_retry(self, task, state) -> tuple[object, int]:
        raw_output = self.agent.run_reviewer(task, state)
        for retry_count in range(task.max_review_json_retries + 1):
            try:
                return self.review_validator.parse_and_validate(raw_output, task), retry_count
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
    ) -> None:
        content = self.final_report_writer.render(state, reason, quality_report)
        self.state_repository.write_final_report(state, content)

    def _log_phase(self, state: RunState, phase: str, event: str, **fields: object) -> None:
        self.phase_logger.info(state, phase, event, **fields)
