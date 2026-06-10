# External Agent Closed Loop Smoke

## Goal

Add a repeatable smoke that proves the external command-agent contract works from task JSON through the orchestrator run loop, wrapper process, reviewer JSON validation, quality gate, and final report artifacts.

## Scope

- Use the existing `codex` external-command adapter.
- Use `scripts/run_external_agent.py` as the stable wrapper surface.
- Use a local backend command so the smoke does not require real Codex/OMX credentials or network access.
- Run in `.tmp/external-agent-closed-loop-smoke`.

## Acceptance Criteria

- The CLI returns `RunStatus.DONE`.
- The run directory contains `run_state.json`, `logs/agent.log`, `logs/external_agent_wrapper.log`, `attempts/001/review.json`, `attempts/001/quality_report.json`, and `final_report.md`.
- The smoke verifies wrapper runtime, role, exit-code, and backend-command provenance from `logs/external_agent_wrapper.log`.
- A pytest wrapper covers the smoke script.
- Web run detail surfaces wrapper command provenance from `logs/external_agent_wrapper.log`.
- Run audit Markdown exports the same wrapper command provenance for offline review.

## Follow-Up Candidates

- Add an opt-in real `omx` / `codex` command smoke when runtime configuration is present.
- Add deeper real-command browser smoke once runtime credentials and command configuration are available.

## Opt-In Real Command Smoke

`scripts/run_real_external_agent_smoke.py` provides the gated real-command path. By default it exits successfully with `real_external_agent_smoke=skipped`; it only runs when `OMX_RUN_REAL_EXTERNAL_AGENT_SMOKE=1` is set and the selected runtime has backend commands configured.

Required environment for `--runtime codex`:

- `OMX_RUN_REAL_EXTERNAL_AGENT_SMOKE=1`
- `OMX_CODEX_CODER_COMMAND`
- `OMX_CODEX_REVIEWER_COMMAND`

Required environment for `--runtime omx`:

- `OMX_RUN_REAL_EXTERNAL_AGENT_SMOKE=1`
- `OMX_OMX_CODER_COMMAND`
- `OMX_OMX_REVIEWER_COMMAND`

The backend command templates are rendered by `scripts/run_external_agent.py` with Python `str.format()`. Literal JSON braces in command strings must be escaped as `{{` and `}}`; placeholders such as `{task_id}`, `{prompt_file}`, `{worktree}`, and `{output_last_message}` remain single-braced.
