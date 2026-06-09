# External Agent Closed Loop Smoke Process

## Resume Capsule

- Task need: advance real external agent execution closure with a script-level smoke.
- Key decision: use real external-command adapter and wrapper process, but local backend command to avoid credentials/network dependency.
- Current phase: completed.
- Completed artifacts: `scripts/run_external_agent_closed_loop_smoke.py`, `tests/test_external_agent_closed_loop_smoke.py`, `scripts/run_external_agent.py`, `docs/codex/v1/plans/external-agent-closed-loop-smoke.md`, `docs/codex/v1/trace/external-agent-closed-loop-smoke-trace.md`.
- Remaining work: commit/push after final git review.
- Important finding: existing tests cover adapters and wrapper units, but not a full script-level external-agent run loop.

## Steps

- [v] Inspect external agent adapter, wrapper, CLI, and existing tests.
- [v] Add `scripts/run_external_agent_closed_loop_smoke.py`.
- [v] Add pytest wrapper.
- [v] Validate and update trace/status.

## Research Findings

- `RunTaskUseCase` calls coder, hard checks, reviewer, quality gate, and final report in sequence.
- `ExternalCommandAgent` writes both prompt files and `logs/agent.log`; wrapper dry/backend paths can write `logs/external_agent_wrapper.log`.

## Error Log

- Initial command template used unsupported `{role}` placeholder in the orchestrator command renderer; fixed by generating role-specific wrapper commands.
- Quoted Python executable paths made the safety allowlist parser report an empty prefix; fixed by using the allowed `python` command prefix.
- Nested `--backend-command` quoting made the wrapper command brittle; fixed by passing backend commands through the wrapper's existing environment-variable contract.
- CLI returns `status=done`; the smoke now accepts both `done` and the older `RunStatus.DONE` spelling.

## Validation Evidence

- `python scripts/run_external_agent_closed_loop_smoke.py`: passed with `external_agent_closed_loop_smoke=passed`.
- `python -m py_compile scripts/run_external_agent.py scripts/run_external_agent_closed_loop_smoke.py`: passed.
- `python -m pytest -q tests/test_external_agent_closed_loop_smoke.py tests/test_external_agent.py tests/test_external_agent_wrapper.py`: 17 passed.
- `python -m pytest -q tests/test_external_agent_closed_loop_smoke.py tests/test_external_agent.py tests/test_external_agent_wrapper.py tests/test_web_browser_smoke.py tests/test_demo_readiness_smoke.py`: 19 passed.
- `python -m pytest -q`: 152 passed.
- `git diff --check`: passed with CRLF warnings only.
