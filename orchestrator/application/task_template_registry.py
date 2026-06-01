from __future__ import annotations

from copy import deepcopy
from typing import Any


DEFAULT_TEMPLATE_ID = "local_omx_team"

DOCKER_AGENT_COMMAND_PRESETS: dict[str, dict[str, Any]] = {
    "custom": {
        "label": "Custom commands",
        "description": "Keep the command fields as entered.",
        "agent_modes": ["codex", "mock", "omx", "omx_patch", "omx_team_patch", "shell"],
        "commands": None,
    },
    "team_patch_backend": {
        "label": "Docker team_result backend",
        "description": "Run the default worktree backend that prints OMX team_result JSON.",
        "agent_modes": ["omx_team_patch"],
        "commands": {
            "patch_coder": "python /worktree/docker_team_backend.py {task_id} {prompt_file}",
            "patch_fixer": "",
            "reviewer": "",
        },
    },
    "patch_json_backend": {
        "label": "Docker patch_plan backend",
        "description": "Run the default worktree backend that prints patch_plan JSON.",
        "agent_modes": ["omx_patch"],
        "commands": {
            "patch_coder": "python /worktree/patch_backend.py {task_id} {prompt_file}",
            "patch_fixer": "python /worktree/patch_backend.py {task_id} {prompt_file}",
            "reviewer": "",
        },
    },
}

TASK_TEMPLATES: dict[str, dict[str, Any]] = {
    "local_omx_team": {
        "label": "Local OMX Team Patch",
        "description": "Use the local wrapper script to run an OMX team_result style task.",
        "badges": ["Default", "Local"],
        "form": {
            "task_id": "task-omx-team-web-001",
            "title": "OMX Team Patch 示例任务",
            "description": (
                "请让 OMX Team 产出 team_result JSON，其中包含 patch_plan。"
                "把 calculator.py 里的 add 函数从错误的 a - b 修复为 a + b。"
                "真实写文件、审批和测试都交给 Orchestrator。"
            ),
            "change_type": "bugfix",
            "allowed_paths": "calculator.py",
            "check_command": "python -m unittest -q",
            "agent_mode": "omx_team_patch",
            "command_preset": "custom",
            "execution_backend": "local",
            "real_checks": True,
        },
    },
    "docker_team_patch": {
        "label": "Docker OMX Team Patch",
        "description": "Run the bundled Docker team_result backend with safe /worktree paths.",
        "badges": ["Recommended", "Docker"],
        "form": {
            "task_id": "task-docker-team-web-001",
            "title": "Docker OMX Team Patch 示例任务",
            "description": (
                "请在 Docker sandbox 中运行 team_result backend，产出 patch_plan。"
                "把 calculator.py 里的 add 函数从错误的 a - b 修复为 a + b。"
                "Orchestrator 负责应用 patch 并在 Docker 中执行 hard check。"
            ),
            "change_type": "bugfix",
            "allowed_paths": "calculator.py\ntest_calculator.py\ndocker_team_backend.py",
            "check_command": "python -m unittest -q",
            "agent_mode": "omx_team_patch",
            "command_preset": "team_patch_backend",
            "execution_backend": "docker",
            "real_checks": True,
        },
    },
    "docker_patch_json": {
        "label": "Docker Patch JSON",
        "description": "Run the bundled Docker patch_plan backend for a single-agent patch task.",
        "badges": ["Docker"],
        "form": {
            "task_id": "task-docker-patch-web-001",
            "title": "Docker Patch JSON 示例任务",
            "description": (
                "请在 Docker sandbox 中运行 patch_plan backend，直接产出 patch JSON。"
                "把 calculator.py 里的 add 函数从错误的 a - b 修复为 a + b。"
            ),
            "change_type": "bugfix",
            "allowed_paths": "calculator.py\ntest_calculator.py\npatch_backend.py",
            "check_command": "python -m unittest -q",
            "agent_mode": "omx_patch",
            "command_preset": "patch_json_backend",
            "execution_backend": "docker",
            "real_checks": True,
        },
    },
    "mock_demo": {
        "label": "Mock Flow Demo",
        "description": "Run the orchestrator flow without a real external agent.",
        "badges": ["Demo"],
        "form": {
            "task_id": "task-mock-web-001",
            "title": "Mock 流程演示任务",
            "description": "使用 mock agent 验证 Orchestrator 的状态流转、测试和质量门禁。",
            "change_type": "bugfix",
            "allowed_paths": "calculator.py",
            "check_command": "",
            "agent_mode": "mock",
            "command_preset": "custom",
            "execution_backend": "local",
            "real_checks": False,
        },
    },
}


def normalize_template_id(template_id: str) -> str:
    return template_id if template_id in TASK_TEMPLATES else DEFAULT_TEMPLATE_ID


def get_task_template_form(template_id: str) -> dict[str, Any]:
    return deepcopy(TASK_TEMPLATES[normalize_template_id(template_id)]["form"])


def _compact_allowed_paths(value: Any) -> str:
    if isinstance(value, str):
        return ", ".join(line.strip() for line in value.splitlines() if line.strip())
    if isinstance(value, list):
        return ", ".join(str(item) for item in value)
    return str(value or "")


def list_task_templates() -> list[dict[str, str]]:
    items = []
    for template_id, template in TASK_TEMPLATES.items():
        form = template["form"]
        items.append(
            {
                "id": template_id,
                "label": str(template["label"]),
                "description": str(template["description"]),
                "badges": list(template.get("badges", [])),
                "execution_backend": str(form.get("execution_backend", "")),
                "agent_mode": str(form.get("agent_mode", "")),
                "command_preset": str(form.get("command_preset", "")),
                "allowed_paths": _compact_allowed_paths(form.get("allowed_paths")),
                "check_command": str(form.get("check_command", "")),
            }
        )
    return items


def get_task_template_summary(template_id: str) -> dict[str, str]:
    normalized_id = normalize_template_id(template_id)
    template = TASK_TEMPLATES[normalized_id]
    return {
        "id": normalized_id,
        "label": str(template["label"]),
        "description": str(template["description"]),
    }


def get_command_preset(preset_id: str) -> dict[str, Any] | None:
    preset = DOCKER_AGENT_COMMAND_PRESETS.get(preset_id)
    return deepcopy(preset) if preset else None


def list_command_presets() -> list[dict[str, object]]:
    return [
        {
            "id": preset_id,
            "label": str(preset["label"]),
            "description": str(preset["description"]),
            "agent_modes": ", ".join(preset["agent_modes"]),
        }
        for preset_id, preset in DOCKER_AGENT_COMMAND_PRESETS.items()
    ]
