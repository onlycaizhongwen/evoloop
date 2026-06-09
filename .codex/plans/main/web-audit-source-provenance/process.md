# Web Audit Source Provenance Process

## Resume Capsule

- Task need: continue production-grade operations by making audit records traceable to active vs archived source files.
- Key decision: source metadata is read-time only; existing JSONL files are not rewritten.
- Current phase: completed.
- Completed artifacts: audit reader metadata, page source display, Markdown source line, source/source-file filters, source/source-file option counts, tests.
- Remaining work: none for this slice. Do not commit unless the user asks.
- Important finding: this closes the archived-audit provenance follow-up from the archive search plan.

## Steps

- [v] Inspect audit reader, Web audit page, Markdown export, and archive tests.
- [v] Add read-time source metadata to audit records.
- [v] Render source metadata on page and Markdown export.
- [v] Add source filter for active/archive triage.
- [v] Add source-file filter for exact audit file triage.
- [v] Make source-file filter automatically include archives.
- [v] Show active/archive/all record counts in source options.
- [v] Show per-file record counts in source-file options.
- [v] Add per-file source summary to Markdown exports.
- [v] Add/adjust tests for source metadata.
- [v] Run broader verification and update trace/status.

## Research Findings

- `WebJobAuditLog.list_recent(include_archives=True)` already reads archives and active files in an order that preserves recent-first output.
- Adding metadata during `_read_records()` avoids changing the persisted event schema.

## Error Log

- Existing corrupt-line test expected exact raw dict equality; updated it to assert core fields plus source metadata.

## Validation Evidence

- `python -m py_compile orchestrator/infrastructure/persistence/web_job_audit_log.py orchestrator/interfaces/web/main.py`: passed.
- `python -m pytest -q tests/test_web_job_audit_log.py tests/test_web_ui.py -k "audit"`: 12 passed, 55 deselected.
- `python -m pytest -q tests/test_web_ui.py tests/test_web_job_audit_log.py`: 67 passed.
- `python -m pytest -q`: 155 passed.
- `git diff --check`: passed with CRLF warnings only.
