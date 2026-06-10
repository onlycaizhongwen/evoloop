# External Agent Closed Loop Smoke Process

## Resume Capsule

- Task need: advance real external agent execution closure with a script-level smoke.
- Key decision: use real external-command adapter and wrapper process, but local backend command to avoid credentials/network dependency.
- Current phase: completed.
- Completed artifacts: `scripts/run_external_agent_closed_loop_smoke.py`, `tests/test_external_agent_closed_loop_smoke.py`, `scripts/run_external_agent.py`, Web run-detail and run-audit Markdown wrapper provenance, `docs/codex/v1/plans/external-agent-closed-loop-smoke.md`, `docs/codex/v1/trace/external-agent-closed-loop-smoke-trace.md`.
- Remaining work: optional real `omx` / `codex` command smoke when runtime configuration and credentials are present.
- Important finding: existing tests cover adapters and wrapper units, but not a full script-level external-agent run loop.

## Steps

- [v] Inspect external agent adapter, wrapper, CLI, and existing tests.
- [v] Add `scripts/run_external_agent_closed_loop_smoke.py`.
- [v] Add pytest wrapper.
- [v] Make the smoke assert wrapper log runtime, role, exit-code, and backend-command evidence.
- [v] Surface external-agent wrapper command provenance in Web run detail.
- [v] Include external-agent wrapper command provenance in exported run audit Markdown.
- [v] Validate and update trace/status.

## Research Findings

- `RunTaskUseCase` calls coder, hard checks, reviewer, quality gate, and final report in sequence.
- `ExternalCommandAgent` writes both prompt files and `logs/agent.log`; wrapper dry/backend paths can write `logs/external_agent_wrapper.log`.
- The wrapper log is already append-only `key=value` blocks separated by `---`, so Web can parse it read-only without changing the wrapper contract.
- The smoke now validates wrapper provenance content directly: `wrapper_runtime=codex`, `wrapper_roles=coder,reviewer`, `wrapper_exit_codes=0,0`, and `wrapper_backend_commands=2`.

## Error Log

- Initial command template used unsupported `{role}` placeholder in the orchestrator command renderer; fixed by generating role-specific wrapper commands.
- Quoted Python executable paths made the safety allowlist parser report an empty prefix; fixed by using the allowed `python` command prefix.
- Nested `--backend-command` quoting made the wrapper command brittle; fixed by passing backend commands through the wrapper's existing environment-variable contract.
- CLI returns `status=done`; the smoke now accepts both `done` and the older `RunStatus.DONE` spelling.

## Validation Evidence

- `python -m py_compile scripts/run_external_agent.py scripts/run_external_agent_closed_loop_smoke.py`: passed.
- `python -m pytest -q tests/test_external_agent_closed_loop_smoke.py tests/test_external_agent.py tests/test_external_agent_wrapper.py tests/test_web_browser_smoke.py tests/test_demo_readiness_smoke.py`: 19 passed.
- `python -m py_compile orchestrator/interfaces/web/main.py`: passed.
- `python -m py_compile scripts/run_external_agent_closed_loop_smoke.py`: passed.
- `python scripts/run_external_agent_closed_loop_smoke.py`: passed with `wrapper_runtime=codex`, `wrapper_roles=coder,reviewer`, `wrapper_exit_codes=0,0`, `wrapper_backend_commands=2`, and `external_agent_closed_loop_smoke=passed`.
- `python -m pytest -q tests/test_external_agent_closed_loop_smoke.py tests/test_external_agent.py tests/test_external_agent_wrapper.py`: 17 passed.
- `python -m pytest -q tests/test_web_ui.py -k "run_audit_markdown or wrapper_provenance or run_detail"`: 9 passed, 53 deselected.
- `python -m pytest -q tests/test_web_ui.py`: 62 passed.
- `python -m pytest -q`: 156 passed.
- `git diff --check`: passed with CRLF warnings only.
