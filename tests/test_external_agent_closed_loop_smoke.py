from __future__ import annotations

import subprocess
import sys


def test_external_agent_closed_loop_smoke_script_passes():
    completed = subprocess.run(
        [sys.executable, "scripts/run_external_agent_closed_loop_smoke.py"],
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "smoke_status=done" in completed.stdout
    assert "external_agent_closed_loop_smoke=passed" in completed.stdout
