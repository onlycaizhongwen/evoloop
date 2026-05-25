from __future__ import annotations

import subprocess
import sys


def test_real_project_smoke_script_passes():
    completed = subprocess.run(
        [sys.executable, "scripts/run_real_project_smoke.py"],
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "preview_ok=true" in completed.stdout
    assert "rerun_status=done" in completed.stdout
    assert "real_project_smoke=passed" in completed.stdout
