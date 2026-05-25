from __future__ import annotations

from orchestrator.domain.enums import Decision
from orchestrator.domain.models.check_result import HardCheckResult
from orchestrator.domain.models.diff import DiffStats
from orchestrator.domain.models.quality_report import QualityReport
from orchestrator.domain.models.review import ReviewResult
from orchestrator.domain.models.run_state import RunState
from orchestrator.domain.models.task import TaskConfig
from orchestrator.domain.services.diff_risk import DiffRiskService


class QualityGate:
    def __init__(self, diff_risk_service: DiffRiskService | None = None):
        self.diff_risk_service = diff_risk_service or DiffRiskService()

    def should_halt_hard_check(self, hard_result: HardCheckResult, state: RunState) -> bool:
        return not state.can_attempt() and not hard_result.passed

    def evaluate(
        self,
        task: TaskConfig,
        state: RunState,
        hard_result: HardCheckResult,
        review: ReviewResult,
        diff_stats: DiffStats,
        review_json_retry_count: int,
    ) -> QualityReport:
        diff_score = self.diff_risk_service.calculate_score(diff_stats, task.change_type)
        review_score = 20 if review.pass_ and not review.blocking and not review.has_critical_issue else 0
        confidence_score = 10 if review.confidence >= 80 else int(review.confidence / 10)
        quality_score = hard_result.score + review_score + confidence_score + diff_score

        reason = "quality gate passed"
        decision = Decision.DONE
        passed = True

        if review.has_critical_issue:
            decision = Decision.HALT
            passed = False
            reason = "critical review issue"
        elif review.blocking:
            decision = Decision.RETRY if state.can_attempt() else Decision.HALT
            passed = False
            reason = "blocking review issue"
        elif quality_score < 80:
            decision = Decision.RETRY if state.can_attempt() else Decision.HALT
            passed = False
            reason = f"quality score below threshold: {quality_score}"

        return QualityReport(
            task_id=task.task_id,
            attempt=state.attempt,
            change_type=task.change_type,
            hard_check_score=hard_result.score,
            review_schema_valid=True,
            review_json_retry_count=review_json_retry_count,
            review_pass=review.pass_,
            review_confidence=review.confidence,
            review_score=review_score + confidence_score,
            diff_risk_score=diff_score,
            quality_score=quality_score,
            passed=passed,
            decision=decision,
            reason=reason,
        )
