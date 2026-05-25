from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SMOKE_DIR = ROOT / ".tmp" / "omx-team-runtime-smoke"
PROMPT_FILE = SMOKE_DIR / "team_prompt.txt"
RUN_DIR = SMOKE_DIR / "run"
RESULT_FILE = SMOKE_DIR / "team_result.json"


def main() -> int:
    SMOKE_DIR.mkdir(parents=True, exist_ok=True)
    PROMPT_FILE.write_text(
        "Smoke task: return a valid team_result JSON with no real worktree edits.",
        encoding="utf-8",
    )
    command = [
        sys.executable,
        str(ROOT / "scripts" / "run_omx_team_patch.py"),
        "task-omx-team-runtime-smoke",
        str(PROMPT_FILE),
        str(RUN_DIR),
        "--runtime",
        "team",
        "--output-last-message",
        str(RESULT_FILE),
        "--team-workers",
        "1",
        "--team-agent-type",
        "executor",
        "--team-timeout-ms",
        "120000",
    ]
    completed = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
    print(completed.stdout, end="")
    if completed.stderr:
        print(completed.stderr, end="", file=sys.stderr)
    if completed.returncode != 0:
        _print_diagnostics()
        return completed.returncode
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        print(f"smoke output was not valid JSON: {exc}", file=sys.stderr)
        _print_diagnostics()
        return 1
    if payload.get("task_id") != "task-omx-team-runtime-smoke":
        print(f"unexpected task_id: {payload.get('task_id')}", file=sys.stderr)
        return 1
    return 0


def _print_diagnostics() -> None:
    log_path = RUN_DIR / "logs" / "omx_team_patch_backend.json"
    if log_path.exists():
        print(f"\nbackend log: {log_path}", file=sys.stderr)
        print(log_path.read_text(encoding="utf-8", errors="replace"), file=sys.stderr)
    prompt_path = RUN_DIR / "attempts" / "omx_team_runtime_prompt.txt"
    if prompt_path.exists():
        print(f"\nruntime prompt: {prompt_path}", file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
