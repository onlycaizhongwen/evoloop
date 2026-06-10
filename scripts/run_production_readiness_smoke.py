from __future__ import annotations

import subprocess
import sys
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


def main() -> int:
    results: list[tuple[SmokeStage, str, subprocess.CompletedProcess[str]]] = []
    for stage in STAGES:
        print(f"stage={stage.name} status=running command={format_command(stage.command)}")
        completed = subprocess.run(
            stage.command,
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
            timeout=stage.timeout_seconds,
        )
        status = classify_stage(stage, completed)
        results.append((stage, status, completed))
        print_stage_output(stage, completed)
        print(f"stage={stage.name} status={status} exit_code={completed.returncode}")
        if status == "failed":
            print_summary(results)
            print("production_readiness_smoke=failed")
            return completed.returncode or 1

    print_summary(results)
    print("production_readiness_smoke=passed")
    return 0


def classify_stage(stage: SmokeStage, completed: subprocess.CompletedProcess[str]) -> str:
    combined = completed.stdout + completed.stderr
    if completed.returncode == 0 and stage.pass_marker in combined:
        return "passed"
    if completed.returncode == 0 and stage.skip_marker and stage.skip_marker in combined:
        return "skipped"
    return "failed"


def print_stage_output(stage: SmokeStage, completed: subprocess.CompletedProcess[str]) -> None:
    if completed.stdout.strip():
        print(f"stage={stage.name} stdout_begin")
        print(completed.stdout.rstrip())
        print(f"stage={stage.name} stdout_end")
    if completed.stderr.strip():
        print(f"stage={stage.name} stderr_begin")
        print(completed.stderr.rstrip())
        print(f"stage={stage.name} stderr_end")


def print_summary(results: list[tuple[SmokeStage, str, subprocess.CompletedProcess[str]]]) -> None:
    passed = sum(1 for _stage, status, _completed in results if status == "passed")
    skipped = sum(1 for _stage, status, _completed in results if status == "skipped")
    failed = sum(1 for _stage, status, _completed in results if status == "failed")
    print(f"production_readiness_summary passed={passed} skipped={skipped} failed={failed}")
    for stage, status, completed in results:
        print(f"production_readiness_stage name={stage.name} status={status} exit_code={completed.returncode}")


def format_command(command: list[str]) -> str:
    return " ".join(command)


if __name__ == "__main__":
    raise SystemExit(main())
