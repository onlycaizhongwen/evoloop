# External Agent Closed Loop Smoke Trace

## Status

Completed.

## Covered Scope

- Task JSON generated in an isolated workspace.
- `codex` external-command adapter selected through CLI.
- `scripts/run_external_agent.py` wrapper invoked for coder and reviewer roles.
- Local backend command produces deterministic reviewer JSON.
- Orchestrator validates review JSON, evaluates quality gate, and writes final report artifacts.

## Remaining Work

- Optional real `omx` / `codex` command smoke when runtime configuration and credentials are present.
- Optional Web run-detail exposure for wrapper command provenance.

## Verification Evidence

- `python scripts/run_external_agent_closed_loop_smoke.py`: passed with `external_agent_closed_loop_smoke=passed`.
- `python -m py_compile scripts/run_external_agent.py scripts/run_external_agent_closed_loop_smoke.py`: passed.
- `python -m pytest -q tests/test_external_agent_closed_loop_smoke.py tests/test_external_agent.py tests/test_external_agent_wrapper.py`: 17 passed.
- `python -m pytest -q tests/test_external_agent_closed_loop_smoke.py tests/test_external_agent.py tests/test_external_agent_wrapper.py tests/test_web_browser_smoke.py tests/test_demo_readiness_smoke.py`: 19 passed.
- `python -m pytest -q`: 152 passed.
- `git diff --check`: passed; Git reported only Windows CRLF conversion warnings for `.codex/plans/main/TASKS.md` and `scripts/run_external_agent.py`.
