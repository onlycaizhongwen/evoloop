# Web Run Artifact Cleanup

## Goal

Add an operator-triggered cleanup action for old `.omx/runs/{run_id}` artifact directories without weakening task/job auditability.

## Scope

- Add a conservative `/tasks/maintenance/prune-runs` action from the task manager page.
- Delete only run directories older than the selected age threshold.
- Preserve Web Job database records and Web Job audit logs.
- Skip run directories linked to a `running` Web Job.
- Skip directories that do not contain `run_state.json`.
- Record a `maintenance_prune_runs` audit event with run IDs, linked Job IDs, candidate directories, deleted directories, cutoff, and skip reasons.

## Acceptance Criteria

- Operators can choose 7, 30, or 90 day thresholds from `/tasks`.
- Old orphan run artifacts and old completed-job run artifacts can be deleted.
- Running-job run artifacts, fresh artifacts, and malformed/missing-state directories are skipped.
- Audit search can find the `maintenance_prune_runs` event and deleted run evidence.
- Existing Web Job maintenance pruning remains unchanged.

## Verification Plan

- `python -m py_compile orchestrator/interfaces/web/main.py orchestrator/infrastructure/persistence/sqlite_job_repository.py`
- `python -m pytest -q tests/test_web_ui.py -k "maintenance"`
- `python -m pytest -q tests/test_web_ui.py`
- `python -m pytest -q`
- `git diff --check`
