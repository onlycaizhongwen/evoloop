# Web Browser Smoke Process

## Resume Capsule

- Task need: advance production readiness with a repeatable real-server Web smoke.
- Key decision: first use Uvicorn plus standard-library HTTP checks instead of adding Playwright dependency.
- Current phase: completed.
- Completed artifacts: `scripts/run_web_browser_smoke.py`, `tests/test_web_browser_smoke.py`, `docs/codex/v1/plans/web-production-readiness-next.md`, `docs/codex/v1/trace/web-production-readiness-next-trace.md`.
- Remaining work: none for this slice. Do not commit unless the user asks.
- Important finding: repository has FastAPI/Uvicorn but no committed Playwright/Selenium dependency manifest.

## Steps

- [v] Inspect current Web UI routes, existing smoke scripts, and task-template behavior.
- [v] Add `scripts/run_web_browser_smoke.py`.
- [v] Add pytest wrapper `tests/test_web_browser_smoke.py`.
- [v] Extend smoke coverage to archived audit source/source-file filtering and Markdown export.
- [v] Validate smoke and update project status.

## Research Findings

- `/templates/run` can submit the `mock_demo` template, which keeps this smoke independent from Docker, OMX, Codex credentials, and browser binary installation.
- `/tasks/health.json` is read-only and suitable as the readiness gate before exercising form flows.
- Seeded active and archived audit JSONL records let the Uvicorn smoke validate source provenance without touching project history.

## Error Log

- Initial health check returned `warn` because the isolated smoke workspace had no audit log; fixed by seeding a minimal audit JSONL record.
- Initial POST redirect parsing missed the `Location` header because header lookup was case-sensitive; fixed with case-insensitive header lookup.

## Validation Evidence

- `python scripts/run_web_browser_smoke.py`: passed with `audit_archive_smoke=passed` and `web_browser_smoke=passed`.
- `python -m py_compile scripts/run_web_browser_smoke.py orchestrator/interfaces/web/main.py orchestrator/infrastructure/persistence/web_job_audit_log.py`: passed.
- `python -m pytest -q tests/test_web_browser_smoke.py`: 1 passed.
- `python -m pytest -q tests/test_web_ui.py tests/test_web_browser_smoke.py tests/test_demo_readiness_smoke.py`: 63 passed.
- `python -m pytest -q`: 155 passed.
- `git diff --check`: passed with only CRLF warnings.
