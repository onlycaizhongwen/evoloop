# Web Audit Archive Search Trace

## Status

Completed.

## Covered Scope

- Persistence helper for reading active audit plus archives.
- Web audit page `scope=active|all` selector.
- Markdown export preserving `scope=all`.
- Tests for active-only compatibility and archived search/export.

## Remaining Work

- Optional source-file labels per audit row if operators need active/archive provenance.
- Optional archive count/size health-check summary.

## Verification Evidence

- `python -m py_compile orchestrator/infrastructure/persistence/web_job_audit_log.py orchestrator/interfaces/web/main.py`: passed.
- `python -m pytest -q tests/test_web_job_audit_log.py tests/test_web_ui.py -k "audit"`: 12 passed, 54 deselected.
- `python -m pytest -q tests/test_web_ui.py tests/test_web_job_audit_log.py`: 66 passed.
- `python -m pytest -q`: 154 passed.
- `git diff --check`: passed; Git reported only Windows CRLF conversion warnings.
