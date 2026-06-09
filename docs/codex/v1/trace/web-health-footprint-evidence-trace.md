# Web Health Footprint Evidence Trace

## Status

Completed.

## Covered Scope

- `/tasks/health` includes task audit archive footprint evidence.
- `/tasks/health` includes run artifact footprint evidence.
- `/tasks/health.json` exposes the same checks for scripts.
- Tests cover archive footprint and run artifact footprint in machine-readable output.

## Alignment Check

- Plan requirement: read-only health evidence.
  Implementation: checks inspect existing paths only and do not create missing directories.
- Plan requirement: archive footprint evidence.
  Implementation: `_check_task_audit_archive_footprint()` counts `web-job-audit.*.jsonl` archives and sums file sizes.
- Plan requirement: run artifact footprint evidence.
  Implementation: `_check_run_artifact_footprint()` counts existing run directories and sums file sizes under them.

## Remaining Work

- Optional future enhancement: expose warning thresholds for archive or run artifact footprint sizes.

## Verification Evidence

- `python -m py_compile orchestrator/interfaces/web/main.py`: passed.
- `python -m pytest -q tests/test_web_ui.py -k "health"`: 5 passed, 56 deselected.
- `python -m pytest -q tests/test_demo_readiness_smoke.py tests/test_web_browser_smoke.py`: 2 passed.
- `python -m pytest -q tests/test_web_ui.py`: 61 passed.
- `python -m pytest -q`: 155 passed.
- `git diff --check`: passed; Git reported only Windows CRLF conversion warnings.
