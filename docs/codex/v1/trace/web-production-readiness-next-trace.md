# Web Production Readiness Next Trace

## Status

Completed.

## Current Increment

The first production-readiness increment adds a repeatable Web browser-path smoke. It runs the FastAPI app through Uvicorn in an isolated workspace and validates the main operator path over HTTP before future Playwright or real external-agent expansion.

## Covered Scope

- Real server process startup.
- Demo readiness JSON.
- Task manager page controls.
- Archived task audit page filtering.
- Archived task audit Markdown export.
- Template-based mock run submission.
- Job-to-run redirect.
- Run detail page rendering.
- Task manager visibility after the run.

## Remaining Work

- Optional future Playwright coverage after dependency and browser binary provisioning are explicit.
- Optional real external-agent browser smoke gated by configured `omx` / `codex` commands.
- Optional deeper maintenance-control browser smoke for destructive cleanup paths, using seeded disposable artifacts only.

## Verification Evidence

- `python scripts/run_web_browser_smoke.py`: passed with `health_overall=pass`, `audit_archive_smoke=passed`, and `web_browser_smoke=passed`.
- `python -m py_compile scripts/run_web_browser_smoke.py orchestrator/interfaces/web/main.py orchestrator/infrastructure/persistence/web_job_audit_log.py`: passed.
- `python -m pytest -q tests/test_web_browser_smoke.py`: 1 passed.
- `python -m pytest -q tests/test_web_ui.py tests/test_web_browser_smoke.py tests/test_demo_readiness_smoke.py`: 63 passed.
- `python -m pytest -q`: 155 passed.
- `git diff --check`: passed; Git reported only Windows CRLF conversion warnings.
