# Web Audit Archive Search Process

## Resume Capsule

- Task need: make rotated Web task-manager audit records searchable/exportable.
- Key decision: default remains active-only; `scope=all` opt-in includes archives.
- Current phase: completed.
- Completed artifacts: persistence helper, Web scope parameter, template selector, tests, plan/trace drafts.
- Remaining work: commit/push after final git review.
- Important finding: audit rotation already preserves archives but Web audit read path only used active JSONL.

## Steps

- [v] Inspect audit persistence, Web audit page, and tests.
- [v] Implement archive-inclusive audit read.
- [v] Add Web `scope=all` search/export.
- [v] Validate and update project status.

## Research Findings

- `WebJobAuditLog._archive_paths()` already returns archive files newest-first for pruning.
- Existing audit page tests expect active-only default behavior, so archive search must be opt-in to avoid semantic drift.

## Error Log

- Initial test asserted the query string was absent from the page; fixed by checking record content instead because export links correctly preserve query params.

## Validation Evidence

- `python -m py_compile orchestrator/infrastructure/persistence/web_job_audit_log.py orchestrator/interfaces/web/main.py`: passed.
- `python -m pytest -q tests/test_web_job_audit_log.py tests/test_web_ui.py -k "audit"`: 12 passed, 54 deselected.
- `python -m pytest -q tests/test_web_ui.py tests/test_web_job_audit_log.py`: 66 passed.
- `python -m pytest -q`: 154 passed.
- `git diff --check`: passed with CRLF warnings only.
