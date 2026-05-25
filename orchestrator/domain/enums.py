from __future__ import annotations

from enum import StrEnum


class ChangeType(StrEnum):
    FEATURE = "feature"
    BUGFIX = "bugfix"
    REFACTOR = "refactor"
    CONFIG = "config"


class AgentMode(StrEnum):
    MOCK = "mock"
    SHELL = "shell"
    CODEX = "codex"
    OMX = "omx"
    OMX_PATCH = "omx_patch"
    OMX_TEAM_PATCH = "omx_team_patch"


class PermissionLevel(StrEnum):
    READ_ONLY = "read-only"
    WORKSPACE_WRITE = "workspace-write"
    ELEVATED = "elevated"
    FORBIDDEN = "forbidden"


class ExecutionBackend(StrEnum):
    LOCAL = "local"
    DOCKER = "docker"


class RunStatus(StrEnum):
    RUNNING = "running"
    RETRYING = "retrying"
    DONE = "done"
    HALTED = "halted"


class Decision(StrEnum):
    DONE = "done"
    RETRY = "retry"
    HALT = "halt"


class Severity(StrEnum):
    MINOR = "minor"
    MAJOR = "major"
    CRITICAL = "critical"
