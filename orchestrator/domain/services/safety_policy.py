from __future__ import annotations

from pathlib import Path
import re
import shlex

from orchestrator.domain.enums import ChangeType, PermissionLevel
from orchestrator.domain.models.task import TaskConfig
from orchestrator.domain.services.exceptions import SafetyViolation


class SafetyPolicy:
    FORBIDDEN_COMMAND_PATTERNS = [
        r"\brm\s+-rf\b",
        r"\bRemove-Item\b.*\b-Recurse\b",
        r"\bdel\s+/s\b",
        r"\bformat\b",
        r"\bmkfs\b",
        r"\bchmod\s+-R\s+777\b",
        r"\bcurl\b.*\|\s*sh\b",
        r"\bInvoke-WebRequest\b.*\|\s*iex\b",
        r"\bDROP\s+TABLE\b",
        r"\bTRUNCATE\b",
        r"\bDELETE\s+FROM\b(?!.*\bWHERE\b)",
    ]

    def resolve_permission(self, task: TaskConfig) -> tuple[PermissionLevel, str | None]:
        if task.change_type == ChangeType.CONFIG:
            return PermissionLevel.ELEVATED, "change_type_config_requires_elevated"
        return PermissionLevel.WORKSPACE_WRITE, None

    def precheck(self, task: TaskConfig) -> tuple[PermissionLevel, str | None]:
        self._ensure_worktree_inside_repo_or_exists(task)
        permission, reason = self.resolve_permission(task)
        return permission, reason

    def validate_write_path(self, task: TaskConfig, target: Path) -> None:
        worktree = task.worktree_path.resolve()
        resolved = target.resolve()
        if not self._is_relative_to(resolved, worktree):
            raise SafetyViolation(f"path escapes worktree: {target}")

        rel = resolved.relative_to(worktree).as_posix()
        if self._matches_any(rel, task.forbidden_paths):
            raise SafetyViolation(f"path is forbidden: {rel}")
        if task.allowed_paths and not self._matches_any(rel, task.allowed_paths):
            raise SafetyViolation(f"path is not allowed: {rel}")

    def validate_command(self, command: str, task: TaskConfig | None = None) -> None:
        normalized = command.strip()
        for pattern in self.FORBIDDEN_COMMAND_PATTERNS:
            if re.search(pattern, normalized, flags=re.IGNORECASE):
                raise SafetyViolation(f"command is forbidden by safety policy: {pattern}")
        if task is not None and task.allowed_command_prefixes:
            actual_prefix = self._normalized_command_for_allowlist(normalized)
            allowed_prefixes = {self._normalize_command_prefix(prefix) for prefix in task.allowed_command_prefixes}
            if not actual_prefix or not any(actual_prefix.startswith(prefix) for prefix in allowed_prefixes):
                allowed = ", ".join(task.allowed_command_prefixes)
                raise SafetyViolation(
                    f"command is not allowed by allowlist: prefix={actual_prefix or '<empty>'}, allowed={allowed}"
                )

    def _ensure_worktree_inside_repo_or_exists(self, task: TaskConfig) -> None:
        if task.worktree_path.exists():
            return
        if not task.worktree_path.parent.exists():
            raise SafetyViolation(f"worktree parent does not exist: {task.worktree_path.parent}")

    def _matches_any(self, rel_path: str, patterns: list[str]) -> bool:
        normalized = rel_path.strip("/")
        for pattern in patterns:
            item = pattern.strip("/")
            if normalized == item or normalized.startswith(item + "/"):
                return True
        return False

    def _is_relative_to(self, child: Path, parent: Path) -> bool:
        try:
            child.relative_to(parent)
            return True
        except ValueError:
            return False

    def _normalized_command_for_allowlist(self, command: str) -> str:
        try:
            tokens = shlex.split(command, posix=False)
        except ValueError:
            return ""
        if not tokens:
            return ""
        normalized_tokens = [self._normalize_executable_token(token) for token in tokens]
        return " ".join(normalized_tokens)

    def _normalize_command_prefix(self, prefix: str) -> str:
        return " ".join(self._normalize_executable_token(token) for token in prefix.split())

    def _normalize_executable_token(self, token: str) -> str:
        cleaned = token.strip().strip('"').strip("'").replace("\\", "/")
        name = cleaned.rsplit("/", 1)[-1].lower()
        if name.endswith(".exe"):
            return name
        return name
