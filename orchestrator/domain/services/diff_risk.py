from __future__ import annotations

from orchestrator.domain.enums import ChangeType
from orchestrator.domain.models.diff import DiffStats


class DiffRiskService:
    def calculate_score(self, diff_stats: DiffStats, change_type: ChangeType) -> int:
        score = 10
        score -= max(0, diff_stats.changed_files - 5)
        if diff_stats.total_changed_lines > 200:
            score -= 2
        if diff_stats.max_file_changed_lines > 300:
            score -= 2
        score -= diff_stats.deleted_files * 2
        if diff_stats.only_tests_changed:
            score -= 1
        if diff_stats.source_changed_without_tests and change_type in {ChangeType.FEATURE, ChangeType.BUGFIX}:
            score -= 2
        if diff_stats.touches_forbidden_path:
            score -= 5
        return max(0, score)
