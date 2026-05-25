from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from orchestrator.domain.enums import ChangeType
from orchestrator.domain.models.patch_plan import PatchPlan
from orchestrator.domain.models.task import TaskConfig
from orchestrator.domain.services.patch_validator import PatchValidator
from orchestrator.domain.models.run_state import RunState
from orchestrator.infrastructure.patches.patch_approval import PatchApprovalPolicy, PendingPatchWriter
from orchestrator.infrastructure.patches.patch_applier import PatchApplier, PatchApplyError
from orchestrator.infrastructure.patches.pending_patch_service import PendingPatchService


def make_task(tmp_path: Path) -> TaskConfig:
    return TaskConfig(
        task_id="task-001",
        title="Patch task",
        description="Patch task",
        change_type=ChangeType.BUGFIX,
        repo_path=tmp_path,
        worktree_path=tmp_path,
        allowed_paths=["calculator.py", "new_file.py", "old_file.py"],
        forbidden_paths=["secrets"],
    )


def test_patch_validator_extracts_and_validates_patch_json(tmp_path: Path):
    task = make_task(tmp_path)
    raw = json.dumps(
        {
            "schema_version": "1.0",
            "task_id": "task-001",
            "summary": "ok",
            "operations": [{"op": "replace_text", "path": "a.py", "old": "1", "new": "2"}],
        }
    )

    plan = PatchValidator().parse_and_validate(raw, task)

    assert plan.operations[0].path == "a.py"


def test_patch_applier_replaces_text_inside_allowed_worktree(tmp_path: Path):
    task = make_task(tmp_path)
    target = tmp_path / "calculator.py"
    target.write_text("def add(a, b):\n    return a - b\n", encoding="utf-8")
    plan = PatchPlan(
        task_id="task-001",
        operations=[
            {
                "op": "replace_text",
                "path": "calculator.py",
                "old": "return a - b",
                "new": "return a + b",
            }
        ],
    )

    result = PatchApplier().apply(task, plan)

    assert result.changed_files == ["calculator.py"]
    assert result.risk_score == 10
    assert "return a + b" in target.read_text(encoding="utf-8")


def test_patch_applier_creates_file_inside_allowed_worktree(tmp_path: Path):
    task = make_task(tmp_path)
    target = tmp_path / "new_file.py"
    plan = PatchPlan(
        task_id="task-001",
        operations=[{"op": "create_file", "path": "new_file.py", "content": "VALUE = 1\n"}],
    )

    result = PatchApplier().apply(task, plan)

    assert result.created_files == ["new_file.py"]
    assert target.read_text(encoding="utf-8") == "VALUE = 1\n"


def test_patch_applier_deletes_file_and_scores_risk(tmp_path: Path):
    task = make_task(tmp_path)
    target = tmp_path / "old_file.py"
    target.write_text("obsolete", encoding="utf-8")
    plan = PatchPlan(
        task_id="task-001",
        operations=[{"op": "delete_file", "path": "old_file.py"}],
    )

    result = PatchApplier().apply(task, plan)

    assert result.deleted_files == ["old_file.py"]
    assert result.risk_score == 8
    assert "files_deleted" in result.risk_reasons
    assert not target.exists()


def test_patch_applier_applies_unified_diff(tmp_path: Path):
    task = make_task(tmp_path)
    target = tmp_path / "calculator.py"
    target.write_text("def add(a, b):\n    return a - b\n", encoding="utf-8")
    diff = "\n".join(
        [
            "--- a/calculator.py",
            "+++ b/calculator.py",
            "@@ -1,2 +1,2 @@",
            " def add(a, b):",
            "-    return a - b",
            "+    return a + b",
            "",
        ]
    )
    plan = PatchPlan(task_id="task-001", operations=[{"op": "unified_diff", "path": "calculator.py", "diff": diff}])

    result = PatchApplier().apply(task, plan)

    assert result.changed_files == ["calculator.py"]
    assert "return a + b" in target.read_text(encoding="utf-8")


def test_patch_applier_unified_diff_dry_run_does_not_modify_file(tmp_path: Path):
    task = make_task(tmp_path)
    target = tmp_path / "calculator.py"
    target.write_text("def add(a, b):\n    return a - b\n", encoding="utf-8")
    diff = "@@ -1,2 +1,2 @@\n def add(a, b):\n-    return a - b\n+    return a + b\n"
    plan = PatchPlan(task_id="task-001", operations=[{"op": "unified_diff", "path": "calculator.py", "diff": diff}])

    result = PatchApplier().apply(task, plan, dry_run=True)

    assert result.changed_files == ["calculator.py"]
    assert "return a - b" in target.read_text(encoding="utf-8")


