from __future__ import annotations

from pathlib import Path

from orchestrator.domain.models.check_result import HardCheckResult
from orchestrator.domain.models.quality_report import QualityReport
from orchestrator.domain.models.run_state import RunState
from orchestrator.domain.models.task import TaskConfig
from orchestrator.domain.services.exceptions import SafetyViolation
from orchestrator.infrastructure.agents.prompt_builder import AgentPromptBuilder
from orchestrator.infrastructure.command.safe_command_runner import SafeCommandRunner
from orchestrator.infrastructure.exceptions import AgentCommandError


class ExternalCommandAgent:
    def __init__(
        self,
        command_runner: SafeCommandRunner | None = None,
        prompt_builder: AgentPromptBuilder | None = None,
        adapter_name: str = "external",
    ):
        self.command_runner = command_runner or SafeCommandRunner()
        self.prompt_builder = prompt_builder or AgentPromptBuilder()
        self.adapter_name = adapter_name

    def run_coder(self, task: TaskConfig, state: RunState) -> None:
        command = task.agent_commands.coder
        if not command:
            self._append_agent_log(state, "coder: skipped; command not configured\n")
            return
        prompt = self.prompt_builder.build_coder_prompt(task, state)
        prompt_file = self.prompt_builder.write_prompt_file(state, "coder", prompt)
        self._run_command(task, state, command, "coder", prompt_file=prompt_file)

    def run_fixer(self, task: TaskConfig, state: RunState, reason: HardCheckResult | QualityReport) -> None:
        command = task.agent_commands.fixer
        if not command:
            self._append_agent_log(state, "fixer: skipped; command not configured\n")
            return
        reason_file = self.prompt_builder.write_reason_file(state, reason)
        prompt = self.prompt_builder.build_fixer_prompt(task, state, reason, reason_file)
        prompt_file = self.prompt_builder.write_prompt_file(state, "fixer", prompt)
        self._run_command(task, state, command, "fixer", reason_file=reason_file, prompt_file=prompt_file)

    def run_reviewer(self, task: TaskConfig, state: RunState, repair_prompt: str | None = None) -> str:
        command = task.agent_commands.reviewer
        if not command:
            raise AgentCommandError(f"{self.adapter_name} reviewer command is not configured")
        prompt = self.prompt_builder.build_reviewer_prompt(task, state, repair_prompt)
        prompt_file = self.prompt_builder.write_prompt_file(state, "reviewer", prompt)
        return self._run_command(task, state, command, "reviewer", prompt_file=prompt_file)

    def _run_command(
        self,
        task: TaskConfig,
        state: RunState,
        command: str,
        role: str,
        reason_file: Path | None = None,
        prompt_file: Path | None = None,
    ) -> str:
        rendered = self.prompt_builder.render_command(
            task,
            state,
            command,
            reason_file=reason_file,
            prompt_file=prompt_file,
        )
        try:
            completed = self.command_runner.run(task, rendered, phase=f"agent:{self.adapter_name}:{role}", state=state)
        except SafetyViolation as exc:
            raise AgentCommandError(str(exc)) from exc
        self._append_agent_log(
            state,
            (
                f"adapter={self.adapter_name}\nrole={role}\ncommand={rendered}\nexit_code={completed.exit_code}\n"
                f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}\n---\n"
            ),
        )
        if completed.exit_code != 0:
            raise AgentCommandError(f"{self.adapter_name} {role} command failed with exit code {completed.exit_code}")
        return completed.stdout

    def _append_agent_log(self, state: RunState, content: str) -> None:
        log_dir = self.prompt_builder.run_dir(state) / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        with (log_dir / "agent.log").open("a", encoding="utf-8") as file:
            file.write(content)


class CodexAgent(ExternalCommandAgent):
    def __init__(self, command_runner: SafeCommandRunner | None = None, prompt_builder: AgentPromptBuilder | None = None):
        super().__init__(command_runner=command_runner, prompt_builder=prompt_builder, adapter_name="codex")


class OmxAgent(ExternalCommandAgent):
    def __init__(self, command_runner: SafeCommandRunner | None = None, prompt_builder: AgentPromptBuilder | None = None):
        super().__init__(command_runner=command_runner, prompt_builder=prompt_builder, adapter_name="omx")
