# Web Audit Archive Search

## Goal

Make rotated task-manager audit evidence searchable and exportable without changing the default active-file audit view.

## Scope

- Keep `/tasks/audit` and `/tasks/audit.md` defaulting to active `.omx/web-job-audit.jsonl`.
- Add `scope=all` to include rotated archive files matching `web-job-audit.*.jsonl`.
- Preserve existing event, outcome, search, and limit filters.
- Include the selected scope in filtered Markdown exports.

## Acceptance Criteria

- `WebJobAuditLog.list_recent(..., include_archives=True)` returns records from archives plus the active file in recent-first order.
- `/tasks/audit?scope=all&q=...` can find archived events.
- `/tasks/audit.md?scope=all&q=...` exports the same filtered archived evidence.
- Existing active-only behavior remains compatible.

## Follow-Up Candidates

- Add source-file labels per audit row if operators need to distinguish active vs archived provenance.
- Add archive count/size health-check summary.
