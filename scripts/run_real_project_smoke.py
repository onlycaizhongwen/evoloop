from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SMOKE_DIR = ROOT / ".tmp" / "real-project-smoke"
TASK_PATH = ROOT / ".tmp" / "real-project-smoke-task.json"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.infrastructure.patches.pending_patch_service import PendingPatchService
from orchestrator.infrastructure.persistence.sqlite_job_repository import SQLiteJobRepository


def main() -> int:
    reset_smoke_project()
    write_task()

    print("== Real project pending patch smoke ==")
    run = run_cli(["--task", str(TASK_PATH), "--agent", "omx_patch", "--real-checks"])
    run_id = extract("run_id", run.stdout)
    assert_contains(run.stdout, "status=halted", "initial run must wait for patch approval")
    print(run.stdout.strip())

    patch_summaries = PendingPatchService().list(run_id=run_id)
    assert_true(len(patch_summaries) == 1, f"expected one pending patch, got {len(patch_summaries)}")
    patch = patch_summaries[0]
    patch_name = patch["patch"]
    assert_true(patch["status"] == "pending", f"patch status must be pending: {patch}")
    assert_true(patch["operations"][0]["op"] == "replace_text", "operation preview missing replace_text")
    assert_contains(patch["operations"][0]["preview"], "return a + b", "operation preview must include new code")
    print(f"preview_ok=true patch={patch_name}")

    print("\n== Approve patch and rerun validation ==")
    applied = run_cli(
        [
            "patches",
            "apply",
            "--run-id",
            run_id,
            "--patch",
            patch_name,
            "--reviewer",
            "real-project-smoke",
            "--note",
            "approved by smoke",
            "--rerun-task",
        ]
    )
    assert_contains(applied.stdout, "status=applied", "patch apply failed")
    assert_contains(applied.stdout, "rerun_status=done", "post-apply rerun did not finish")
    assert_contains(applied.stdout, "rerun_reason=quality gate passed", "quality gate did not pass")
    print(applied.stdout.strip())

    assert_contains((SMOKE_DIR / "calculator.py").read_text(encoding="utf-8"), "return a + b", "file was not patched")
    test_result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q"],
        cwd=SMOKE_DIR,
        text=True,
        capture_output=True,
        check=False,
    )
    assert_true(test_result.returncode == 0, test_result.stdout + test_result.stderr)
    print(test_result.stdout.strip())

    print("\n== SQLite job repository smoke ==")
    jobs = SQLiteJobRepository(ROOT / ".omx" / "orchestrator.db").list_recent(limit=5)
    print(f"sqlite_web_jobs_visible={bool(jobs)}")

    print("\nreal_project_smoke=passed")
    return 0


def reset_smoke_project() -> None:
    if SMOKE_DIR.exists():
        shutil.rmtree(SMOKE_DIR)
    SMOKE_DIR.mkdir(parents=True)
    (SMOKE_DIR / "calculator.py").write_text("def add(a, b):\n    return a - b\n", encoding="utf-8")
    (SMOKE_DIR / "test_calculator.py").write_text(
        "from calculator import add\n\n\n"
        "def test_add():\n"
        "    assert add(1, 2) == 3\n",
        encoding="utf-8",
    )


def write_task() -> None:
    python = f'"{sys.executable}"'
    payload = {
        "task_id": "task-real-project-smoke-001",
        "title": "Real project smoke",
        "description": "Generate a patch JSON that fixes calculator.add from a - b to a + b.",
        "change_type": "bugfix",
        "repo_path": str(SMOKE_DIR),
        "worktree_path": str(SMOKE_DIR),
        "allowed_paths": ["calculator.py"],
        "forbidden_paths": [".env", "secrets", "deploy/prod"],
        "allowed_command_prefixes": ["python", "python -m pytest", "pytest"],
        "check_commands": {"test": f"{python} -m pytest -q", "lint": None, "typecheck": None},
        "agent_mode": "omx_patch",
        "agent_commands": {
            "patch_coder": f'{python} "{ROOT / "examples" / "patch_smoke_backend.py"}" {{task_id}}',
            "reviewer": f'{python} "{ROOT / "examples" / "shell_reviewer.py"}" {{task_id}}',
        },
        "patch_auto_apply": False,
        "patch_approval_risk_threshold": 10,
        "patch_require_approval_on_delete": True,
        "max_attempts": 1,
        "max_review_json_retries": 1,
        "heartbeat_interval_seconds": 10,
        "command_timeout_seconds": 120,
        "risk_level": "medium",
    }
    TASK_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def run_cli(args: list[str]) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        [sys.executable, "-m", "orchestrator.interfaces.cli.main", *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        print(completed.stdout, end="")
        print(completed.stderr, end="", file=sys.stderr)
        raise SystemExit(completed.returncode)
    return completed


def extract(key: str, text: str) -> str:
    match = re.search(rf"{re.escape(key)}=([^ \r\n]+)", text)
    if not match:
        raise RuntimeError(f"could not find {key}=... in output:\n{text}")
    return match.group(1)


def assert_contains(text: str, expected: str, message: str) -> None:
    assert_true(expected in text, f"{message}: expected {expected!r} in\n{text}")


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


if __name__ == "__main__":
    raise SystemExit(main())
