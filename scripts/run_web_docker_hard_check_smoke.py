from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.infrastructure.persistence.sqlite_job_repository import SQLiteJobRepository
from orchestrator.interfaces.web.main import app


WORKTREE = ROOT / ".tmp" / "web-docker-hard-check-smoke"
JOB_DB = ROOT / ".omx" / "orchestrator.db"
TIMEOUT_SECONDS = 180


def main() -> int:
    os.chdir(ROOT)
    _prepare_worktree()

    response = TestClient(app).post(
        "/tasks/run",
        data={
            "task_id": "task-web-docker-hard-check-smoke-001",
            "title": "Web Docker hard check smoke",
            "description": "Submit a Docker-backed hard-check task through the Web form.",
            "change_type": "bugfix",
            "allowed_paths": "calculator.py\ntest_calculator.py",
            "worktree_path": str(WORKTREE),
            "check_command": "python -m unittest -q",
            "agent_mode": "mock",
            "patch_coder": "",
            "patch_fixer": "",
            "reviewer": "",
            "execution_backend": "docker",
            "sandbox_image": "python:3.12-slim",
            "sandbox_network": "none",
            "sandbox_worktree_mount": "readonly",
            "sandbox_memory_limit": "1g",
            "sandbox_cpu_limit": "1",
            "real_checks": "on",
        },
        follow_redirects=False,
    )
    if response.status_code != 303:
        print(f"web_submit_status={response.status_code}")
        print(response.text)
        return 1

    job_id = response.headers["location"].rsplit("/", 1)[-1]
    print(f"job_id={job_id}")
    job = _wait_for_job(job_id)
    print(f"job_status={job['status']}")
    print(f"run_id={job.get('run_id', '')}")
    print(f"message={job.get('message', '')}")

    run_id = str(job.get("run_id") or "")
    if not run_id:
        return 1

    run_dir = ROOT / ".omx" / "runs" / run_id
    print(f"run_dir={run_dir}")
    _print_run_evidence(run_dir)
    _print_environment_hint(run_dir)

    if job["status"] != "done":
        return 1
    docker_log = run_dir / "logs" / "docker_sandbox.jsonl"
    if not docker_log.exists():
        print("docker_log_missing=true")
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


def _wait_for_job(job_id: str) -> dict:
    repository = SQLiteJobRepository(JOB_DB)
    deadline = time.time() + TIMEOUT_SECONDS
    while time.time() < deadline:
        job = repository.get(job_id)
        if job and job["status"] in {"done", "failed"}:
            return job
        time.sleep(0.2)
    raise TimeoutError(f"job did not finish within {TIMEOUT_SECONDS}s: {job_id}")


def _print_run_evidence(run_dir: Path) -> None:
    for relative in [
        Path("run_state.json"),
        Path("logs") / "docker_sandbox.jsonl",
        Path("attempts") / "001" / "hard_checks.json",
        Path("attempts") / "001" / "quality_report.json",
    ]:
        path = run_dir / relative
        print(f"{relative.as_posix()}_exists={path.exists()}")

    docker_log = run_dir / "logs" / "docker_sandbox.jsonl"
    if docker_log.exists():
        lines = docker_log.read_text(encoding="utf-8", errors="replace").splitlines()
        if lines:
            print(f"docker_log_last={lines[-1]}")

    quality_report = run_dir / "attempts" / "001" / "quality_report.json"
    if quality_report.exists():
        payload = json.loads(quality_report.read_text(encoding="utf-8"))
        print(f"quality_score={payload.get('quality_score')} quality_passed={payload.get('passed')}")


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
