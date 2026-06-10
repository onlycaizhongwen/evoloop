# Web Browser Smoke Process

## Resume Capsule

- Task need: advance production readiness with a repeatable real-server Web smoke.
- Key decision: first use Uvicorn plus standard-library HTTP checks instead of adding Playwright dependency.
- Current phase: completed.
- Completed artifacts: `scripts/run_web_browser_smoke.py`, `tests/test_web_browser_smoke.py`, external-agent wrapper provenance HTTP coverage, disposable maintenance prune-runs HTTP coverage, process-scoped smoke workspace cleanup, `docs/codex/v1/plans/web-production-readiness-next.md`, `docs/codex/v1/trace/web-production-readiness-next-trace.md`.
- Remaining work: none for this slice. Do not commit unless the user asks.
- Important finding: repository has FastAPI/Uvicorn but no committed Playwright/Selenium dependency manifest.

## Steps

- [v] Inspect current Web UI routes, existing smoke scripts, and task-template behavior.
- [v] Add `scripts/run_web_browser_smoke.py`.
- [v] Add pytest wrapper `tests/test_web_browser_smoke.py`.
- [v] Extend smoke coverage to archived audit source/source-file filtering and Markdown export.
- [v] Extend smoke coverage to external-agent wrapper provenance on run detail and run audit Markdown over real HTTP.
- [v] Make the smoke workspace process-scoped so concurrent pytest runs do not contend on Windows.
- [v] Prune stale process-scoped smoke workspaces older than 24 hours without failing on locked directories.
- [v] Validate destructive run-artifact maintenance over real HTTP using seeded disposable artifacts only.
- [v] Validate smoke and update project status.

## Research Findings

- `/templates/run` can submit the `mock_demo` template, which keeps this smoke independent from Docker, OMX, Codex credentials, and browser binary installation.
- `/tasks/health.json` is read-only and suitable as the readiness gate before exercising form flows.
- Seeded active and archived audit JSONL records let the Uvicorn smoke validate source provenance without touching project history.
- The same Uvicorn smoke can run a local-backend `codex` external-agent task without credentials, then verify wrapper provenance through `/runs/{run_id}` and `/runs/{run_id}/audit.md`.
- The smoke can safely cover destructive maintenance by seeding old/fresh/running/missing-state run artifact directories inside its disposable workspace, then POSTing `/tasks/maintenance/prune-runs` over HTTP and verifying deletion, preservation, and audit evidence.
- The process-scoped workspace cleanup only touches `run-*` children under `.tmp/web-browser-smoke`, skips the current process directory, and ignores locked stale directories.

## Error Log

- Initial health check returned `warn` because the isolated smoke workspace had no audit log; fixed by seeding a minimal audit JSONL record.
- Initial POST redirect parsing missed the `Location` header because header lookup was case-sensitive; fixed with case-insensitive header lookup.
- Parallel pytest invocations contended on `.tmp/web-browser-smoke` on Windows, causing missing seed files or locked-directory cleanup failures; fixed by using `.tmp/web-browser-smoke/run-{pid}`.

## Validation Evidence

- `python scripts/run_web_browser_smoke.py`: passed with `audit_archive_smoke=passed` and `web_browser_smoke=passed`.
- `python -m py_compile scripts/run_web_browser_smoke.py orchestrator/interfaces/web/main.py orchestrator/infrastructure/persistence/web_job_audit_log.py`: passed.
- `python -m pytest -q tests/test_web_browser_smoke.py`: 1 passed.
- `python -m pytest -q tests/test_web_ui.py tests/test_web_browser_smoke.py tests/test_demo_readiness_smoke.py`: 63 passed.
- `python -m pytest -q`: 155 passed.
- `git diff --check`: passed with only CRLF warnings.
- `python -m py_compile scripts/run_web_browser_smoke.py`: passed.
- `python scripts/run_web_browser_smoke.py`: passed with `health_overall=pass`, `audit_archive_smoke=passed`, `wrapper_runtime=codex`, `wrapper_roles=coder,reviewer`, `wrapper_exit_codes=0,0`, `wrapper_backend_commands=2`, `web_external_agent_provenance_smoke=passed`, and `web_browser_smoke=passed`.
- `python -m pytest -q tests/test_web_browser_smoke.py`: 1 passed.
- `python -m py_compile scripts/run_web_browser_smoke.py tests/test_web_browser_smoke.py`: passed.
- `python -m pytest -q tests/test_web_browser_smoke.py`: 2 passed.
- `python scripts/run_web_browser_smoke.py`: passed with `web_external_agent_provenance_smoke=passed` and `web_browser_smoke=passed`.
- `python scripts/run_web_browser_smoke.py`: passed with `maintenance_prune_runs_smoke=passed`, `web_external_agent_provenance_smoke=passed`, and `web_browser_smoke=passed`.
