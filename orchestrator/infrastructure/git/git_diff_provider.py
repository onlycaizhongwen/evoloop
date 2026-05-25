from __future__ import annotations

import subprocess
from pathlib import PurePosixPath

from orchestrator.domain.models.diff import DiffStats
from orchestrator.domain.models.task import TaskConfig


class GitDiffProvider:
    def get_diff_stats(self, task: TaskConfig) -> DiffStats:
        if not (task.worktree_path / ".git").exists():
            return DiffStats()

        numstat = self._git(task, "diff", "--numstat")
        name_status = self._git(task, "diff", "--name-status")

        changed_files = 0
        total_changed_lines = 0
        max_file_changed_lines = 0
        deleted_files = 0
        source_changed = False
        tests_changed = False
        touches_forbidden = False

        for line in numstat.splitlines():
            parts = line.split("\t")
            if len(parts) < 3:
                continue
            added_raw, deleted_raw, path = parts[0], parts[1], parts[2]
            added = self._safe_int(added_raw)
            deleted = self._safe_int(deleted_raw)
            changed = added + deleted
            changed_files += 1
            total_changed_lines += changed
            max_file_changed_lines = max(max_file_changed_lines, changed)
            normalized = path.replace("\\", "/")
            tests_changed = tests_changed or self._is_test_path(normalized)
            source_changed = source_changed or self._is_source_path(normalized)
            touches_forbidden = touches_forbidden or self._matches_any(normalized, task.forbidden_paths)

        for line in name_status.splitlines():
            parts = line.split("\t")
            if len(parts) >= 2 and parts[0].startswith("D"):
                deleted_files += 1

        return DiffStats(
            changed_files=changed_files,
            total_changed_lines=total_changed_lines,
            max_file_changed_lines=max_file_changed_lines,
            deleted_files=deleted_files,
            only_tests_changed=tests_changed and not source_changed,
            source_changed_without_tests=source_changed and not tests_changed,
            touches_forbidden_path=touches_forbidden,
        )

    def _git(self, task: TaskConfig, *args: str) -> str:
        result = subprocess.run(
            ["git", *args],
            cwd=task.worktree_path,
            text=True,
            capture_output=True,
            check=False,
        )
        if result.returncode != 0:
            return ""
        return result.stdout

    def _safe_int(self, value: str) -> int:
        try:
            return int(value)
        except ValueError:
            return 0

    def _is_test_path(self, path: str) -> bool:
        parts = PurePosixPath(path).parts
        return "tests" in parts or path.endswith("_test.py") or path.endswith(".test.ts") or path.endswith(".spec.ts")

    def _is_source_path(self, path: str) -> bool:
        parts = PurePosixPath(path).parts
        if self._is_test_path(path):
            return False
        return any(part in parts for part in ("src", "orchestrator", "app", "lib"))

    def _matches_any(self, rel_path: str, patterns: list[str]) -> bool:
        normalized = rel_path.strip("/")
        for pattern in patterns:
            item = pattern.strip("/")
            if normalized == item or normalized.startswith(item + "/"):
                return True
        return False
