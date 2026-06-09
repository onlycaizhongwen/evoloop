# Web Production Readiness Next Trace

## Status

Completed.

## Current Increment

The first production-readiness increment adds a repeatable Web browser-path smoke. It runs the FastAPI app through Uvicorn in an isolated workspace and validates the main operator path over HTTP before future Playwright or real external-agent expansion.

## Covered Scope

- Real server process startup.
- Demo readiness JSON.
- Task manager page controls.
- Template-based mock run submission.
- Job-to-run redirect.
- Run detail page rendering.
- Task manager visibility after the run.

## Remaining Work

- Optional future Playwright coverage after dependency and browser binary provisioning are explicit.
- Optional real external-agent browser smoke gated by configured `omx` / `codex` commands.
- Optional production maintenance controls for archived audit search and explicit run-artifact cleanup.

## Verification Evidence

- `python scripts/run_web_browser_smoke.py`: passed with `health_overall=pass` and `web_browser_smoke=passed`.
- `python -m py_compile scripts/run_web_browser_smoke.py`: passed.
- `python -m pytest -q tests/test_web_browser_smoke.py`: 1 passed.
- `python -m pytest -q tests/test_web_ui.py tests/test_web_browser_smoke.py tests/test_demo_readiness_smoke.py`: 61 passed.
- `python -m pytest -q`: 151 passed.
- `git diff --check`: passed; Git reported only the existing Windows CRLF conversion warning for `.codex/plans/main/TASKS.md`.
