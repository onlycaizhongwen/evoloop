from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKTREE = ROOT / ".tmp" / "omx-team-real-smoke"
TASK_PATH = ROOT / ".tmp" / "omx-team-real-smoke-task.json"


def main() -> int:
    _prepare_worktree()
    task = _write_task()
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "orchestrator.interfaces.cli.main",
            "--task",
            str(task),
            "--agent",
            "omx_team_patch",
            "--real-checks",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    print(completed.stdout, end="")
    if completed.stderr:
        print(completed.stderr, end="", file=sys.stderr)
    if completed.returncode != 0:
        return completed.returncode
    if "return a + b" not in (WORKTREE / "calculator.py").read_text(encoding="utf-8"):
        print("calculator.py was not patched", file=sys.stderr)
        return 1
    return 0


def _prepare_worktree() -> None:
    WORKTREE.mkdir(parents=True, exist_ok=True)
    (WORKTREE / "calculator.py").write_text("def add(a, b):\n    return a - b\n", encoding="utf-8")
    (WORKTREE / "test_calculator.py").write_text(
        "from calculator import add\n\n\ndef test_add():\n    assert add(1, 2) == 3\n",
        encoding="utf-8",
    )


def _write_task() -> Path:
    task = {
        "task_id": "task-omx-team-real-smoke-001",
        "title": "Real OMX team smoke calculator fix",
        "description": "Fix calculator.add so test_calculator.py passes. Return team_result JSON only.",
        "change_type": "bugfix",
        "repo_path": str(WORKTREE),
        "worktree_path": str(WORKTREE),
        "allowed_paths": ["calculator.py"],
        "forbidden_paths": [".env", "secrets", "deploy/prod"],
        "allowed_command_prefixes": ["python", "python.exe", "python -m pytest", "pytest"],
        "check_commands": {"test": "python -m pytest -q", "lint": None, "typecheck": None},
        "agent_mode": "omx_team_patch",
        "agent_commands": {
            "patch_coder": f'"{sys.executable}" "{ROOT / "scripts" / "run_omx_team_patch.py"}" {{task_id}} {{prompt_file}} {{run_dir}}'
        },
        "max_attempts": 1,
        "max_review_json_retries": 1,
        "heartbeat_interval_seconds": 10,
        "command_timeout_seconds": 240,
        "risk_level": "medium",
    }
    TASK_PATH.parent.mkdir(parents=True, exist_ok=True)
    TASK_PATH.write_text(json.dumps(task, ensure_ascii=False, indent=2), encoding="utf-8")
    return TASK_PATH


if __name__ == "__main__":
    raise SystemExit(main())
