from __future__ import annotations

import json
import subprocess
import sys

import pytest

from scripts import run_production_readiness_smoke as readiness


def test_production_readiness_smoke_script_passes():
    completed = subprocess.run(
        [sys.executable, "scripts/run_production_readiness_smoke.py"],
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "stage=demo_readiness status=passed" in completed.stdout
    assert "stage=external_agent_closed_loop status=passed" in completed.stdout
    assert "stage=real_external_agent_gate status=skipped" in completed.stdout
    assert "stage=web_browser_http status=passed" in completed.stdout
    assert "production_readiness_summary passed=3 skipped=1 failed=0" in completed.stdout
    assert "production_readiness_smoke=passed" in completed.stdout


def test_production_readiness_writes_success_summary_json(monkeypatch, tmp_path):
    stages = [
        readiness.SmokeStage(name="pass_stage", command=["pass"], pass_marker="passed_marker"),
        readiness.SmokeStage(name="skip_stage", command=["skip"], pass_marker="never", skip_marker="skip_marker"),
    ]
    executions = [
        readiness.StageExecution(returncode=0, stdout="passed_marker\n"),
        readiness.StageExecution(returncode=0, stdout="skip_marker\n"),
    ]
    summary_path = tmp_path / "nested" / "summary.json"

    monkeypatch.setattr(readiness, "STAGES", stages)
    monkeypatch.setattr(readiness, "run_stage", lambda _stage: executions.pop(0))

    assert readiness.main(["--summary-json", str(summary_path)]) == 0
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["schema_version"] == 1
    assert summary["generated_at"].endswith("+00:00")
    assert summary["overall_status"] == "passed"
    assert summary["passed"] == 1
    assert summary["skipped"] == 1
    assert summary["failed"] == 0
    assert [stage["name"] for stage in summary["stages"]] == ["pass_stage", "skip_stage"]
    assert all("duration_seconds" in stage for stage in summary["stages"])


def test_production_readiness_reports_timeout_without_traceback(monkeypatch, capsys):
    stage = readiness.SmokeStage(
        name="slow_stage",
        command=[sys.executable, "-c", "pass"],
        pass_marker="never",
        timeout_seconds=7,
    )

    def fake_run(*_args, **_kwargs):
        raise subprocess.TimeoutExpired(cmd=stage.command, timeout=7, output="partial out", stderr="partial err")

    monkeypatch.setattr(readiness, "STAGES", [stage])
    monkeypatch.setattr(subprocess, "run", fake_run)

    assert readiness.main() == 124
    output = capsys.readouterr().out
    assert "stage=slow_stage error=timed out after 7s" in output
    assert "stage=slow_stage status=failed exit_code=124" in output
    assert "production_readiness_summary passed=0 skipped=0 failed=1" in output
    assert "production_readiness_smoke=failed" in output


def test_production_readiness_writes_failure_summary_json(monkeypatch, tmp_path):
    stage = readiness.SmokeStage(
        name="slow_stage",
        command=[sys.executable, "-c", "pass"],
        pass_marker="never",
        timeout_seconds=7,
    )
    summary_path = tmp_path / "summary.json"

    def fake_run(*_args, **_kwargs):
        raise subprocess.TimeoutExpired(cmd=stage.command, timeout=7, output="partial out", stderr="partial err")

    monkeypatch.setattr(readiness, "STAGES", [stage])
    monkeypatch.setattr(subprocess, "run", fake_run)

    assert readiness.main(["--summary-json", str(summary_path)]) == 124
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["schema_version"] == 1
    assert summary["generated_at"].endswith("+00:00")
    assert summary["overall_status"] == "failed"
    assert summary["passed"] == 0
    assert summary["skipped"] == 0
    assert summary["failed"] == 1
    assert summary["stages"] == [
        {
            "name": "slow_stage",
            "status": "failed",
            "exit_code": 124,
            "command": [sys.executable, "-c", "pass"],
            "error": "timed out after 7s",
            "duration_seconds": summary["stages"][0]["duration_seconds"],
        }
    ]
    assert summary["stages"][0]["duration_seconds"] >= 0


def test_production_readiness_reports_launch_failure_without_traceback(monkeypatch, capsys):
    stage = readiness.SmokeStage(
        name="missing_command",
        command=["missing-command"],
        pass_marker="never",
    )

    def fake_run(*_args, **_kwargs):
        raise FileNotFoundError("missing-command")

    monkeypatch.setattr(readiness, "STAGES", [stage])
    monkeypatch.setattr(subprocess, "run", fake_run)

    assert readiness.main() == 127
    output = capsys.readouterr().out
    assert "stage=missing_command error=FileNotFoundError: missing-command" in output
    assert "stage=missing_command status=failed exit_code=127" in output
    assert "production_readiness_summary passed=0 skipped=0 failed=1" in output
    assert "production_readiness_smoke=failed" in output


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, ""),
        ("text", "text"),
        (b"byte text", "byte text"),
        (b"\xff", "\ufffd"),
    ],
)
def test_text_or_empty_normalizes_timeout_output(value, expected):
    assert readiness.text_or_empty(value) == expected
