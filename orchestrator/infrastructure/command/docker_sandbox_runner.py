from __future__ import annotations

import json
import shlex
import subprocess
import sys
import time
from pathlib import Path

from orchestrator.domain.models.run_state import RunState
from orchestrator.domain.models.task import TaskConfig
from orchestrator.infrastructure.command.cancellation import (
    CancellationRegistry,
    CommandCancelled,
    terminate_process_tree,
)
from orchestrator.infrastructure.command.command_result import CommandExecutionResult
from orchestrator.ports.heartbeat_port import HeartbeatPort


class DockerSandboxRunner:
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
        docker_command = self.build_docker_command(task, command, state=state)
        started_at = time.monotonic()
        process = subprocess.Popen(
            docker_command,
            cwd=cwd or task.repo_path,
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
                        self.heartbeat.beat(state, phase, f"status=running backend=docker elapsed={elapsed}s")
                    if time.monotonic() - started_at > task.command_timeout_seconds:
                        self._terminate_container(process)
                        stdout, stderr = process.communicate()
                        duration = time.monotonic() - started_at
                        result = CommandExecutionResult(
                            command=docker_command,
                            exit_code=124,
                            stdout=stdout or "",
                            stderr=(stderr or "") + f"\ndocker command timed out after {task.command_timeout_seconds}s",
                            duration_seconds=duration,
                            timed_out=True,
                        )
                        self._write_log(task, state, phase, command, docker_command, result)
                        return result
        finally:
            self._unregister_process(process)

        self._raise_if_cancelled(process)

        duration = time.monotonic() - started_at
        result = CommandExecutionResult(
            command=docker_command,
            exit_code=process.returncode,
            stdout=stdout or "",
            stderr=stderr or "",
            duration_seconds=duration,
        )
        self._write_log(task, state, phase, command, docker_command, result)
        return result

    def build_docker_command(self, task: TaskConfig, command: str, state: RunState | None = None) -> str:
        sandbox = task.sandbox
        worktree_mount = "ro" if sandbox.worktree_mount == "readonly" else "rw"
        run_dir = self._run_dir(state, task)
        cache_dir = task.repo_path.resolve() / ".omx" / "cache" / "docker"
        run_dir.mkdir(parents=True, exist_ok=True)
        cache_dir.mkdir(parents=True, exist_ok=True)

        args = [
            "docker",
            "run",
            "--rm",
            "--network",
            sandbox.network,
            "--memory",
            sandbox.memory_limit,
            "--cpus",
            str(sandbox.cpu_limit),
            "-v",
            f"{task.worktree_path.resolve()}:/worktree:{worktree_mount}",
            "-v",
            f"{run_dir.resolve()}:/run:rw",
            "-v",
            f"{cache_dir.resolve()}:/cache:rw",
            "-w",
            sandbox.container_workdir,
        ]
        if sandbox.user == "nonroot":
            args.extend(["--user", "1000:1000"])
        elif sandbox.user:
            args.extend(["--user", sandbox.user])
        for key, value in sorted(sandbox.environment.items()):
            args.extend(["-e", f"{key}={value}"])
        args.append(sandbox.image)
        args.extend(self._shell_invocation(command))
        return " ".join(self._quote(part) for part in args)

    def _shell_invocation(self, command: str) -> list[str]:
        if sys.platform == "win32":
            return ["sh", "-lc", command]
        return ["sh", "-lc", command]

    def _run_dir(self, state: RunState | None, task: TaskConfig) -> Path:
        if state and state.artifacts.get("run_dir"):
            return Path(state.artifacts["run_dir"])
        return task.repo_path / ".omx" / "runs" / "docker-sandbox"

    def _write_log(
        self,
        task: TaskConfig,
        state: RunState | None,
        phase: str,
        command: str,
        docker_command: str,
        result: CommandExecutionResult,
    ) -> None:
        run_dir = self._run_dir(state, task)
        log_dir = run_dir / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "phase": phase,
            "image": task.sandbox.image,
            "command": command,
            "container_command": docker_command,
            "worktree_host_path": str(task.worktree_path.resolve()),
            "worktree_container_path": "/worktree",
            "network": task.sandbox.network,
            "worktree_mount": task.sandbox.worktree_mount,
            "exit_code": result.exit_code,
            "duration_seconds": result.duration_seconds,
            "timed_out": result.timed_out,
        }
        with (log_dir / "docker_sandbox.jsonl").open("a", encoding="utf-8") as file:
            file.write(json.dumps(payload, ensure_ascii=False) + "\n")

    def _terminate_container(self, process: subprocess.Popen[str]) -> None:
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

    def _quote(self, value: str) -> str:
        if sys.platform == "win32":
            return subprocess.list2cmdline([value])
        return shlex.quote(value)
