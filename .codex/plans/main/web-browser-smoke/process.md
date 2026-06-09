# Web Browser Smoke Process

## Resume Capsule

- Task need: advance production readiness with a repeatable real-server Web smoke.
- Key decision: first use Uvicorn plus standard-library HTTP checks instead of adding Playwright dependency.
- Current phase: completed.
- Completed artifacts: `scripts/run_web_browser_smoke.py`, `tests/test_web_browser_smoke.py`, `docs/codex/v1/plans/web-production-readiness-next.md`, `docs/codex/v1/trace/web-production-readiness-next-trace.md`.
- Remaining work: commit/push after final git review.
- Important finding: repository has FastAPI/Uvicorn but no committed Playwright/Selenium dependency manifest.

## Steps

- [v] Inspect current Web UI routes, existing smoke scripts, and task-template behavior.
- [v] Add `scripts/run_web_browser_smoke.py`.
- [v] Add pytest wrapper `tests/test_web_browser_smoke.py`.
- [v] Validate smoke and update project status.

## Research Findings

- `/templates/run` can submit the `mock_demo` template, which keeps this smoke independent from Docker, OMX, Codex credentials, and browser binary installation.
- `/tasks/health.json` is read-only and suitable as the readiness gate before exercising form flows.

## Error Log

- Initial health check returned `warn` because the isolated smoke workspace had no audit log; fixed by seeding a minimal audit JSONL record.
- Initial POST redirect parsing missed the `Location` header because header lookup was case-sensitive; fixed with case-insensitive header lookup.

## Validation Evidence

- `python scripts/run_web_browser_smoke.py`: passed with `web_browser_smoke=passed`.
- `python -m py_compile scripts/run_web_browser_smoke.py`: passed.
- `python -m pytest -q tests/test_web_browser_smoke.py`: 1 passed.
- `python -m pytest -q tests/test_web_ui.py tests/test_web_browser_smoke.py tests/test_demo_readiness_smoke.py`: 61 passed.
- `python -m pytest -q`: 151 passed.
- `git diff --check`: passed with only CRLF warning for `.codex/plans/main/TASKS.md`.
