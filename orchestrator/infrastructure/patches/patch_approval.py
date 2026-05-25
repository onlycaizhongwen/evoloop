from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from orchestrator.domain.models.patch_plan import PatchApplyResult, PatchPlan
from orchestrator.domain.models.run_state import RunState
from orchestrator.domain.models.task import TaskConfig


class PatchApprovalRequired(Exception):
    pass


class PatchApprovalPolicy:
    def requires_approval(self, task: TaskConfig, result: PatchApplyResult) -> bool:
        if not task.patch_auto_apply:
            return True
        if result.risk_score < task.patch_approval_risk_threshold:
            return True
        if task.patch_require_approval_on_delete and result.deleted_files:
            return True
        return False


class PendingPatchWriter:
    def write(self, state: RunState, role: str, plan: PatchPlan, result: PatchApplyResult) -> Path:
        pending_dir = Path(state.artifacts["run_dir"]) / "pending-patches"
        pending_dir.mkdir(parents=True, exist_ok=True)
        path = pending_dir / f"{state.attempt:03d}-{role}.json"
        payload = {
            "schema_version": "1.0",
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "run_id": state.run_id,
            "task_id": state.task_id,
            "attempt": state.attempt,
            "role": role,
            "patch_plan": plan.model_dump(mode="json"),
            "risk": result.model_dump(mode="json"),
        }
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return path
