# External Agent Closed Loop Smoke Trace

## Status

Completed.

## Covered Scope

- Task JSON generated in an isolated workspace.
- `codex` external-command adapter selected through CLI.
- `scripts/run_external_agent.py` wrapper invoked for coder and reviewer roles.
- Local backend command produces deterministic reviewer JSON.
- Orchestrator validates review JSON, evaluates quality gate, and writes final report artifacts.
- The smoke validates wrapper log provenance content: runtime, coder/reviewer roles, backend command count, and successful exit codes.
- Web run detail parses `logs/external_agent_wrapper.log` and shows wrapper runtime, roles, task IDs, exit code/dry-run status, backend command, prompt files, and raw diagnostics.
- Run audit Markdown exports the same wrapper provenance so offline audit summaries preserve command-level evidence.
- `scripts/run_real_external_agent_smoke.py` adds an opt-in real-command smoke gate for configured `codex` / `omx` backend commands. It skips safely by default and verifies real wrapper/backend provenance when explicitly enabled.

## Remaining Work

- Optional execution of the real `omx` / `codex` command smoke in a credentialed environment.
- Optional real-command browser smoke once runtime credentials and command configuration are available.

## Verification Evidence

- `python -m py_compile scripts/run_external_agent.py scripts/run_external_agent_closed_loop_smoke.py`: passed.
- `python -m pytest -q tests/test_external_agent_closed_loop_smoke.py tests/test_external_agent.py tests/test_external_agent_wrapper.py tests/test_web_browser_smoke.py tests/test_demo_readiness_smoke.py`: 19 passed.
- `python -m py_compile orchestrator/interfaces/web/main.py`: passed.
- `python -m py_compile scripts/run_external_agent_closed_loop_smoke.py`: passed.
- `python scripts/run_external_agent_closed_loop_smoke.py`: passed with `wrapper_runtime=codex`, `wrapper_roles=coder,reviewer`, `wrapper_exit_codes=0,0`, `wrapper_backend_commands=2`, and `external_agent_closed_loop_smoke=passed`.
- `python -m pytest -q tests/test_external_agent_closed_loop_smoke.py tests/test_external_agent.py tests/test_external_agent_wrapper.py`: 17 passed.
- `python -m pytest -q tests/test_web_ui.py -k "run_audit_markdown or wrapper_provenance or run_detail"`: 9 passed, 53 deselected.
- `python -m pytest -q tests/test_web_ui.py`: 62 passed.
- `python -m pytest -q`: 156 passed.
- `git diff --check`: passed; Git reported only Windows CRLF conversion warnings.
- `python -m py_compile scripts/run_real_external_agent_smoke.py tests/test_real_external_agent_smoke.py`: passed.
- `python -m pytest -q tests/test_real_external_agent_smoke.py`: 2 passed.
- `python scripts/run_real_external_agent_smoke.py`: skipped safely with `real_external_agent_smoke=skipped`.
