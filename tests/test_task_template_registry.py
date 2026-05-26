from __future__ import annotations

from orchestrator.application.task_template_registry import (
    DEFAULT_TEMPLATE_ID,
    get_command_preset,
    get_task_template_summary,
    get_task_template_form,
    list_command_presets,
    list_task_templates,
    normalize_template_id,
)


def test_template_id_normalization_falls_back_to_default():
    assert normalize_template_id("docker_team_patch") == "docker_team_patch"
    assert normalize_template_id("missing") == DEFAULT_TEMPLATE_ID


def test_template_form_is_copied_before_returning():
    first = get_task_template_form("docker_team_patch")
    first["task_id"] = "mutated"

    second = get_task_template_form("docker_team_patch")

    assert second["task_id"] == "task-docker-team-web-001"
    assert second["execution_backend"] == "docker"
    assert second["command_preset"] == "team_patch_backend"


def test_template_summary_normalizes_unknown_id():
    summary = get_task_template_summary("missing")

    assert summary["id"] == DEFAULT_TEMPLATE_ID
    assert summary["label"] == "Local OMX Team Patch"


def test_command_preset_is_copied_before_returning():
    preset = get_command_preset("team_patch_backend")
    assert preset is not None
    preset["commands"]["patch_coder"] = "mutated"

    fresh = get_command_preset("team_patch_backend")

    assert fresh is not None
    assert fresh["commands"]["patch_coder"] == "python /worktree/docker_team_backend.py {task_id} {prompt_file}"


def test_template_and_command_preset_lists_are_view_models():
    templates = list_task_templates()
    template_ids = {item["id"] for item in templates}
    preset_ids = {item["id"] for item in list_command_presets()}
    docker_team = next(item for item in templates if item["id"] == "docker_team_patch")

    assert {"local_omx_team", "docker_team_patch", "docker_patch_json", "mock_demo"} <= template_ids
    assert {"custom", "team_patch_backend", "patch_json_backend"} <= preset_ids
    assert "Recommended" in docker_team["badges"]
    assert "Docker" in docker_team["badges"]
    assert docker_team["execution_backend"] == "docker"
    assert docker_team["agent_mode"] == "omx_team_patch"
    assert docker_team["command_preset"] == "team_patch_backend"
    assert docker_team["check_command"] == "python -m unittest -q"
    assert docker_team["allowed_paths"] == "calculator.py, test_calculator.py, docker_team_backend.py"
