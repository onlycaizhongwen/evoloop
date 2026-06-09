# Web Run Artifact Cleanup Trace

## Status

Completed.

## Covered Scope

- Web task-manager maintenance form for run artifact cleanup.
- POST endpoint `/tasks/maintenance/prune-runs`.
- Conservative artifact pruning helper for `.omx/runs/{run_id}`.
- SQLite lookup helper for jobs linked to candidate run IDs.
- Audit event `maintenance_prune_runs`.
- Regression coverage for orphan, completed, running, fresh, and missing-state run directories.

## Alignment Check

- Plan requirement: delete old run artifact directories only.
  Implementation: `_prune_old_run_artifacts()` enumerates `RUNS_DIR.iterdir()` directories and deletes only selected old candidates.
- Plan requirement: preserve records and audit logs.
  Implementation: no Web Job records are deleted; the action appends a Web Job audit event.
- Plan requirement: skip active or suspicious artifacts.
  Implementation: linked `running` jobs and directories missing `run_state.json` are skipped with reasons.
- Plan requirement: operator evidence.
  Implementation: audit details include cutoff, candidate directories, deleted directories, linked job IDs, run IDs, and skip reasons.

## Remaining Work

- Optional future enhancement: show aggregate run artifact disk usage before deletion.

## Verification Evidence

- `python -m py_compile orchestrator/interfaces/web/main.py orchestrator/infrastructure/persistence/sqlite_job_repository.py`: passed.
- `python -m pytest -q tests/test_web_ui.py -k "maintenance"`: 2 passed, 59 deselected.
- `python -m pytest -q tests/test_web_ui.py`: 61 passed.
- `python -m pytest -q`: 155 passed.
- `git diff --check`: passed; Git reported only Windows CRLF conversion warnings.
