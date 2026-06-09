# Web Run Artifact Cleanup Process

## Resume Capsule

- Task need: continue production operations hardening by safely cleaning old `.omx/runs/{run_id}` artifacts from the Web task manager.
- Key decision: cleanup is opt-in, age-gated, audit-logged, and skips running-linked or malformed run directories.
- Current phase: completed.
- Completed artifacts: Web endpoint, task-manager form, SQLite run lookup, targeted regression test, plan and trace drafts.
- Remaining work: Lore commit and push.
- Important finding: audit details should use resolvable run directory paths so operators can locate deleted evidence.

## Steps

- [v] Inspect existing maintenance prune and Web audit patterns.
- [v] Implement run artifact cleanup endpoint and helper.
- [v] Add UI form and regression test for safe pruning.
- [v] Fix summary initialization and audit path evidence after targeted test failures.
- [v] Run full verification and finalize trace/status.

## Research Findings

- Existing Web Job cleanup intentionally preserves run directories; run artifact cleanup should remain a separate explicit action.
- Existing batch/audit summaries can represent run IDs in processed/skipped fields while keeping linked Job IDs in `selected_job_ids`.

## Error Log

- Targeted maintenance test initially failed with `KeyError: 'selected_job_ids'`; fixed by initializing run cleanup summary fields.
- Targeted maintenance test then found audit details used relative paths; fixed by recording resolved candidate/deleted run directory paths.

## Validation Evidence

- `python -m py_compile orchestrator/interfaces/web/main.py orchestrator/infrastructure/persistence/sqlite_job_repository.py`: passed.
- `python -m pytest -q tests/test_web_ui.py -k "maintenance"`: 2 passed, 59 deselected.
- `python -m pytest -q tests/test_web_ui.py`: 61 passed.
- `python -m pytest -q`: 155 passed.
- `git diff --check`: passed with CRLF warnings only.
