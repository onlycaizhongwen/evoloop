# Web Health Footprint Evidence

## Goal

Make the Web demo readiness health surface more useful for production operations by exposing read-only storage footprint evidence for audit archives and run artifacts.

## Scope

- Add a `Task audit archives` readiness check.
- Add a `Run artifact footprint` readiness check.
- Keep `/tasks/health` and `/tasks/health.json` read-only.
- Do not create `.omx`, audit logs, run directories, or cleanup actions from these checks.

## Acceptance Criteria

- Health JSON includes archive count and total archive size when rotated audit files exist.
- Health JSON includes run directory count and total size when run artifacts exist.
- Missing `.omx` remains non-mutating and reported as warning-level readiness evidence.
- Existing health checks and demo readiness smoke remain compatible.

## Verification Plan

- `python -m py_compile orchestrator/interfaces/web/main.py`
- `python -m pytest -q tests/test_web_ui.py -k "health"`
- `python -m pytest -q tests/test_web_ui.py`
- `python -m pytest -q`
- `git diff --check`
