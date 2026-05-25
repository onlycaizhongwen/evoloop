from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

from orchestrator.domain.models.run_state import RunState
from orchestrator.domain.models.task import TaskConfig
from orchestrator.domain.services.exceptions import SafetyViolation
from orchestrator.infrastructure.command.command_result import CommandExecutionResult
from orchestrator.ports.heartbeat_port import HeartbeatPort


class LocalCommandRunner:
    def __init__(self, heartbeat: HeartbeatPort | None = None):
        self.heartbeat = heartbeat

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

        try:
            while True:
                try:
                    stdout, stderr = process.communicate(timeout=task.heartbeat_interval_seconds)
                    break
                except subprocess.TimeoutExpired:
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

        duration = time.monotonic() - started_at
        return CommandExecutionResult(
            command=command,
            exit_code=process.returncode,
            stdout=stdout or "",
            stderr=stderr or "",
            duration_seconds=duration,
        )

    def _terminate_process_tree(self, process: subprocess.Popen[str]) -> None:
        if process.poll() is not None:
            return
        if sys.platform == "win32":
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(process.pid)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
            return
        process.kill()
