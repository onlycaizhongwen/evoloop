from __future__ import annotations

import os
import subprocess
import sys


def test_real_external_agent_smoke_skips_without_opt_in():
    env = os.environ.copy()
    env.pop("OMX_RUN_REAL_EXTERNAL_AGENT_SMOKE", None)

    completed = subprocess.run(
        [sys.executable, "scripts/run_real_external_agent_smoke.py"],
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "real_external_agent_smoke=skipped" in completed.stdout
    assert "set_OMX_RUN_REAL_EXTERNAL_AGENT_SMOKE=1" in completed.stdout


def test_real_external_agent_smoke_skips_without_backend_env():
    env = os.environ.copy()
    env["OMX_RUN_REAL_EXTERNAL_AGENT_SMOKE"] = "1"
    env.pop("OMX_CODEX_CODER_COMMAND", None)
    env.pop("OMX_CODEX_REVIEWER_COMMAND", None)

    completed = subprocess.run(
        [sys.executable, "scripts/run_real_external_agent_smoke.py", "--runtime", "codex"],
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "real_external_agent_smoke=skipped" in completed.stdout
    assert "reason=missing_backend_env" in completed.stdout
    assert "OMX_CODEX_CODER_COMMAND" in completed.stdout
    assert "OMX_CODEX_REVIEWER_COMMAND" in completed.stdout
