from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CommandExecutionResult:
    command: str
    exit_code: int
    stdout: str
    stderr: str
    duration_seconds: float
    timed_out: bool = False
