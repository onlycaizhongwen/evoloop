from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from orchestrator.config.task_loader import TaskLoader
from orchestrator.domain.models.patch_plan import PatchPlan
from orchestrator.infrastructure.checks.shell_check_runner import ShellCheckRunner
from orchestrator.infrastructure.command.safe_command_runner import SafeCommandRunner
from orchestrator.infrastructure.patches.patch_applier import PatchApplier


class PendingPatchService:
    def __init__(self, runs_dir: Path | str = ".omx/runs", task_loader: TaskLoader | None = None):
        self.runs_dir = Path(runs_dir)
        self.task_loader = task_loader or TaskLoader()
        self.patch_applier = PatchApplier()

    def list(self, run_id: str | None = None) -> list[dict[str, Any]]:
        run_dirs = [self.runs_dir / run_id] if run_id else [path for path in self.runs_dir.glob("run-*") if path.is_dir()]
        patches: list[dict[str, Any]] = []
        for run_dir in run_dirs:
            pending_dir = run_dir / "pending-patches"
            if not pending_dir.exists():
                continue
            for path in sorted(pending_dir.glob("*.json")):
                payload = self._read(path)
                patches.append(self._summary(path, payload))
        return patches

    def apply(
        self,
        run_id: str,
        patch_name: str,
        reviewer: str | None = None,
        note: str | None = None,
        rerun_checks: bool = False,
    ) -> dict[str, Any]:
        path = self._patch_path(run_id, patch_name)
        payload = self._read(path)
        if payload.get("status") == "applied":
            return self._summary(path, payload)
        if payload.get("status") == "rejected":
            raise ValueError(f"cannot apply rejected patch: {patch_name}")
        task = self.task_loader.load(self.runs_dir / run_id / "task.json")
        plan = PatchPlan.model_validate(payload["patch_plan"])
        result = self.patch_applier.apply(task, plan)
        payload["status"] = "applied"
        payload["applied_at"] = datetime.now().isoformat()
        payload["reviewed_by"] = reviewer
        payload["review_note"] = note
        payload["apply_result"] = result.model_dump(mode="json")
        if rerun_checks:
            checks = ShellCheckRunner(command_runner=SafeCommandRunner()).run_all(task)
            payload["post_apply_checks"] = checks.model_dump(mode="json")
        self._write(path, payload)
        return self._summary(path, payload)

    def reject(self, run_id: str, patch_name: str, reviewer: str | None = None, note: str | None = None) -> dict[str, Any]:
        path = self._patch_path(run_id, patch_name)
        payload = self._read(path)
        payload["status"] = "rejected"
        payload["rejected_at"] = datetime.now().isoformat()
        payload["reviewed_by"] = reviewer
        payload["review_note"] = note
        self._write(path, payload)
        return self._summary(path, payload)

    def record_rerun_task(self, run_id: str, patch_name: str, rerun_state: Any) -> dict[str, Any]:
        path = self._patch_path(run_id, patch_name)
        payload = self._read(path)
        payload["post_apply_rerun"] = {
            "run_id": rerun_state.run_id,
            "status": str(rerun_state.status),
            "phase": rerun_state.current_phase,
            "attempt": rerun_state.attempt,
            "reason": rerun_state.artifacts.get("validation_reason"),
            "run_dir": rerun_state.artifacts.get("run_dir"),
            "recorded_at": datetime.now().isoformat(),
        }
        self._write(path, payload)
        return self._summary(path, payload)

    def _patch_path(self, run_id: str, patch_name: str) -> Path:
        path = self.runs_dir / run_id / "pending-patches" / patch_name
        if path.suffix != ".json":
            path = path.with_suffix(".json")
        if not path.exists():
            raise FileNotFoundError(path)
        return path

    def _read(self, path: Path) -> dict[str, Any]:
        return json.loads(path.read_text(encoding="utf-8"))

    def _write(self, path: Path, payload: dict[str, Any]) -> None:
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def _summary(self, path: Path, payload: dict[str, Any]) -> dict[str, Any]:
        risk = payload.get("risk", {})
        patch_plan = payload.get("patch_plan", {})
        operations = patch_plan.get("operations", [])
        post_apply_checks = payload.get("post_apply_checks", {})
        check_commands = post_apply_checks.get("commands")
        checks_passed = check_commands is not None and all(command.get("passed") for command in check_commands)
        checks_status = "not_run"
        if check_commands is not None:
            checks_status = "passed" if checks_passed else "failed"
        post_apply_rerun = payload.get("post_apply_rerun", {})
        return {
            "patch": path.name,
            "run_id": payload.get("run_id"),
            "task_id": payload.get("task_id"),
            "status": payload.get("status"),
            "risk_score": risk.get("risk_score"),
            "risk_reasons": risk.get("risk_reasons", []),
            "summary": patch_plan.get("summary", ""),
            "operations": [self._operation_preview(operation) for operation in operations],
            "ops": ",".join(operation.get("op", "") for operation in operations),
            "files": ",".join(
                path
                for path in (
                    risk.get("changed_files", [])
                    + risk.get("created_files", [])
                    + risk.get("deleted_files", [])
                )
            ),
            "checks_passed": checks_passed,
            "checks_status": checks_status,
            "rerun_run_id": post_apply_rerun.get("run_id"),
            "rerun_status": post_apply_rerun.get("status"),
            "rerun_phase": post_apply_rerun.get("phase"),
            "rerun_attempt": post_apply_rerun.get("attempt"),
            "rerun_reason": post_apply_rerun.get("reason"),
        }

    def _operation_preview(self, operation: dict[str, Any]) -> dict[str, Any]:
        op = operation.get("op", "")
        path = operation.get("path", "")
        preview = ""
        if op == "replace_text":
            preview = self._format_replace_preview(operation)
        elif op == "create_file":
            preview = self._truncate(str(operation.get("content", "")))
        elif op == "delete_file":
            preview = "删除文件"
        elif op == "unified_diff":
            preview = self._truncate(str(operation.get("diff", "")), limit=2000)
        return {"op": op, "path": path, "preview": preview}

    def _format_replace_preview(self, operation: dict[str, Any]) -> str:
        old = self._truncate(str(operation.get("old", "")), limit=800)
        new = self._truncate(str(operation.get("new", "")), limit=800)
        return f"--- old\n{old}\n+++ new\n{new}"

    def _truncate(self, value: str, limit: int = 1200) -> str:
        if len(value) <= limit:
            return value
        return value[:limit] + "\n... truncated ..."
