from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SMOKE_ROOT = ROOT / ".tmp" / "real-external-agent-smoke"
ENABLE_ENV = "OMX_RUN_REAL_EXTERNAL_AGENT_SMOKE"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Opt-in smoke for real codex/omx external-agent commands through the wrapper."
    )
    parser.add_argument(
        "--runtime",
        choices=["codex", "omx"],
        default=os.environ.get("OMX_REAL_EXTERNAL_AGENT_RUNTIME", "codex"),
    )
    args = parser.parse_args()

    if os.environ.get(ENABLE_ENV) != "1":
        print(f"real_external_agent_smoke=skipped reason=set_{ENABLE_ENV}=1")
        return 0

    missing = missing_backend_env(args.runtime)
    if missing:
        print(f"real_external_agent_smoke=skipped reason=missing_backend_env vars={','.join(missing)}")
        return 0

    smoke_dir = SMOKE_ROOT / args.runtime
    worktree = smoke_dir / "worktree"
    runs_dir = smoke_dir / ".omx" / "runs"
    reset_smoke_workspace(smoke_dir, worktree)
    task_path = write_task(args.runtime, smoke_dir, worktree)

    completed = run_orchestrator(task_path, smoke_dir)
    print(completed.stdout, end="")
    if completed.stderr:
        print(completed.stderr, end="", file=sys.stderr)
    if completed.returncode != 0:
        return completed.returncode

    run_id = extract_value(completed.stdout, "run_id")
    status = extract_value(completed.stdout, "status")
    print(f"real_smoke_runtime={args.runtime}")
    print(f"real_smoke_run_id={run_id}")
    print(f"real_smoke_status={status}")
    if status not in {"done", "RunStatus.DONE"}:
        return 1

    run_dir = runs_dir / run_id
    evidence = collect_evidence(run_dir)
    for key, value in evidence.items():
        print(f"{key}={value}")
    if not all(evidence.values()):
        return 1

    wrapper_evidence = collect_wrapper_evidence(run_dir)
    for key, value in wrapper_evidence.items():
        print(f"{key}={value}")
    if (
        wrapper_evidence["wrapper_runtime"] != args.runtime
        or wrapper_evidence["wrapper_roles"] != "coder,reviewer"
        or wrapper_evidence["wrapper_exit_codes"] != "0,0"
        or wrapper_evidence["wrapper_backend_commands"] != "2"
    ):
        return 1

    review = json.loads((run_dir / "attempts" / "001" / "review.json").read_text(encoding="utf-8"))
    if review.get("recommended_next_action") != "pass":
        print(json.dumps(review, ensure_ascii=False, indent=2))
        return 1

    print("real_external_agent_smoke=passed")
    return 0


def missing_backend_env(runtime: str) -> list[str]:
    prefix = f"OMX_{runtime.upper()}"
    required = [f"{prefix}_CODER_COMMAND", f"{prefix}_REVIEWER_COMMAND"]
    return [name for name in required if not os.environ.get(name)]


def reset_smoke_workspace(smoke_dir: Path, worktree: Path) -> None:
    if smoke_dir.exists():
        shutil.rmtree(smoke_dir)
    worktree.mkdir(parents=True)
    (worktree / "calculator.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")


def write_task(runtime: str, smoke_dir: Path, worktree: Path) -> Path:
    wrapper = ROOT / "scripts" / "run_external_agent.py"
    task = {
        "task_id": f"task-real-{runtime}-external-agent-smoke",
        "title": f"Real {runtime} external agent smoke",
        "description": (
            "Opt-in smoke for a configured real external agent command. "
            "The command may no-op for coder, but reviewer must return valid review JSON."
        ),
        "change_type": "bugfix",
        "repo_path": str(worktree),
        "worktree_path": str(worktree),
        "allowed_paths": ["calculator.py"],
        "forbidden_paths": [".env"],
        "allowed_command_prefixes": ["python", sys.executable],
        "check_commands": {"test": None, "lint": None, "typecheck": None},
        "agent_mode": runtime,
        "agent_commands": {
            "coder": wrapper_command(runtime, "coder", wrapper),
            "fixer": wrapper_command(runtime, "fixer", wrapper),
            "reviewer": wrapper_command(runtime, "reviewer", wrapper),
        },
        "max_attempts": 1,
        "max_review_json_retries": 1,
    }
    task_path = smoke_dir / f"task.real-{runtime}-external-agent-smoke.json"
    task_path.write_text(json.dumps(task, ensure_ascii=False, indent=2), encoding="utf-8")
    return task_path


def wrapper_command(runtime: str, role: str, wrapper: Path) -> str:
    output_name = f"external_agent_{role}_last_message.txt"
    return (
        f'python "{wrapper}" --runtime {runtime} --role {role} --task-id {{task_id}} '
        f'--prompt-file {{prompt_file}} --run-dir {{run_dir}} --worktree {{worktree}} '
        f'--stdin-prompt --output-last-message "{{run_dir}}/attempts/{output_name}"'
    )


def run_orchestrator(task_path: Path, smoke_dir: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run(
        [
            "python",
            "-m",
            "orchestrator.interfaces.cli.main",
            "--task",
            str(task_path),
            "--agent",
            json.loads(task_path.read_text(encoding="utf-8"))["agent_mode"],
        ],
        cwd=smoke_dir,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def extract_value(output: str, key: str) -> str:
    for line in output.splitlines():
        for part in line.split():
            if part.startswith(key + "="):
                return part.split("=", 1)[1]
    return ""


def collect_evidence(run_dir: Path) -> dict[str, bool]:
    return {
        "run_state_exists": (run_dir / "run_state.json").exists(),
        "agent_log_exists": (run_dir / "logs" / "agent.log").exists(),
        "wrapper_log_exists": (run_dir / "logs" / "external_agent_wrapper.log").exists(),
        "review_json_exists": (run_dir / "attempts" / "001" / "review.json").exists(),
        "quality_report_exists": (run_dir / "attempts" / "001" / "quality_report.json").exists(),
        "final_report_exists": (run_dir / "final_report.md").exists(),
    }


def collect_wrapper_evidence(run_dir: Path) -> dict[str, str]:
    entries = parse_wrapper_log(run_dir / "logs" / "external_agent_wrapper.log")
    roles = sorted({entry.get("role", "") for entry in entries if entry.get("role")})
    runtimes = sorted({entry.get("runtime", "") for entry in entries if entry.get("runtime")})
    exit_codes = [entry.get("exit_code", "") for entry in entries if entry.get("exit_code")]
    backend_commands = [entry.get("backend_command", "") for entry in entries if entry.get("backend_command")]
    return {
        "wrapper_runtime": ",".join(runtimes),
        "wrapper_roles": ",".join(roles),
        "wrapper_exit_codes": ",".join(exit_codes),
        "wrapper_backend_commands": str(len(backend_commands)),
    }


def parse_wrapper_log(path: Path) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    current: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped == "---":
            if current:
                entries.append(current)
                current = {}
            continue
        if "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        current[key.strip()] = value.strip()
    if current:
        entries.append(current)
    return entries


if __name__ == "__main__":
    raise SystemExit(main())
