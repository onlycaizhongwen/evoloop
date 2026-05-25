from __future__ import annotations

import json
from pathlib import Path

from orchestrator.domain.enums import ExecutionBackend
from orchestrator.domain.models.check_result import HardCheckResult
from orchestrator.domain.models.quality_report import QualityReport
from orchestrator.domain.models.run_state import RunState
from orchestrator.domain.models.task import TaskConfig


class AgentPromptBuilder:
    def render_command(
        self,
        task: TaskConfig,
        state: RunState,
        template: str,
        *,
        reason_file: Path | None = None,
        repair_prompt_file: Path | None = None,
        prompt_file: Path | None = None,
    ) -> str:
        run_dir = self.run_dir(state)
        attempt_dir = run_dir / f"attempts/{state.attempt:03d}"
        return template.format(
            task_id=task.task_id,
            task_title=task.title,
            task_json=self._render_path(task, run_dir / "task.json", run_dir=run_dir),
            run_dir=self._render_path(task, run_dir, run_dir=run_dir),
            worktree=self._render_worktree_path(task),
            attempt=str(state.attempt),
            attempt_dir=self._render_path(task, attempt_dir, run_dir=run_dir),
            reason_file=self._render_path(task, reason_file, run_dir=run_dir) if reason_file else "",
            repair_prompt_file=self._render_path(task, repair_prompt_file, run_dir=run_dir) if repair_prompt_file else "",
            prompt_file=self._render_path(task, prompt_file, run_dir=run_dir) if prompt_file else "",
        )

    def build_coder_prompt(self, task: TaskConfig, state: RunState) -> str:
        return "\n".join(
            [
                "You are the Coder agent for an auto-evolution coding loop.",
                f"Task ID: {task.task_id}",
                f"Title: {task.title}",
                f"Change type: {task.change_type}",
                f"Attempt: {state.attempt}/{state.max_attempts}",
                "",
                "Description:",
                task.description,
                "",
                "Apply the smallest safe code change needed for this task.",
            ]
        )

    def build_fixer_prompt(
        self,
        task: TaskConfig,
        state: RunState,
        reason: HardCheckResult | QualityReport,
        reason_file: Path,
    ) -> str:
        return "\n".join(
            [
                "You are the Fixer agent for an auto-evolution coding loop.",
                f"Task ID: {task.task_id}",
                f"Title: {task.title}",
                f"Attempt: {state.attempt}/{state.max_attempts}",
                f"Failure reason file: {reason_file}",
                "",
                "Failure summary:",
                self._summarize_reason(reason),
                "",
                "Fix the issue without broad refactors.",
            ]
        )

    def build_patch_coder_prompt(self, task: TaskConfig, state: RunState) -> str:
        return "\n".join(
            [
                "You are the Coder agent for an auto-evolution coding loop.",
                "Do not edit files directly. Return only patch JSON.",
                f"Task ID: {task.task_id}",
                f"Title: {task.title}",
                f"Change type: {task.change_type}",
                f"Attempt: {state.attempt}/{state.max_attempts}",
                "",
                "Description:",
                task.description,
                "",
                self._render_allowed_file_snapshot(task),
                "",
                "Patch JSON schema:",
                self._patch_schema_example(task.task_id),
                "",
                self._patch_output_rules(task.task_id),
                "",
                "Return only JSON. Paths must be relative to the worktree.",
            ]
        )

    def build_patch_fixer_prompt(
        self,
        task: TaskConfig,
        state: RunState,
        reason: HardCheckResult | QualityReport,
        reason_file: Path,
    ) -> str:
        return "\n".join(
            [
                "You are the Fixer agent for an auto-evolution coding loop.",
                "Do not edit files directly. Return only patch JSON.",
                f"Task ID: {task.task_id}",
                f"Title: {task.title}",
                f"Attempt: {state.attempt}/{state.max_attempts}",
                f"Failure reason file: {reason_file}",
                "",
                "Failure summary:",
                self._summarize_reason(reason),
                "",
                self._render_allowed_file_snapshot(task),
                "",
                "Patch JSON schema:",
                self._patch_schema_example(task.task_id),
                "",
                self._patch_output_rules(task.task_id),
                "",
                "Return only JSON. Paths must be relative to the worktree.",
            ]
        )

    def build_reviewer_prompt(
        self,
        task: TaskConfig,
        state: RunState,
        repair_prompt: str | None = None,
    ) -> str:
        if repair_prompt:
            return repair_prompt
        return "\n".join(
            [
                "You are the Reviewer agent for an auto-evolution coding loop.",
                f"Task ID: {task.task_id}",
                f"Title: {task.title}",
                f"Attempt: {state.attempt}/{state.max_attempts}",
                "",
                "Return only review.json content that matches the required schema.",
            ]
        )

    def write_prompt_file(self, state: RunState, role: str, content: str) -> Path:
        path = self.run_dir(state) / f"attempts/{state.attempt:03d}/{role}_prompt.txt"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def write_reason_file(self, state: RunState, reason: HardCheckResult | QualityReport) -> Path:
        path = self.run_dir(state) / f"attempts/{state.attempt:03d}/fix_reason.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = reason.model_dump(mode="json") if hasattr(reason, "model_dump") else {"reason": str(reason)}
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def run_dir(self, state: RunState) -> Path:
        return Path(state.artifacts["run_dir"])

    def _render_path(self, task: TaskConfig, path: Path, *, run_dir: Path) -> str:
        if task.execution_backend != ExecutionBackend.DOCKER:
            return str(path.resolve())
        try:
            relative = path.resolve().relative_to(run_dir.resolve())
        except ValueError:
            return str(path.resolve())
        if not relative.parts:
            return "/run"
        return "/run/" + relative.as_posix()

    def _render_worktree_path(self, task: TaskConfig) -> str:
        if task.execution_backend == ExecutionBackend.DOCKER:
            return task.sandbox.container_workdir
        return str(task.worktree_path.resolve())

    def _summarize_reason(self, reason: HardCheckResult | QualityReport) -> str:
        if isinstance(reason, HardCheckResult):
            return reason.first_failure_reason() or "hard check failed"
        return reason.reason

    def _patch_schema_example(self, task_id: str) -> str:
        return (
            '{"schema_version":"1.0","task_id":"'
            + task_id
            + '","summary":"...",'
            + '"operations":['
            + '{"op":"replace_text","path":"relative/file.py","old":"exact old text","new":"replacement text"},'
            + '{"op":"create_file","path":"relative/new_file.py","content":"file content","overwrite":false},'
            + '{"op":"delete_file","path":"relative/old_file.py","must_exist":true},'
            + '{"op":"unified_diff","path":"relative/file.py","diff":"--- a/relative/file.py\\n+++ b/relative/file.py\\n@@ -1,2 +1,2 @@\\n old line\\n-new\\n+replacement\\n"}'
            + "]}"
        )

    def _patch_output_rules(self, task_id: str) -> str:
        return "\n".join(
            [
                "Patch output rules:",
                "- Prefer replace_text for simple exact replacements in one file.",
                "- Use unified_diff only when replace_text is not enough.",
                "- If you use unified_diff, diff must include ---/+++ file headers and at least one @@ hunk header.",
                "- A unified_diff without @@ is invalid and will be rejected.",
                "- operations must contain at least one operation; do not return an empty operations list.",
                "- If no code change is needed, create a minimal documentation or comment change only when the task explicitly asks for it; otherwise explain by using a safe replace_text only when exact old text exists.",
                "- Before returning, self-check that the JSON is valid, task_id matches exactly, paths are relative, and every old text or diff context exists in the allowed file snapshot.",
                "Valid simple example:",
                '{"schema_version":"1.0","task_id":"'
                + task_id
                + '","summary":"Fix add.","operations":[{"op":"replace_text","path":"calculator.py","old":"return a - b","new":"return a + b"}]}',
                "Valid unified_diff example:",
                '{"schema_version":"1.0","task_id":"'
                + task_id
                + '","summary":"Fix add.","operations":[{"op":"unified_diff","path":"calculator.py","diff":"--- a/calculator.py\\n+++ b/calculator.py\\n@@ -1,2 +1,2 @@\\n def add(a, b):\\n-    return a - b\\n+    return a + b\\n"}]}',
            ]
        )

    def _render_allowed_file_snapshot(self, task: TaskConfig) -> str:
        lines = ["Allowed file snapshot:"]
        snapshots = []
        for rel_path in task.allowed_paths:
            normalized = rel_path.strip().replace("\\", "/").strip("/")
            if not normalized or normalized == ".":
                continue
            target = task.worktree_path / normalized
            if not target.is_file():
                continue
            try:
                content = target.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            snapshots.append((normalized, content))
        if not snapshots:
            lines.append("(no readable allowed files)")
            return "\n".join(lines)
        for rel_path, content in snapshots:
            lines.extend(
                [
                    f"--- file: {rel_path} ---",
                    content,
                    f"--- end file: {rel_path} ---",
                ]
            )
        return "\n".join(lines)
