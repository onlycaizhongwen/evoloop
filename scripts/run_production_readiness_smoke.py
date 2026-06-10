from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import UTC, datetime
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class SmokeStage:
    name: str
    command: list[str]
    pass_marker: str
    skip_marker: str | None = None
    timeout_seconds: int = 180


@dataclass(frozen=True)
class StageExecution:
    returncode: int
    stdout: str = ""
    stderr: str = ""
    error: str | None = None
    duration_seconds: float = 0.0


STAGES = [
    SmokeStage(
        name="demo_readiness",
        command=[sys.executable, "scripts/run_demo_readiness_smoke.py"],
        pass_marker="demo_readiness_smoke=passed",
    ),
    SmokeStage(
        name="external_agent_closed_loop",
        command=[sys.executable, "scripts/run_external_agent_closed_loop_smoke.py"],
        pass_marker="external_agent_closed_loop_smoke=passed",
    ),
    SmokeStage(
        name="real_external_agent_gate",
        command=[sys.executable, "scripts/run_real_external_agent_smoke.py"],
        pass_marker="real_external_agent_smoke=passed",
        skip_marker="real_external_agent_smoke=skipped",
    ),
    SmokeStage(
        name="web_browser_http",
        command=[sys.executable, "scripts/run_web_browser_smoke.py"],
        pass_marker="web_browser_smoke=passed",
        timeout_seconds=240,
    ),
]


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    results: list[tuple[SmokeStage, str, StageExecution]] = []
    for stage in STAGES:
        print(f"stage={stage.name} status=running command={format_command(stage.command)}")
        completed = run_stage(stage)
        status = classify_stage(stage, completed)
        results.append((stage, status, completed))
        print_stage_output(stage, completed)
        print(f"stage={stage.name} status={status} exit_code={completed.returncode}")
        if status == "failed":
            print_summary(results)
            print("production_readiness_smoke=failed")
            write_summary_json(args.summary_json, results, overall_status="failed")
            return completed.returncode or 1

    print_summary(results)
    print("production_readiness_smoke=passed")
    write_summary_json(args.summary_json, results, overall_status="passed")
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the aggregate production readiness smoke suite.")
    parser.add_argument(
        "--summary-json",
        type=Path,
        help="Optional path for a machine-readable pass/skip/fail summary.",
    )
    return parser.parse_args([] if argv is None else argv)


def run_stage(stage: SmokeStage) -> StageExecution:
    started = time.monotonic()
    try:
        completed = subprocess.run(
            stage.command,
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
            timeout=stage.timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        return StageExecution(
            returncode=124,
            stdout=text_or_empty(exc.stdout),
            stderr=text_or_empty(exc.stderr),
            error=f"timed out after {stage.timeout_seconds}s",
            duration_seconds=elapsed_seconds(started),
        )
    except OSError as exc:
        return StageExecution(
            returncode=127,
            error=f"{type(exc).__name__}: {exc}",
            duration_seconds=elapsed_seconds(started),
        )
    return StageExecution(
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
        duration_seconds=elapsed_seconds(started),
    )


def classify_stage(stage: SmokeStage, completed: StageExecution) -> str:
    combined = completed.stdout + completed.stderr
    if completed.returncode == 0 and stage.pass_marker in combined:
        return "passed"
    if completed.returncode == 0 and stage.skip_marker and stage.skip_marker in combined:
        return "skipped"
    return "failed"


def print_stage_output(stage: SmokeStage, completed: StageExecution) -> None:
    if completed.error:
        print(f"stage={stage.name} error={completed.error}")
    if completed.stdout.strip():
        print(f"stage={stage.name} stdout_begin")
        print(completed.stdout.rstrip())
        print(f"stage={stage.name} stdout_end")
    if completed.stderr.strip():
        print(f"stage={stage.name} stderr_begin")
        print(completed.stderr.rstrip())
        print(f"stage={stage.name} stderr_end")


def print_summary(results: list[tuple[SmokeStage, str, StageExecution]]) -> None:
    passed = sum(1 for _stage, status, _completed in results if status == "passed")
    skipped = sum(1 for _stage, status, _completed in results if status == "skipped")
    failed = sum(1 for _stage, status, _completed in results if status == "failed")
    print(f"production_readiness_summary passed={passed} skipped={skipped} failed={failed}")
    for stage, status, completed in results:
        print(f"production_readiness_stage name={stage.name} status={status} exit_code={completed.returncode}")


def write_summary_json(
    path: Path | None,
    results: list[tuple[SmokeStage, str, StageExecution]],
    *,
    overall_status: str,
) -> None:
    if path is None:
        return
    summary = build_summary(results, overall_status=overall_status)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"production_readiness_summary_json={path}")


def build_summary(
    results: list[tuple[SmokeStage, str, StageExecution]],
    *,
    overall_status: str,
) -> dict[str, object]:
    return {
        "schema_version": 1,
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "overall_status": overall_status,
        "environment": build_environment_summary(),
        "passed": sum(1 for _stage, status, _completed in results if status == "passed"),
        "skipped": sum(1 for _stage, status, _completed in results if status == "skipped"),
        "failed": sum(1 for _stage, status, _completed in results if status == "failed"),
        "stages": [
            {
                "name": stage.name,
                "status": status,
                "exit_code": completed.returncode,
                "command": stage.command,
                "error": completed.error,
                "duration_seconds": completed.duration_seconds,
            }
            for stage, status, completed in results
        ],
    }


def build_environment_summary() -> dict[str, object]:
    codex_command = shutil.which("codex")
    omx_command = shutil.which("omx")
    required_codex_env = ["OMX_CODEX_CODER_COMMAND", "OMX_CODEX_REVIEWER_COMMAND"]
    required_omx_env = ["OMX_OMX_CODER_COMMAND", "OMX_OMX_REVIEWER_COMMAND"]
    missing_codex_env = [name for name in required_codex_env if not os.environ.get(name)]
    missing_omx_env = [name for name in required_omx_env if not os.environ.get(name)]
    return {
        "codex_command": codex_command,
        "omx_command": omx_command,
        "playwright_python_installed": importlib.util.find_spec("playwright") is not None,
        "real_external_agent": {
            "opt_in_enabled": os.environ.get("OMX_RUN_REAL_EXTERNAL_AGENT_SMOKE") == "1",
            "codex_backend_env_ready": not missing_codex_env,
            "codex_backend_env_missing": missing_codex_env,
            "omx_backend_env_ready": not missing_omx_env,
            "omx_backend_env_missing": missing_omx_env,
        },
    }


def format_command(command: list[str]) -> str:
    return " ".join(command)


def text_or_empty(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode(errors="replace")
    return value


def elapsed_seconds(started: float) -> float:
    return round(time.monotonic() - started, 3)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
