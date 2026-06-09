from __future__ import annotations

import subprocess
import sys


def test_web_browser_smoke_script_passes():
    completed = subprocess.run(
        [sys.executable, "scripts/run_web_browser_smoke.py"],
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "health_overall=pass" in completed.stdout
    assert "audit_archive_smoke=passed" in completed.stdout
    assert "web_browser_smoke=passed" in completed.stdout
