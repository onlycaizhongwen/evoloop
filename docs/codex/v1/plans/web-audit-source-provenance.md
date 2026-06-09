# Web Audit Source Provenance

## Goal

Make task-manager audit evidence easier to operate when `scope=all` includes rotated archives by showing which file each audit record came from.

## Scope

- Add read-time source metadata to Web Job audit records.
- Preserve the JSONL write format and keep old audit files compatible.
- Show source kind and source file in `/tasks/audit`.
- Include source kind and source file in `/tasks/audit.md`.
- Include source metadata in audit search text.
- Add a `source=all|active|archive` filter for page and Markdown export.
- Add a `source_file=<audit file name>` filter for page and Markdown export.
- Show record counts beside each source option.
- Show record counts beside each source-file option.
- Include a source-file count summary in Markdown exports.

## Acceptance Criteria

- Active audit records are marked as `active / web-job-audit.jsonl`.
- Archived audit records are marked as `archive / web-job-audit.<timestamp>.jsonl`.
- Markdown export includes a `Source` line per record.
- `source=archive` automatically includes archives and filters out active records.
- `source_file=<archive name>` filters the page/export to that exact source file and automatically includes archives.
- Source options show counts, for example `Archives only (3)`.
- Source file options show counts, for example `web-job-audit.jsonl (12)`.
- Markdown exports include `Source files: ...` for the filtered result set.
- Existing audit filters, search, and active-only default behavior remain compatible.

## Verification Plan

- `python -m py_compile orchestrator/infrastructure/persistence/web_job_audit_log.py orchestrator/interfaces/web/main.py`
- `python -m pytest -q tests/test_web_job_audit_log.py tests/test_web_ui.py -k "audit"`
- `python -m pytest -q tests/test_web_ui.py tests/test_web_job_audit_log.py`
- `python -m pytest -q`
- `git diff --check`
