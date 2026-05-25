from __future__ import annotations

from orchestrator.domain.models.quality_report import QualityReport
from orchestrator.domain.models.run_state import RunState


class FinalReportWriter:
    def render(self, state: RunState, reason: str, quality_report: QualityReport | None = None) -> str:
        lines = [
            "# 自动循环进化编码智能体系统 - 运行报告",
            "",
            f"- run_id: `{state.run_id}`",
            f"- task_id: `{state.task_id}`",
            f"- status: `{state.status}`",
            f"- phase: `{state.current_phase}`",
            f"- attempt: `{state.attempt}/{state.max_attempts}`",
            f"- reason: {reason}",
        ]
        if quality_report:
            lines.extend(
                [
                    "",
                    "## Quality Gate",
                    "",
                    f"- quality_score: `{quality_report.quality_score}`",
                    f"- decision: `{quality_report.decision}`",
                    f"- diff_risk_score: `{quality_report.diff_risk_score}`",
                    f"- review_json_retry_count: `{quality_report.review_json_retry_count}`",
                ]
            )
        return "\n".join(lines) + "\n"