def test_patch_applier_unified_diff_rejects_context_mismatch(tmp_path: Path):
    task = make_task(tmp_path)
    target = tmp_path / "calculator.py"
    target.write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
    diff = "@@ -1,2 +1,2 @@\n def add(a, b):\n-    return a - b\n+    return a + b\n"
    plan = PatchPlan(task_id="task-001", operations=[{"op": "unified_diff", "path": "calculator.py", "diff": diff}])

    with pytest.raises(PatchApplyError, match="context mismatch"):
        PatchApplier().apply(task, plan)


def test_patch_applier_unified_diff_rejects_missing_hunk(tmp_path: Path):
    task = make_task(tmp_path)
    target = tmp_path / "calculator.py"
    target.write_text("def add(a, b):\n    return a - b\n", encoding="utf-8")
    plan = PatchPlan(
        task_id="task-001",
        operations=[{"op": "unified_diff", "path": "calculator.py", "diff": "not a unified diff"}],
    )

    with pytest.raises(PatchApplyError, match="no hunks"):
        PatchApplier().apply(task, plan)


def test_patch_approval_policy_requires_approval_for_delete(tmp_path: Path):
    task = make_task(tmp_path)
    target = tmp_path / "old_file.py"
    target.write_text("obsolete", encoding="utf-8")
    plan = PatchPlan(task_id="task-001", operations=[{"op": "delete_file", "path": "old_file.py"}])

    result = PatchApplier().apply(task, plan, dry_run=True)

    assert PatchApprovalPolicy().requires_approval(task, result)
    assert target.exists()


def test_pending_patch_writer_persists_patch_plan(tmp_path: Path):
    run_dir = tmp_path / "run"
    state = RunState(
        run_id="run-test",
        task_id="task-001",
        attempt=1,
        max_attempts=1,
        artifacts={"run_dir": str(run_dir)},
    )
    plan = PatchPlan(task_id="task-001", operations=[{"op": "delete_file", "path": "old_file.py"}])
    (tmp_path / "old_file.py").write_text("obsolete", encoding="utf-8")
    result = PatchApplier().apply(make_task(tmp_path), plan, dry_run=True)

    path = PendingPatchWriter().write(state, "patch_coder", plan, result)

    assert path.exists()
    assert '"status": "pending"' in path.read_text(encoding="utf-8")


def test_pending_patch_service_includes_operation_previews(tmp_path: Path):
    run_dir = tmp_path / "runs" / "run-test"
    state = RunState(
        run_id="run-test",
        task_id="task-001",
        attempt=1,
        max_attempts=1,
        artifacts={"run_dir": str(run_dir)},
    )
    task = make_task(tmp_path)
    (tmp_path / "calculator.py").write_text("def add(a, b):\n    return a - b\n", encoding="utf-8")
    (tmp_path / "old_file.py").write_text("obsolete", encoding="utf-8")
    diff = "@@ -1,2 +1,2 @@\n def add(a, b):\n-    return a - b\n+    return a + b\n"
    plan = PatchPlan(
        task_id="task-001",
        summary="fix add",
        operations=[
            {"op": "replace_text", "path": "calculator.py", "old": "return a - b", "new": "return a + b"},
            {"op": "create_file", "path": "new_file.py", "content": "VALUE = 1\n"},
            {"op": "delete_file", "path": "old_file.py", "must_exist": True},
            {"op": "unified_diff", "path": "calculator.py", "diff": diff},
        ],
    )
    result = PatchApplier().apply(task, plan, dry_run=True)
    PendingPatchWriter().write(state, "patch_coder", plan, result)

    [summary] = PendingPatchService(runs_dir=tmp_path / "runs").list(run_id="run-test")

    assert summary["summary"] == "fix add"
    assert "files_deleted" in summary["risk_reasons"]
    assert summary["operations"][0]["op"] == "replace_text"
    assert "--- old" in summary["operations"][0]["preview"]
    assert "VALUE = 1" in summary["operations"][1]["preview"]
    assert "删除文件" in summary["operations"][2]["preview"]
    assert "@@ -1,2 +1,2 @@" in summary["operations"][3]["preview"]


def test_patch_applier_rejects_forbidden_path(tmp_path: Path):
    task = make_task(tmp_path)
    target = tmp_path / "secrets" / "token.txt"
    target.parent.mkdir()
    target.write_text("old", encoding="utf-8")
    plan = PatchPlan(
        task_id="task-001",
        operations=[{"op": "replace_text", "path": "secrets/token.txt", "old": "old", "new": "new"}],
    )

    with pytest.raises(PatchApplyError, match="forbidden"):
        PatchApplier().apply(task, plan)
