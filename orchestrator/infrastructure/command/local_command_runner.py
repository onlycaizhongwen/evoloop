from __future__ import annotations

import subprocess
import time
from pathlib import Path

from orchestrator.domain.models.run_state import RunState
from orchestrator.domain.models.task import TaskConfig
from orchestrator.domain.services.exceptions import SafetyViolation
from orchestrator.infrastructure.command.cancellation import (
    CancellationRegistry,
    CommandCancelled,
    terminate_process_tree,
)
from orchestrator.infrastructure.command.command_result import CommandExecutionResult
from orchestrator.ports.heartbeat_port import HeartbeatPort


class LocalCommandRunner:
    def __init__(
        self,
        heartbeat: HeartbeatPort | None = None,
        cancellation_registry: CancellationRegistry | None = None,
        cancellation_key: str | None = None,
    ):
        self.heartbeat = heartbeat
        self.cancellation_registry = cancellation_registry
        self.cancellation_key = cancellation_key

    def run(
        self,
        task: TaskConfig,
        command: str,
        phase: str,
        state: RunState | None = None,
        cwd: Path | None = None,
    ) -> CommandExecutionResult:
        started_at = time.monotonic()
        process = subprocess.Popen(
            command,
            cwd=cwd or task.worktree_path,
            shell=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self._register_process(process)

        try:
            while True:
                try:
                    stdout, stderr = process.communicate(timeout=task.heartbeat_interval_seconds)
                    break
                except subprocess.TimeoutExpired:
                    self._raise_if_cancelled(process)
                    if state and self.heartbeat:
                        elapsed = int(time.monotonic() - started_at)
                        self.heartbeat.beat(state, phase, f"status=running elapsed={elapsed}s")
                    if time.monotonic() - started_at > task.command_timeout_seconds:
                        self._terminate_process_tree(process)
                        stdout, stderr = process.communicate()
                        duration = time.monotonic() - started_at
                        return CommandExecutionResult(
                            command=command,
                            exit_code=124,
                            stdout=stdout or "",
                            stderr=(stderr or "") + f"\ncommand timed out after {task.command_timeout_seconds}s",
                            duration_seconds=duration,
                            timed_out=True,
                        )
        except SafetyViolation:
            self._terminate_process_tree(process)
            raise
        finally:
            self._unregister_process(process)

        self._raise_if_cancelled(process)

        duration = time.monotonic() - started_at
        return CommandExecutionResult(
            command=command,
            exit_code=process.returncode,
            stdout=stdout or "",
            stderr=stderr or "",
            duration_seconds=duration,
        )

    def _terminate_process_tree(self, process: subprocess.Popen[str]) -> None:
        terminate_process_tree(process)

    def _register_process(self, process: subprocess.Popen[str]) -> None:
        if self.cancellation_registry and self.cancellation_key:
            self.cancellation_registry.register(self.cancellation_key, process)

    def _unregister_process(self, process: subprocess.Popen[str]) -> None:
        if self.cancellation_registry and self.cancellation_key:
            self.cancellation_registry.unregister(self.cancellation_key, process)

    def _raise_if_cancelled(self, process: subprocess.Popen[str]) -> None:
        if self.cancellation_registry and self.cancellation_key and self.cancellation_registry.is_cancelled(
            self.cancellation_key
        ):
            terminate_process_tree(process)
            raise CommandCancelled(f"command cancelled: {self.cancellation_key}")
