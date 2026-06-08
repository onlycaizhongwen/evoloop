# Web UI Operational Maintenance Hardening Trace

## Conclusion

Priority 1, Priority 2, and Priority 3 are implemented. Task-manager audit JSONL now has bounded active-file retention through pre-append rotation, the task manager has a conservative maintenance action for pruning old non-running Web Job records while preserving run artifacts, and demo operators have a read-only readiness page.

## Alignment

- Plan: `docs/codex/v1/plans/web-ui-operational-maintenance-hardening.md`
- Priority covered: Audit Log Retention And Rotation; Task Manager Maintenance Actions; Demo Readiness Health Check
- Implementation: `WebJobAuditLog` accepts `max_bytes` and `archive_count`, rotates `.omx/web-job-audit.jsonl` when the active file reaches the configured threshold, and prunes older archives.
- Maintenance implementation: `/tasks/maintenance/prune` prunes only `done`, `failed`, and `stopped` Web Job records older than the selected age. It does not delete `.omx/runs/{run_id}` and writes a `maintenance_prune` audit event with selected, processed, skipped, failed, run IDs, cutoff, status scope, and artifact-preservation details.
- Compatibility: `/tasks/audit` and `/tasks/audit.md` still read the active audit file first and do not change archived-file search semantics.
- Non-blocking behavior: rotation errors surface as `OSError`; the existing Web handler warning path keeps task operations non-blocking when audit append fails.
- Health-check implementation: `/tasks/health` reports pass/warn/fail rows for read-only SQLite access, audit log readability, template examples, static assets, required templates, and Docker command preset discoverability. `/tasks/health.json` exposes the same read-only evidence for scripts and pre-demo automation. `scripts/run_demo_readiness_smoke.py` seeds an isolated temporary workspace and fails fast if the JSON summary is not `pass`. These endpoints do not create `.omx`, job records, audit events, or run artifacts outside their explicit smoke workspace.

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
- `python -m py_compile orchestrator/interfaces/web/main.py`: passed.
- `python -m pytest -q tests/test_web_ui.py -k "health"`: 4 passed, 54 deselected.
- `python -m pytest -q tests/test_web_ui.py -k "task_manager or audit or health"`: 14 passed, 44 deselected.
- `python -m pytest -q tests/test_web_ui.py -k "health"`: 5 passed, 54 deselected.
- `python -m py_compile scripts/run_demo_readiness_smoke.py`: passed.
- `python scripts/run_demo_readiness_smoke.py`: passed with `demo_readiness_smoke=passed`.
- `python -m pytest -q tests/test_demo_readiness_smoke.py`: 1 passed.

## Remaining Work

- No remaining work in this hardening plan. Future enhancements can add optional archived-audit search or explicit run-artifact cleanup behind separate controls.
