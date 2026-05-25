from __future__ import annotations

from orchestrator.domain.models.check_result import HardCheckResult
from orchestrator.domain.models.quality_report import QualityReport
from orchestrator.domain.models.run_state import RunState
from orchestrator.domain.models.task import TaskConfig
from orchestrator.domain.services.exceptions import SafetyViolation
from orchestrator.infrastructure.agents.prompt_builder import AgentPromptBuilder
from orchestrator.infrastructure.command.safe_command_runner import SafeCommandRunner
from orchestrator.infrastructure.exceptions import AgentCommandError


class ShellAgent:
    def __init__(self, command_runner: SafeCommandRunner | None = None, prompt_builder: AgentPromptBuilder | None = None):
        self.command_runner = command_runner or SafeCommandRunner()
        self.prompt_builder = prompt_builder or AgentPromptBuilder()

    def run_coder(self, task: TaskConfig, state: RunState) -> None:
        self._run_optional_command(task, state, task.agent_commands.coder, "coder")

    def run_fixer(self, task: TaskConfig, state: RunState, reason: HardCheckResult | QualityReport) -> None:
        reason_path = self.prompt_builder.write_reason_file(state, reason)
        self._run_optional_command(task, state, task.agent_commands.fixer, "fixer", reason_file=reason_path)

    def run_reviewer(self, task: TaskConfig, state: RunState, repair_prompt: str | None = None) -> str:
        command = task.agent_commands.reviewer
        if not command:
            raise AgentCommandError("shell reviewer command is not configured")
        repair_prompt_file = None
        if repair_prompt is not None:
            repair_prompt_file = self.prompt_builder.run_dir(state) / "repair_prompt.txt"
            repair_prompt_file.write_text(repair_prompt, encoding="utf-8")
        return self._run_required_command(task, state, command, "reviewer", repair_prompt_file=repair_prompt_file)

    def _run_optional_command(
        self,
        task: TaskConfig,
        state: RunState,
        command: str | None,
        role: str,
        reason_file: Path | None = None,
    ) -> None:
        if not command:
            self._append_agent_log(state, f"{role}: skipped; command not configured\n")
            return
        self._run_required_command(task, state, command, role, reason_file=reason_file)

    def _run_required_command(
        self,
        task: TaskConfig,
        state: RunState,
        command: str,
        role: str,
        reason_file: Path | None = None,
        repair_prompt_file: Path | None = None,
    ) -> str:
        rendered = self.prompt_builder.render_command(
            task,
            state,
            command,
            reason_file=reason_file,
            repair_prompt_file=repair_prompt_file,
        )
        try:
            completed = self.command_runner.run(task, rendered, phase=f"agent:{role}", state=state)
        except SafetyViolation as exc:
            raise AgentCommandError(str(exc)) from exc
        self._append_agent_log(
            state,
            (
                f"role={role}\ncommand={rendered}\nexit_code={completed.exit_code}\n"
                f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}\n---\n"
            ),
        )
        if completed.exit_code != 0:
            raise AgentCommandError(f"{role} command failed with exit code {completed.exit_code}")
        return completed.stdout

    def _append_agent_log(self, state: RunState, content: str) -> None:
        log_dir = self.prompt_builder.run_dir(state) / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        with (log_dir / "agent.log").open("a", encoding="utf-8") as file:
            file.write(content)
