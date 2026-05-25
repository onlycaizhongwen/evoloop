from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    reset_demo_workspaces()

    print("== Unified diff patch-only smoke ==")
    unified = run_cli(
        [
            "--task",
            "examples/task.omx-patch-unified-diff-smoke.json",
            "--agent",
            "omx_patch",
            "--real-checks",
        ]
    )
    unified_run_id = extract("run_id", unified.stdout)
    print(unified.stdout.strip())
    print(f"unified_final_report=.omx/runs/{unified_run_id}/final_report.md")

    print("\n== Pending patch approval smoke ==")
    approval = run_cli(
        [
            "--task",
            "examples/task.omx-patch-approval-smoke.json",
            "--agent",
            "omx_patch",
            "--real-checks",
        ]
    )
    approval_run_id = extract("run_id", approval.stdout)
    print(approval.stdout.strip())

    print("\n== List pending patch ==")
    listed = run_cli(["patches", "list", "--run-id", approval_run_id])
    patch_name = extract("patch", listed.stdout)
    print(listed.stdout.strip())

    print("\n== Approve, apply, and rerun validation ==")
    applied = run_cli(
        [
            "patches",
            "apply",
            "--run-id",
            approval_run_id,
            "--patch",
            patch_name,
            "--reviewer",
            "demo",
            "--note",
            "approved by demo script",
            "--rerun-task",
        ]
    )
    print(applied.stdout.strip())
    print(f"pending_patch_json=.omx/runs/{approval_run_id}/pending-patches/{patch_name}")
    return 0


def reset_demo_workspaces() -> None:
    unified_dir = ROOT / ".tmp" / "omx-unified-diff-smoke"
    unified_dir.mkdir(parents=True, exist_ok=True)
    (unified_dir / "calculator.py").write_text("def add(a, b):\n    return a - b\n", encoding="utf-8")
    (unified_dir / "test_calculator.py").write_text(
        "from calculator import add\n\n\n"
        "def test_add():\n"
        "    assert add(1, 2) == 3\n",
        encoding="utf-8",
    )

    approval_dir = ROOT / ".tmp" / "omx-real-smoke"
    approval_dir.mkdir(parents=True, exist_ok=True)
    (approval_dir / "old_file.py").write_text("obsolete\n", encoding="utf-8")


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


if __name__ == "__main__":
    raise SystemExit(main())
