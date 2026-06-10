from __future__ import annotations

import subprocess
import sys


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
