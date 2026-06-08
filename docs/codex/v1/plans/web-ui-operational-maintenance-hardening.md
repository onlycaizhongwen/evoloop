# Web UI Operational Maintenance Hardening Plan

## Goal

Make the current Web UI task manager safer to operate over longer local/demo sessions by hardening audit retention, run/job cleanup boundaries, and pre-demo health checks without changing the existing task execution contract.

## Current Baseline

- `/tasks` supports status/quality/rerun/search filters, pagination, single and batch stop/rerun/delete actions.
- Task manager operations write append-only audit events to `.omx/web-job-audit.jsonl`.
- `/tasks/audit` and `/tasks/audit.md` support event type, outcome, search, limit, empty-filter hints, filtered exports, and summary counts.
- Audit write failures are logged as warnings and do not block task operations.
- Latest verified baseline: `python -m pytest -q` passed with `138 passed`.

## Priority 1: Audit Log Retention And Rotation

### Scope

- Add bounded retention behavior to `WebJobAuditLog`.
- Keep append-only semantics for active `.omx/web-job-audit.jsonl`.
- Rotate or archive only when the active file exceeds a conservative size threshold.
- Keep `/tasks/audit` and `/tasks/audit.md` reading the active file first; archived-file search can be a later enhancement.

### Acceptance Criteria

- Existing audit append/list behavior remains compatible.
- Oversized audit file can be rotated without losing newly appended events.
- Rotation failure is logged and does not block task operations.
- Tests cover append, `list_recent`, corrupt-line tolerance, and rotation threshold behavior.

### Candidate Files

- `orchestrator/infrastructure/persistence/web_job_audit_log.py`
- `orchestrator/interfaces/web/main.py`
- `tests/test_web_ui.py` or a new focused persistence test file.

## Priority 2: Task Manager Maintenance Actions

### Scope

- Add safe maintenance actions that distinguish Web Job records from run artifacts.
- First version should be conservative:
  - prune completed/stopped/failed Web Job records older than a selected age;
  - never delete `.omx/runs/{run_id}` by default;
  - write maintenance audit events with selected/processed/skipped/failed IDs.

### Acceptance Criteria

- Running jobs are never pruned.
- Jobs with linked run artifacts preserve run directories.
- Prune actions are audited and visible in `/tasks/audit`.
- The page clearly reports processed/skipped counts.

### Candidate Files

- `orchestrator/interfaces/web/main.py`
- `orchestrator/interfaces/web/templates/tasks.html`
- `tests/test_web_ui.py`
- `docs/codex/v1/trace/web-ui-operational-maintenance-hardening-trace.md`

## Priority 3: Demo Readiness Health Check

### Scope

- Add a read-only health check surface for demo operators.
- Validate:
  - SQLite job DB can be opened;
  - audit log can be read;
  - required template examples and static assets exist;
  - Docker preset smoke prerequisites are discoverable.

### Acceptance Criteria

- Health endpoint/page is read-only.
- It reports pass/warn/fail rows without mutating jobs, audit logs, or run directories.
- Tests cover missing audit file, corrupt audit lines, missing examples directory, and healthy baseline.

### Candidate Files

- `orchestrator/interfaces/web/main.py`
- `orchestrator/interfaces/web/templates/*`
- `tests/test_web_ui.py`
- `docs/codex/v1/plans/demo-readiness.md`

## Recommended Execution Order

1. Implement audit retention/rotation first because it directly addresses the remaining risk documented by the operational audit trace.
2. Add maintenance actions only after audit rotation is stable, so cleanup actions can be audited reliably.
3. Add demo health checks last, reusing the audit and cleanup status helpers rather than inventing a separate diagnostics model.

## Validation Plan

- `python -m pytest -q tests/test_web_ui.py -k "task_manager or audit"`
- `python -m py_compile orchestrator/interfaces/web/main.py orchestrator/infrastructure/persistence/web_job_audit_log.py`
- `python -m pytest -q tests/test_web_ui.py`
- `python -m pytest -q`
- `git diff --check`

## Risks And Guardrails

- Do not delete run directories in the first maintenance increment.
- Do not migrate SQLite schema unless a later requirement proves it is necessary.
- Keep audit writes non-blocking for task operations.
- Prefer focused helpers and tests over broad UI rewrites.
