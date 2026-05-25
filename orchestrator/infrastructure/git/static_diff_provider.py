from __future__ import annotations

from orchestrator.domain.models.diff import DiffStats
from orchestrator.domain.models.task import TaskConfig


class StaticDiffProvider:
    def __init__(self, stats: DiffStats | None = None):
        self.stats = stats or DiffStats(changed_files=1, total_changed_lines=20, max_file_changed_lines=20)

    def get_diff_stats(self, task: TaskConfig) -> DiffStats:
        return self.stats
