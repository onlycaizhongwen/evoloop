from __future__ import annotations

from orchestrator.domain.models.check_result import HardCheckResult
from orchestrator.domain.models.quality_report import QualityReport
from orchestrator.domain.models.rule_proposal import RuleProposal
from orchestrator.domain.models.run_state import RunState


class RuleProposalService:
    def from_halt_reason(
        self,
        state: RunState,
        reason: str,
        *,
        source: str = "orchestrator_halt",
        evidence: list[str] | None = None,
    ) -> RuleProposal:
        return RuleProposal(
            task_id=state.task_id,
            run_id=state.run_id,
            source=source,
            reason=reason,
            suggested_rule=self._suggest_rule(source, reason),
            scope=self._scope_for(source),
            evidence=evidence or [],
        )

    def from_hard_check_failure(self, state: RunState, result: HardCheckResult) -> RuleProposal:
        failed = [command for command in result.commands if not command.passed]
        evidence = [
            f"{command.name}: exit_code={command.exit_code}, command={command.command or 'N/A'}"
            for command in failed
        ]
        reason = result.first_failure_reason() or "hard check failed"
        return self.from_halt_reason(
            state,
            reason,
            source="hard_check_failure",
            evidence=evidence,
        )

    def from_malformed_review(self, state: RunState, reason: str, retry_count: int) -> RuleProposal:
        attempt_dir = f"attempts/{state.attempt:03d}"
        return self.from_halt_reason(
            state,
            reason,
            source="malformed_review_json",
            evidence=[
                f"review_json_retry_count={retry_count}",
                f"raw outputs saved under {attempt_dir}/malformed_review_*.txt",
            ],
        )

    def from_quality_report(self, state: RunState, report: QualityReport) -> RuleProposal:
        return self.from_halt_reason(
            state,
            report.reason,
            source="quality_gate_halt",
            evidence=[
                f"quality_score={report.quality_score}",
                f"decision={report.decision}",
                f"diff_risk_score={report.diff_risk_score}",
                f"review_json_retry_count={report.review_json_retry_count}",
            ],
        )

    def _suggest_rule(self, source: str, reason: str) -> str:
        if source == "hard_check_failure":
            return "When hard checks repeatedly fail, capture the first failing command and require Fixer to address it before any review phase."
        if source == "malformed_review_json":
            return "When Reviewer output is malformed after retries, preserve raw output and improve the repair prompt or reviewer contract before rerunning."
        if source == "quality_gate_halt":
            return "When Quality Gate halts a task, turn the gate reason and scoring evidence into a focused remediation checklist."
        return f"When a run halts with reason `{reason}`, create a pending rule proposal for human review before changing formal skills."

    def _scope_for(self, source: str) -> str:
        if source == "hard_check_failure":
            return "check_runner, fixer_prompt, hard_check_policy"
        if source == "malformed_review_json":
            return "reviewer_prompt, review_json_schema, retry_policy"
        if source == "quality_gate_halt":
            return "quality_gate, review_policy, diff_risk_policy"
        return "orchestrator_halt_policy"
