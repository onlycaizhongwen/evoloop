from __future__ import annotations

import json
from pathlib import Path

from orchestrator.domain.models.patch_plan import PatchPlan
from orchestrator.domain.models.review import ReviewResult


TEAM_TASK_PATH = Path("examples/team_task.omx-team-patch.json")
TEAM_RESULT_PATH = Path("examples/team_result.omx-team-patch.json")
TEAM_RUNTIME_TEMPLATE_PATH = Path("examples/task.omx-team-runtime-template.json")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_team_task_example_defines_required_roles_and_artifacts():
    task = load_json(TEAM_TASK_PATH)

    assert task["schema_version"] == "1.0"
    assert task["mode"] == "omx_team_patch"
    assert task["change_type"] == "bugfix"
    assert task["constraints"]["team_may_write_worktree"] is False
    assert task["constraints"]["orchestrator_is_final_gate"] is True

    roles = {role["role"]: role for role in task["roles"]}
    for role_name in ["planner", "coder", "reviewer", "tester", "gatekeeper", "fixer"]:
        assert role_name in roles

    assert roles["planner"]["required"] is True
    assert roles["coder"]["required"] is True
    assert roles["reviewer"]["required"] is True
    assert task["final_artifacts"] == {
        "patch_plan": "patch_plan.json",
        "review": "review.json",
        "diagnostics": "team_diagnostics.json",
    }
    assert all(not Path(path).is_absolute() for path in task["allowed_paths"])


def test_team_result_example_embeds_valid_patch_plan_and_review():
    task = load_json(TEAM_TASK_PATH)
    result = load_json(TEAM_RESULT_PATH)

    assert result["schema_version"] == "1.0"
    assert result["task_id"] == task["task_id"]
    assert result["status"] == "completed"
    assert result["roles"]["coder"]["artifact"] == "patch_plan.json"
    assert result["roles"]["reviewer"]["artifact"] == "review.json"

    patch_plan = PatchPlan.model_validate(result["artifacts"]["patch_plan"])
    review = ReviewResult.model_validate(result["artifacts"]["review"])

    assert patch_plan.task_id == task["task_id"]
    assert review.task_id == task["task_id"]
    assert review.pass_ is True
    assert patch_plan.operations[0].op == "replace_text"
    assert patch_plan.operations[0].path in task["allowed_paths"]


def test_team_runtime_template_uses_relative_script_command():
    task = load_json(TEAM_RUNTIME_TEMPLATE_PATH)

    command = task["agent_commands"]["patch_coder"]
    assert task["agent_mode"] == "omx_team_patch"
    assert "--runtime team" in command
    assert "scripts/run_omx_team_patch.py" in command
    assert "D:/" not in command
