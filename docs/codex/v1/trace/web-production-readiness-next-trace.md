# Web Production Readiness Next Trace

## Status

Completed.

## Current Increment

The production-readiness increment adds a repeatable Web browser-path smoke. It runs the FastAPI app through Uvicorn in an isolated process-scoped workspace and validates the main operator path over HTTP before future Playwright expansion.

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
- Local-backend `codex` external-agent run creation.
- Wrapper provenance rendering on run detail over HTTP.
- Wrapper provenance export in run audit Markdown over HTTP.
- Destructive run-artifact maintenance cleanup over HTTP with seeded disposable old, fresh, running-linked, and missing-state artifacts.
- Process-scoped smoke workspace isolation for concurrent test runs.
- Stale `run-*` smoke workspace cleanup with current-directory and locked-directory safeguards.
- One-command production readiness smoke aggregation for demo readiness, external-agent closure, real-command gate status, and Web HTTP coverage.
- Structured production readiness failure reporting for stage timeouts and command launch failures.
- Optional production readiness JSON summary output for CI and downstream dashboards, including schema version, UTC generation time, and per-stage duration.

## Remaining Work

- Optional future Playwright coverage after dependency and browser binary provisioning are explicit.
- Optional real external-agent browser smoke gated by configured `omx` / `codex` commands.
- Optional deeper maintenance-control browser smoke only when new destructive controls are introduced.

## Verification Evidence

- `python scripts/run_web_browser_smoke.py`: passed with `health_overall=pass`, `audit_archive_smoke=passed`, and `web_browser_smoke=passed`.
- `python -m py_compile scripts/run_web_browser_smoke.py orchestrator/interfaces/web/main.py orchestrator/infrastructure/persistence/web_job_audit_log.py`: passed.
- `python -m pytest -q tests/test_web_browser_smoke.py`: 1 passed.
- `python -m pytest -q tests/test_web_ui.py tests/test_web_browser_smoke.py tests/test_demo_readiness_smoke.py`: 63 passed.
- `python -m pytest -q`: 155 passed.
- `git diff --check`: passed; Git reported only Windows CRLF conversion warnings.
- `python -m py_compile scripts/run_web_browser_smoke.py`: passed.
- `python scripts/run_web_browser_smoke.py`: passed with `health_overall=pass`, `audit_archive_smoke=passed`, `wrapper_runtime=codex`, `wrapper_roles=coder,reviewer`, `wrapper_exit_codes=0,0`, `wrapper_backend_commands=2`, `web_external_agent_provenance_smoke=passed`, and `web_browser_smoke=passed`.
- `python -m pytest -q tests/test_web_browser_smoke.py`: 1 passed.
- `python -m py_compile scripts/run_web_browser_smoke.py tests/test_web_browser_smoke.py`: passed.
- `python -m pytest -q tests/test_web_browser_smoke.py`: 2 passed.
- `python scripts/run_web_browser_smoke.py`: passed with `web_external_agent_provenance_smoke=passed` and `web_browser_smoke=passed`.
- `python scripts/run_web_browser_smoke.py`: passed with `maintenance_prune_runs_smoke=passed`, `web_external_agent_provenance_smoke=passed`, and `web_browser_smoke=passed`.
- `python scripts/run_production_readiness_smoke.py`: passed with `production_readiness_summary passed=3 skipped=1 failed=0` and `production_readiness_smoke=passed`.
- `python -m py_compile scripts/run_production_readiness_smoke.py tests/test_production_readiness_smoke.py`: passed.
- `python -m pytest -q tests/test_production_readiness_smoke.py`: 9 passed, including timeout, command launch failure, JSON summary reporting, and JSON metadata/duration coverage.
- `python scripts/run_production_readiness_smoke.py`: passed with `production_readiness_summary passed=3 skipped=1 failed=0` and `production_readiness_smoke=passed` after structured failure handling.
- `python scripts/run_production_readiness_smoke.py --summary-json .tmp/production-readiness-summary.json`: passed and wrote pass/skip/fail stage JSON with `schema_version`, UTC `generated_at`, and `duration_seconds`.
- `python -m pytest -q`: 168 passed after versioned JSON summary hardening.
- `git diff --check`: passed; Git reported only Windows CRLF conversion warnings.
