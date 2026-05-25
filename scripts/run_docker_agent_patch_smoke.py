from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKTREE = ROOT / ".tmp" / "docker-agent-patch-smoke"
TASK_PATH = ROOT / ".tmp" / "docker-agent-patch-smoke-task.json"


def main() -> int:
    _prepare_worktree()
    task_path = _write_task()
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "orchestrator.interfaces.cli.main",
            "--task",
            str(task_path),
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
    run_dir = _extract_run_dir(completed.stdout)
    if run_dir:
        _print_run_evidence(run_dir)
        _print_environment_hint(run_dir)
    if completed.returncode != 0:
        return completed.returncode
    if "status=done" not in completed.stdout:
        return 1
    if "return a + b" not in (WORKTREE / "calculator.py").read_text(encoding="utf-8"):
        print("patch_apply_failed=true")
        return 1
    return 0


def _prepare_worktree() -> None:
    WORKTREE.mkdir(parents=True, exist_ok=True)
    (WORKTREE / "calculator.py").write_text("def add(a, b):\n    return a - b\n", encoding="utf-8")
    (WORKTREE / "test_calculator.py").write_text(
        (
            "import unittest\n\n"
            "from calculator import add\n\n\n"
            "class CalculatorTest(unittest.TestCase):\n"
            "    def test_add(self):\n"
            "        self.assertEqual(add(1, 2), 3)\n\n\n"
            "if __name__ == '__main__':\n"
            "    unittest.main()\n"
        ),
        encoding="utf-8",
    )
    (WORKTREE / "docker_team_backend.py").write_text(
        "\n".join(
            [
                "from __future__ import annotations",
                "",
                "import json",
                "import pathlib",
                "import sys",
                "",
                "task_id = sys.argv[1]",
                "prompt = pathlib.Path(sys.argv[2]).read_text(encoding='utf-8')",
                "assert 'Allowed file snapshot' in prompt",
                "payload = {",
                "    'schema_version': '1.0',",
                "    'task_id': task_id,",
                "    'status': 'completed',",
                "    'roles': {},",
                "    'artifacts': {",
                "        'patch_plan': {",
                "            'schema_version': '1.0',",
                "            'task_id': task_id,",
                "            'summary': 'Fix add from docker agent.',",
                "            'operations': [",
                "                {'op': 'replace_text', 'path': 'calculator.py', 'old': 'return a - b', 'new': 'return a + b'}",
                "            ],",
                "        },",
                "        'review': {",
                "            'schema_version': '1.0',",
                "            'task_id': task_id,",
                "            'pass': True,",
                "            'confidence': 91,",
                "            'summary': 'Docker agent review passed.',",
                "            'issues': [],",
                "            'blocking': False,",
                "            'recommended_next_action': 'pass',",
                "        },",
                "    },",
                "    'diagnostics': [],",
                "}",
                "print(json.dumps(payload))",
            ]
        ),
        encoding="utf-8",
    )


def _write_task() -> Path:
    task = {
        "task_id": "task-docker-agent-patch-smoke-001",
        "title": "Docker agent patch smoke",
        "description": "Generate team_result JSON in Docker; host Orchestrator validates and applies the patch.",
        "change_type": "bugfix",
        "repo_path": str(WORKTREE),
        "worktree_path": str(WORKTREE),
        "allowed_paths": ["calculator.py", "test_calculator.py", "docker_team_backend.py"],
        "forbidden_paths": [".env", "secrets", "deploy/prod"],
        "allowed_command_prefixes": ["python", "python.exe", "python -m pytest", "pytest"],
        "check_commands": {"test": "python -m unittest -q", "lint": None, "typecheck": None},
        "execution_backend": "docker",
        "sandbox": {
            "image": "python:3.12-slim",
            "network": "none",
            "worktree_mount": "readonly",
            "memory_limit": "1g",
            "cpu_limit": 1,
        },
        "agent_mode": "omx_team_patch",
        "agent_commands": {
            "patch_coder": "python /worktree/docker_team_backend.py {task_id} {prompt_file}"
        },
        "max_attempts": 1,
        "max_review_json_retries": 1,
        "heartbeat_interval_seconds": 5,
        "command_timeout_seconds": 120,
        "risk_level": "medium",
    }
    TASK_PATH.parent.mkdir(parents=True, exist_ok=True)
    TASK_PATH.write_text(json.dumps(task, ensure_ascii=False, indent=2), encoding="utf-8")
    return TASK_PATH


def _extract_run_dir(stdout: str) -> Path | None:
    for line in stdout.splitlines():
        if line.startswith("run_dir="):
            return Path(line.split("=", 1)[1].strip())
    return None


def _print_run_evidence(run_dir: Path) -> None:
    print(f"run_dir={run_dir}")
    docker_log = run_dir / "logs" / "docker_sandbox.jsonl"
    print(f"docker_log={docker_log}")
    if docker_log.exists():
        lines = docker_log.read_text(encoding="utf-8", errors="replace").splitlines()
        for line in lines:
            if '"phase": "agent:omx_team_patch:team"' in line:
                print(f"docker_agent_log={line}")
            if '"phase": "check:test"' in line:
                print(f"docker_check_log={line}")
    print(f"calculator_fixed={'return a + b' in (WORKTREE / 'calculator.py').read_text(encoding='utf-8')}")


def _print_environment_hint(run_dir: Path) -> None:
    hard_checks = run_dir / "attempts" / "001" / "hard_checks.json"
    agent_log = run_dir / "logs" / "agent.log"
    text = ""
    if hard_checks.exists():
        text += hard_checks.read_text(encoding="utf-8", errors="replace")
    if agent_log.exists():
        text += "\n" + agent_log.read_text(encoding="utf-8", errors="replace")
    if "docker daemon is not running" in text or "pipe/docker_engine" in text:
        print("docker_environment=daemon_not_running")
        print("hint=start Docker Desktop or Docker daemon, then rerun this smoke")
    elif "Unable to find image" in text or "pull access denied" in text:
        print("docker_environment=image_unavailable")
        print("hint=pull or build the configured sandbox image, then rerun this smoke")


if __name__ == "__main__":
    raise SystemExit(main())
