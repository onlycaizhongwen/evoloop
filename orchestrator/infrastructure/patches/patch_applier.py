from __future__ import annotations

from pathlib import Path

from orchestrator.domain.models.patch_plan import PatchApplyResult, PatchPlan
from orchestrator.domain.models.task import TaskConfig
from orchestrator.domain.services.exceptions import SafetyViolation
from orchestrator.domain.services.safety_policy import SafetyPolicy


class PatchApplyError(Exception):
    pass


class PatchApplier:
    def __init__(self, safety_policy: SafetyPolicy | None = None):
        self.safety_policy = safety_policy or SafetyPolicy()

    def apply(self, task: TaskConfig, plan: PatchPlan, dry_run: bool = False) -> PatchApplyResult:
        result = PatchApplyResult()
        for operation in plan.operations:
            target = task.worktree_path / operation.path
            try:
                self.safety_policy.validate_write_path(task, target)
            except SafetyViolation as exc:
                raise PatchApplyError(str(exc)) from exc
            if operation.op == "replace_text":
                self._replace_text(target, operation.path, operation.old, operation.new, dry_run)
                result.changed_files.append(operation.path)
            elif operation.op == "create_file":
                self._create_file(target, operation.path, operation.content, operation.overwrite, dry_run)
                result.created_files.append(operation.path)
            elif operation.op == "delete_file":
                self._delete_file(target, operation.path, operation.must_exist, dry_run)
                result.deleted_files.append(operation.path)
            elif operation.op == "unified_diff":
                self._apply_unified_diff(target, operation.path, operation.diff, dry_run)
                result.changed_files.append(operation.path)
            else:
                raise PatchApplyError(f"unsupported patch operation: {operation.op}")
        self._score_risk(result)
        return result

    def _replace_text(self, target: Path, rel_path: str, old: str, new: str, dry_run: bool) -> None:
        if not target.exists():
            raise PatchApplyError(f"patch target does not exist: {rel_path}")
        text = target.read_text(encoding="utf-8")
        if old not in text:
            raise PatchApplyError(f"old text not found in patch target: {rel_path}")
        if not dry_run:
            target.write_text(text.replace(old, new, 1), encoding="utf-8")

    def _create_file(self, target: Path, rel_path: str, content: str, overwrite: bool, dry_run: bool) -> None:
        if target.exists() and not overwrite:
            raise PatchApplyError(f"patch target already exists: {rel_path}")
        if not dry_run:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")

    def _delete_file(self, target: Path, rel_path: str, must_exist: bool, dry_run: bool) -> None:
        if not target.exists():
            if must_exist:
                raise PatchApplyError(f"patch target does not exist: {rel_path}")
            return
        if not target.is_file():
            raise PatchApplyError(f"patch target is not a file: {rel_path}")
        if not dry_run:
            target.unlink()

    def _apply_unified_diff(self, target: Path, rel_path: str, diff: str, dry_run: bool) -> None:
        if not target.exists():
            raise PatchApplyError(f"patch target does not exist: {rel_path}")
        original = target.read_text(encoding="utf-8").splitlines(keepends=True)
        patched = self._apply_hunks(original, diff, rel_path)
        if not dry_run:
            target.write_text("".join(patched), encoding="utf-8")

    def _apply_hunks(self, original: list[str], diff: str, rel_path: str) -> list[str]:
        diff_lines = diff.splitlines(keepends=True)
        output: list[str] = []
        source_index = 0
        hunk_count = 0
        i = 0
        while i < len(diff_lines):
            line = diff_lines[i]
            if line.startswith(("--- ", "+++ ")):
                i += 1
                continue
            if not line.startswith("@@"):
                i += 1
                continue
            hunk_count += 1
            old_start = self._parse_hunk_old_start(line, rel_path)
            copy_until = old_start - 1
            if copy_until < source_index:
                raise PatchApplyError(f"overlapping unified diff hunk: {rel_path}")
            output.extend(original[source_index:copy_until])
            source_index = copy_until
            i += 1
            while i < len(diff_lines) and not diff_lines[i].startswith("@@"):
                hunk_line = diff_lines[i]
                if hunk_line.startswith("\\ No newline at end of file"):
                    i += 1
                    continue
                if not hunk_line:
                    i += 1
                    continue
                prefix = hunk_line[0]
                content = hunk_line[1:]
                if prefix == " ":
                    self._assert_source_line(original, source_index, content, rel_path)
                    output.append(original[source_index])
                    source_index += 1
                elif prefix == "-":
                    self._assert_source_line(original, source_index, content, rel_path)
                    source_index += 1
                elif prefix == "+":
                    output.append(content)
                else:
                    raise PatchApplyError(f"unsupported unified diff line: {hunk_line.rstrip()}")
                i += 1
        if hunk_count == 0:
            raise PatchApplyError(f"unified diff contains no hunks: {rel_path}")
        output.extend(original[source_index:])
        return output

    def _parse_hunk_old_start(self, header: str, rel_path: str) -> int:
        try:
            old_range = header.split(" ", 2)[1]
            return int(old_range.removeprefix("-").split(",", 1)[0])
        except (IndexError, ValueError) as exc:
            raise PatchApplyError(f"invalid unified diff hunk header for {rel_path}: {header.rstrip()}") from exc

    def _assert_source_line(self, original: list[str], index: int, expected: str, rel_path: str) -> None:
        if index >= len(original):
            raise PatchApplyError(f"unified diff source exhausted: {rel_path}")
        if original[index] != expected:
            raise PatchApplyError(
                f"unified diff context mismatch in {rel_path}: expected={expected.rstrip()} actual={original[index].rstrip()}"
            )

    def _score_risk(self, result: PatchApplyResult) -> None:
        score = 10
        total_files = len(set(result.changed_files + result.created_files + result.deleted_files))
        if total_files > 5:
            score -= total_files - 5
            result.risk_reasons.append("many_files_changed")
        if result.deleted_files:
            score -= len(result.deleted_files) * 2
            result.risk_reasons.append("files_deleted")
        if result.created_files:
            score -= max(0, len(result.created_files) - 2)
            result.risk_reasons.append("files_created")
        result.risk_score = max(0, score)
