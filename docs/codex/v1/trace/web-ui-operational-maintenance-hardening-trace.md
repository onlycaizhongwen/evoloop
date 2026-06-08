# Web UI Operational Maintenance Hardening Trace

## Conclusion

Priority 1 is implemented: task-manager audit JSONL now has bounded active-file retention through pre-append rotation. The active audit file keeps the existing append/list semantics, while oversized files are archived before the next event is written.

## Alignment

- Plan: `docs/codex/v1/plans/web-ui-operational-maintenance-hardening.md`
- Priority covered: Audit Log Retention And Rotation
- Implementation: `WebJobAuditLog` accepts `max_bytes` and `archive_count`, rotates `.omx/web-job-audit.jsonl` when the active file reaches the configured threshold, and prunes older archives.
- Compatibility: `/tasks/audit` and `/tasks/audit.md` still read the active audit file first and do not change archived-file search semantics.
- Non-blocking behavior: rotation errors surface as `OSError`; the existing Web handler warning path keeps task operations non-blocking when audit append fails.

## Verification Evidence

- `python -m pytest -q tests/test_web_job_audit_log.py`: 5 passed.
- `python -m pytest -q tests/test_web_ui.py -k "task_manager or audit" tests/test_web_job_audit_log.py`: 14 passed, 44 deselected.
- `python -m py_compile orchestrator/infrastructure/persistence/web_job_audit_log.py orchestrator/interfaces/web/main.py`: passed.
- `python -m pytest -q tests/test_web_ui.py`: 53 passed.
- `python -m pytest -q`: 143 passed.
- `git diff --check`: passed.

## Remaining Work

- Priority 2 remains open: add conservative task-manager maintenance actions that prune old Web Job records without deleting run directories.
- Priority 3 remains open: add read-only demo readiness health checks.
