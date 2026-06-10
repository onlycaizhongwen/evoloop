from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SMOKE_DIR = ROOT / ".tmp" / "external-agent-closed-loop-smoke"
WORKTREE = SMOKE_DIR / "worktree"
RUNS_DIR = SMOKE_DIR / ".omx" / "runs"


def main() -> int:
    reset_smoke_workspace()
    task_path = write_task()
    completed = run_orchestrator(task_path)
    print(completed.stdout, end="")
    if completed.stderr:
        print(completed.stderr, end="", file=sys.stderr)
    if completed.returncode != 0:
        return completed.returncode

    run_id = extract_value(completed.stdout, "run_id")
    status = extract_value(completed.stdout, "status")
    print(f"smoke_run_id={run_id}")
    print(f"smoke_status={status}")
    if status not in {"done", "RunStatus.DONE"}:
        return 1

    run_dir = RUNS_DIR / run_id
    evidence = collect_evidence(run_dir)
    for key, value in evidence.items():
        print(f"{key}={value}")
    if not all(evidence.values()):
        return 1
    wrapper_evidence = collect_wrapper_evidence(run_dir)
    for key, value in wrapper_evidence.items():
        print(f"{key}={value}")
    if (
        wrapper_evidence["wrapper_runtime"] != "codex"
        or wrapper_evidence["wrapper_roles"] != "coder,reviewer"
        or wrapper_evidence["wrapper_exit_codes"] != "0,0"
        or wrapper_evidence["wrapper_backend_commands"] != "2"
    ):
        return 1

    review = json.loads((run_dir / "attempts" / "001" / "review.json").read_text(encoding="utf-8"))
    if review.get("recommended_next_action") != "pass":
        print(json.dumps(review, ensure_ascii=False, indent=2))
        return 1

    print("external_agent_closed_loop_smoke=passed")
    return 0


def reset_smoke_workspace() -> None:
    if SMOKE_DIR.exists():
        shutil.rmtree(SMOKE_DIR)
    WORKTREE.mkdir(parents=True)
    (WORKTREE / "calculator.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")


def write_task() -> Path:
    backend = SMOKE_DIR / "external_backend.py"
    backend.write_text(
        "\n".join(
            [
                "from __future__ import annotations",
                "import json",
                "import pathlib",
                "import sys",
                "",
                "role = sys.argv[1]",
                "task_id = sys.argv[2]",
                "prompt_file = pathlib.Path(sys.argv[3])",
                "marker = pathlib.Path(sys.argv[4])",
                "prompt = prompt_file.read_text(encoding='utf-8')",
                "marker.parent.mkdir(parents=True, exist_ok=True)",
                "marker.write_text(role + ':' + task_id + ':' + str(len(prompt)), encoding='utf-8')",
                "if role == 'reviewer':",
                "    print(json.dumps({",
                "        'schema_version': '1.0',",
                "        'task_id': task_id,",
                "        'pass': True,",
                "        'confidence': 92,",
                "        'summary': 'external closed-loop smoke review passed',",
                "        'issues': [],",
                "        'blocking': False,",
                "        'recommended_next_action': 'pass',",
                "    }))",
                "else:",
                "    print(role + ' backend ok')",
            ]
        ),
        encoding="utf-8",
    )
    marker = SMOKE_DIR / "backend-marker.txt"
    wrapper = ROOT / "scripts" / "run_external_agent.py"
    coder_command = wrapper_command("coder", wrapper)
    fixer_command = wrapper_command("fixer", wrapper)
    reviewer_command = wrapper_command("reviewer", wrapper)
    task = {
        "task_id": "task-external-agent-closed-loop-smoke",
        "title": "External agent closed-loop smoke",
        "description": "Exercise the external command agent wrapper through the orchestrator run loop.",
        "change_type": "bugfix",
        "repo_path": str(WORKTREE),
        "worktree_path": str(WORKTREE),
        "allowed_paths": ["calculator.py"],
        "forbidden_paths": [".env"],
        "allowed_command_prefixes": ["python", sys.executable],
        "check_commands": {"test": None, "lint": None, "typecheck": None},
        "agent_mode": "codex",
        "agent_commands": {
            "coder": coder_command,
            "fixer": fixer_command,
            "reviewer": reviewer_command,
        },
        "max_attempts": 1,
        "max_review_json_retries": 1,
    }
    write_backend_env(backend, marker)
    task_path = SMOKE_DIR / "task.external-agent-closed-loop-smoke.json"
    task_path.write_text(json.dumps(task, ensure_ascii=False, indent=2), encoding="utf-8")
    return task_path


def wrapper_command(role: str, wrapper: Path) -> str:
    return (
        f'python "{wrapper}" --runtime codex --role {role} --task-id {{task_id}} '
        f"--prompt-file {{prompt_file}} --run-dir {{run_dir}} --worktree {{worktree}}"
    )


def write_backend_env(backend: Path, marker: Path) -> None:
    payload = {
        "OMX_CODEX_CODER_COMMAND": f'python "{backend}" coder {{task_id}} {{prompt_file}} "{marker}"',
        "OMX_CODEX_FIXER_COMMAND": f'python "{backend}" fixer {{task_id}} {{prompt_file}} "{marker}"',
        "OMX_CODEX_REVIEWER_COMMAND": f'python "{backend}" reviewer {{task_id}} {{prompt_file}} "{marker}"',
    }
    (SMOKE_DIR / "backend-env.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def run_orchestrator(task_path: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    env.update(json.loads((SMOKE_DIR / "backend-env.json").read_text(encoding="utf-8")))
    return subprocess.run(
        ["python", "-m", "orchestrator.interfaces.cli.main", "--task", str(task_path), "--agent", "codex"],
        cwd=SMOKE_DIR,
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
        "backend_marker_exists": (SMOKE_DIR / "backend-marker.txt").exists(),
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
