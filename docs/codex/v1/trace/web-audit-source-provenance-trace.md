# Web Audit Source Provenance Trace

## Status

Completed.

## Covered Scope

- Audit persistence read path adds `_source_file`, `_source_path`, and `_source_kind` metadata.
- `/tasks/audit` displays source kind and file per record.
- `/tasks/audit.md` exports a source line per record.
- Audit search includes source metadata.
- `/tasks/audit` and `/tasks/audit.md` support `source=all|active|archive`.
- `/tasks/audit` and `/tasks/audit.md` support exact source-file filtering.
- Source filter options include active/archive/all record counts.
- Source-file filter options include per-file record counts.
- Markdown exports include a source-file count summary for the filtered result set.
- Tests cover archive provenance in persistence, page rendering, and Markdown export.

## Alignment Check

- Plan requirement: preserve JSONL compatibility.
  Implementation: metadata is added after JSON parsing and is not written back to audit files.
- Plan requirement: distinguish active and archived evidence.
  Implementation: active records use `_source_kind=active`; archive records use `_source_kind=archive`.
- Plan requirement: operator-visible provenance.
  Implementation: the page shows `source: kind / file`; Markdown exports `- Source: kind (file)`.
- Plan requirement: source-specific triage.
  Implementation: `source=archive` forces archive-inclusive reads and filters records down to archived sources.
- Plan requirement: file-specific triage.
  Implementation: `source_file=<file>` automatically includes archives, is accepted only when the file name exists in the current audit result set, then filters page and Markdown records to that file.
- Plan requirement: operator scanability.
  Implementation: source select labels include active/archive/all counts, and source-file select labels include per-file counts computed from the current audit result set.
- Plan requirement: portable evidence.
  Implementation: Markdown exports include a `Source files` line with per-file counts computed from the exported records.

## Remaining Work

- None for this slice.

## Verification Evidence

- `python -m py_compile orchestrator/infrastructure/persistence/web_job_audit_log.py orchestrator/interfaces/web/main.py`: passed.
- `python -m pytest -q tests/test_web_job_audit_log.py tests/test_web_ui.py -k "audit"`: 12 passed, 55 deselected.
- `python -m pytest -q tests/test_web_ui.py tests/test_web_job_audit_log.py`: 67 passed.
- `python -m pytest -q`: 155 passed.
- `git diff --check`: passed; Git reported only Windows CRLF conversion warnings.
