# Web Production Readiness Next

## Goal

Continue the Web UI from local demo readiness toward production-grade operation by adding repeatable browser-path smoke coverage, then extending real external-agent execution evidence and operational controls.

## Current Increment: Web Browser Smoke

Add a script-level smoke that starts a real Uvicorn process in an isolated workspace and exercises the main operator routes over HTTP:

- `/`
- `/tasks`
- `/tasks/health.json`
- `/templates/run`
- `/jobs/{job_id}`
- `/runs/{run_id}`

The first increment intentionally uses only the Python standard library plus the existing Uvicorn/FastAPI stack. This avoids making local readiness depend on installing Playwright or browser binaries before the project has a committed browser-test dependency policy.

## Acceptance Criteria

- The smoke starts the Web app as a real server process, not only through `TestClient`.
- The smoke uses an isolated `.tmp/web-browser-smoke` workspace and does not mutate project task history.
- The smoke verifies health JSON, task manager controls, template-run redirect, job completion, run detail rendering, and task-list visibility.
- A pytest wrapper covers the script.

## Follow-Up Candidates

- Add optional Playwright coverage once dependency installation and browser binary provisioning are explicit.
- Add a real external-agent smoke variant gated by available `omx` / `codex` command configuration.
- Add production maintenance controls for archived audit search and explicit run-artifact cleanup.
