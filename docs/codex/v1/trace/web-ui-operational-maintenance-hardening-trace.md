# Web UI Operational Maintenance Hardening Trace

## Conclusion

Priority 1 and Priority 2 are implemented. Task-manager audit JSONL now has bounded active-file retention through pre-append rotation, and the task manager has a conservative maintenance action for pruning old non-running Web Job records while preserving run artifacts.

## Alignment

- Plan: `docs/codex/v1/plans/web-ui-operational-maintenance-hardening.md`
- Priority covered: Audit Log Retention And Rotation; Task Manager Maintenance Actions
- Implementation: `WebJobAuditLog` accepts `max_bytes` and `archive_count`, rotates `.omx/web-job-audit.jsonl` when the active file reaches the configured threshold, and prunes older archives.
- Maintenance implementation: `/tasks/maintenance/prune` prunes only `done`, `failed`, and `stopped` Web Job records older than the selected age. It does not delete `.omx/runs/{run_id}` and writes a `maintenance_prune` audit event with selected, processed, skipped, failed, run IDs, cutoff, status scope, and artifact-preservation details.
- Compatibility: `/tasks/audit` and `/tasks/audit.md` still read the active audit file first and do not change archived-file search semantics.
- Non-blocking behavior: rotation errors surface as `OSError`; the existing Web handler warning path keeps task operations non-blocking when audit append fails.

## Verification Evidence

- `python -m pytest -q tests/test_web_job_audit_log.py`: 5 passed.
- `python -m pytest -q tests/test_web_ui.py -k "task_manager or audit" tests/test_web_job_audit_log.py`: 14 passed, 44 deselected.
- `python -m py_compile orchestrator/infrastructure/persistence/web_job_audit_log.py orchestrator/interfaces/web/main.py`: passed.
- `python -m pytest -q tests/test_web_ui.py`: 53 passed.
- `python -m pytest -q`: 143 passed.
- `git diff --check`: passed.
- `python -m py_compile orchestrator/interfaces/web/main.py orchestrator/infrastructure/persistence/sqlite_job_repository.py`: passed.
- `python -m pytest -q tests/test_web_ui.py -k "task_manager and maintenance"`: 1 passed, 53 deselected.
- `python -m pytest -q tests/test_web_ui.py -k "task_manager or audit"`: 10 passed, 44 deselected.

## Remaining Work

- Priority 3 remains open: add read-only demo readiness health checks.
