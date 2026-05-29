from __future__ import annotations

from pathlib import Path

from orchestrator.domain.enums import ExecutionBackend
from orchestrator.domain.models.run_state import RunState
from orchestrator.domain.models.task import TaskConfig
from orchestrator.domain.services.safety_policy import SafetyPolicy
from orchestrator.infrastructure.command.cancellation import CancellationRegistry
from orchestrator.infrastructure.command.command_result import CommandExecutionResult
from orchestrator.infrastructure.command.docker_sandbox_runner import DockerSandboxRunner
from orchestrator.infrastructure.command.local_command_runner import LocalCommandRunner
from orchestrator.ports.heartbeat_port import HeartbeatPort


class SafeCommandRunner:
    def __init__(
        self,
        safety_policy: SafetyPolicy | None = None,
        heartbeat: HeartbeatPort | None = None,
        local_runner: LocalCommandRunner | None = None,
        docker_runner: DockerSandboxRunner | None = None,
        cancellation_registry: CancellationRegistry | None = None,
        cancellation_key: str | None = None,
    ):
        self.safety_policy = safety_policy or SafetyPolicy()
        self.heartbeat = heartbeat
        self.local_runner = local_runner or LocalCommandRunner(
            heartbeat=heartbeat,
            cancellation_registry=cancellation_registry,
            cancellation_key=cancellation_key,
        )
        self.docker_runner = docker_runner or DockerSandboxRunner(
            heartbeat=heartbeat,
            cancellation_registry=cancellation_registry,
            cancellation_key=cancellation_key,
        )

    def run(
        self,
        task: TaskConfig,
        command: str,
        phase: str,
        state: RunState | None = None,
        cwd: Path | None = None,
    ) -> CommandExecutionResult:
        self.safety_policy.validate_command(command, task)
        if task.execution_backend == ExecutionBackend.DOCKER:
            return self.docker_runner.run(task, command, phase, state=state, cwd=cwd)
        return self.local_runner.run(task, command, phase, state=state, cwd=cwd)
