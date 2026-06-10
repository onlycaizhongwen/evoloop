from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from scripts.run_web_browser_smoke import STALE_WORKSPACE_SECONDS, cleanup_stale_smoke_workspaces


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
    assert "web_external_agent_provenance_smoke=passed" in completed.stdout
    assert "web_browser_smoke=passed" in completed.stdout


def test_web_browser_smoke_removes_only_stale_process_workspaces(tmp_path: Path):
    root = tmp_path / "web-browser-smoke"
    stale = root / "run-stale"
    fresh = root / "run-fresh"
    unrelated = root / "keep"
    current = root / f"run-{os.getpid()}"
    for path in [stale, fresh, unrelated, current]:
        path.mkdir(parents=True)
    now = 2_000_000.0
    old_time = now - STALE_WORKSPACE_SECONDS - 5
    fresh_time = now - STALE_WORKSPACE_SECONDS + 5
    os.utime(stale, (old_time, old_time))
    os.utime(fresh, (fresh_time, fresh_time))
    os.utime(unrelated, (old_time, old_time))
    os.utime(current, (old_time, old_time))

    removed = cleanup_stale_smoke_workspaces(root=root, now=now, current_dir=current)

    assert removed == 1
    assert not stale.exists()
    assert fresh.exists()
    assert unrelated.exists()
    assert current.exists()
