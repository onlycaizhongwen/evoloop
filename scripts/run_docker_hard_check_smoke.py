from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKTREE = ROOT / ".tmp" / "docker-hard-check-smoke"
TASK_PATH = ROOT / ".tmp" / "docker-hard-check-smoke-task.json"


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
        print(f"docker_log={run_dir / 'logs' / 'docker_sandbox.jsonl'}")
        _print_docker_log(run_dir)
        _print_environment_hint(run_dir)
    if completed.returncode != 0:
        return completed.returncode
    if "status=done" not in completed.stdout:
        return 1
    return 0


def _prepare_worktree() -> None:
    WORKTREE.mkdir(parents=True, exist_ok=True)
    (WORKTREE / "calculator.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
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


def _write_task() -> Path:
    task = {
        "task_id": "task-docker-hard-check-smoke-001",
        "title": "Docker hard check smoke",
        "description": "Run pytest inside Docker sandbox for a minimal Python project.",
        "change_type": "bugfix",
        "repo_path": str(WORKTREE),
        "worktree_path": str(WORKTREE),
        "allowed_paths": ["calculator.py", "test_calculator.py"],
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
        "agent_mode": "mock",
        "max_attempts": 1,
        "max_review_json_retries": 1,
        "heartbeat_interval_seconds": 5,
        "command_timeout_seconds": 120,
        "risk_level": "low",
    }
    TASK_PATH.parent.mkdir(parents=True, exist_ok=True)
    TASK_PATH.write_text(json.dumps(task, ensure_ascii=False, indent=2), encoding="utf-8")
    return TASK_PATH


def _extract_run_dir(stdout: str) -> Path | None:
    for line in stdout.splitlines():
        if line.startswith("run_dir="):
            return Path(line.split("=", 1)[1].strip())
    return None


def _print_docker_log(run_dir: Path) -> None:
    log_path = run_dir / "logs" / "docker_sandbox.jsonl"
    if not log_path.exists():
        print("docker_log_missing=true")
        return
    lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
    if lines:
        print(f"docker_log_last={lines[-1]}")


def _print_environment_hint(run_dir: Path) -> None:
    hard_checks = run_dir / "attempts" / "001" / "hard_checks.json"
    if not hard_checks.exists():
        return
    payload = json.loads(hard_checks.read_text(encoding="utf-8"))
    stderr = "\n".join(command.get("stderr", "") for command in payload.get("commands", []))
    if "docker daemon is not running" in stderr or "pipe/docker_engine" in stderr:
        print("docker_environment=daemon_not_running")
        print("hint=start Docker Desktop or Docker daemon, then rerun this smoke")
    elif "Unable to find image" in stderr or "pull access denied" in stderr:
        print("docker_environment=image_unavailable")
        print("hint=pull or build the configured sandbox image, then rerun this smoke")


if __name__ == "__main__":
    raise SystemExit(main())
