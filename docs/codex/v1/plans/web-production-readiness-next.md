# Web Production Readiness Next

## Goal

Continue the Web UI from local demo readiness toward production-grade operation by adding repeatable browser-path smoke coverage, then extending real external-agent execution evidence and operational controls.

## Current Increment: Web Browser Smoke

Add a script-level smoke that starts a real Uvicorn process in an isolated workspace and exercises the main operator routes over HTTP:

- `/`
- `/tasks`
- `/tasks/health.json`
- `/tasks/audit`
- `/tasks/audit.md`
- `/templates/run`
- `/jobs/{job_id}`
- `/runs/{run_id}`
- `/runs/{run_id}/audit.md`
- `/tasks/maintenance/prune-runs`

The increment intentionally uses only the Python standard library plus the existing Uvicorn/FastAPI stack. This avoids making local readiness depend on installing Playwright or browser binaries before the project has a committed browser-test dependency policy.

The smoke now also creates a local-backend `codex` external-agent run inside the same process-scoped workspace and verifies wrapper command provenance through real HTTP page/export requests. It remains credential-free because the wrapper delegates to a deterministic local backend command.

The smoke also seeds disposable old, fresh, running-linked, and malformed run artifact directories, posts the run-artifact cleanup maintenance form over HTTP, and verifies that only eligible old artifacts are deleted while audit evidence is written.

Each invocation uses its own `run-{pid}` workspace to tolerate concurrent pytest runs, and it prunes stale `run-*` workspaces older than 24 hours while ignoring locked directories.

## Acceptance Criteria

- The smoke starts the Web app as a real server process, not only through `TestClient`.
- The smoke uses an isolated `.tmp/web-browser-smoke/run-{pid}` workspace, prunes stale sibling workspaces, and does not mutate project task history.
- The smoke verifies health JSON, task manager controls, template-run redirect, job completion, run detail rendering, and task-list visibility.
- The smoke verifies archived audit source provenance and source/source-file filtering over real HTTP requests.
- The smoke verifies destructive run-artifact maintenance cleanup using seeded disposable artifacts only.
- The smoke verifies external-agent wrapper provenance on run detail and exported run audit Markdown over real HTTP requests.
- A pytest wrapper covers the script.

## Follow-Up Candidates

- Add optional Playwright coverage once dependency installation and browser binary provisioning are explicit.
- Add a real external-agent smoke variant gated by available `omx` / `codex` command configuration.
- Add deeper production maintenance browser coverage only for newly introduced destructive controls, with seeded disposable artifacts.

## Production Readiness Command

`scripts/run_production_readiness_smoke.py` is the one-command readiness entry point for urgent validation and demos. It runs the demo readiness smoke, external-agent closed-loop smoke, opt-in real external-agent gate, and Web HTTP smoke in sequence, then prints a pass/skip/fail summary.

The real external-agent stage is allowed to skip when `OMX_RUN_REAL_EXTERNAL_AGENT_SMOKE=1` is not set, so the command remains credential-free by default while still reporting that the real-command gate was not executed.

The command also catches stage timeouts and process launch failures, prints the failed stage as structured evidence, emits the aggregate summary, and exits non-zero without a Python traceback becoming the only diagnostic.

Pass `--summary-json <path>` to write the same pass/skip/fail evidence as machine-readable JSON for CI, Web dashboards, or handoff artifacts. The JSON file is written for both successful and failed aggregate runs, includes `schema_version`, UTC `generated_at`, per-stage `duration_seconds`, and an `environment` readiness block for Playwright plus real external-agent command configuration.
