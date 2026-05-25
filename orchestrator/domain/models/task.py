from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field, field_validator

from orchestrator.domain.enums import AgentMode, ChangeType, ExecutionBackend


class CheckCommands(BaseModel):
    test: str | None = None
    lint: str | None = None
    typecheck: str | None = None


class AgentCommands(BaseModel):
    coder: str | None = None
    fixer: str | None = None
    reviewer: str | None = None
    patch_coder: str | None = None
    patch_fixer: str | None = None


class SandboxConfig(BaseModel):
    image: str = "auto-evolution-python:3.12"
    network: str = "none"
    worktree_mount: str = "readonly"
    run_mount: str = "rw"
    cache_mount: str = "rw"
    memory_limit: str = "2g"
    cpu_limit: float = Field(default=2, gt=0)
    user: str = "nonroot"
    environment: dict[str, str] = Field(default_factory=dict)
    container_workdir: str = "/worktree"

    @field_validator("network")
    @classmethod
    def validate_network(cls, value: str) -> str:
        if value not in {"none", "bridge"}:
            raise ValueError("sandbox.network must be one of: none, bridge")
        return value

    @field_validator("worktree_mount")
    @classmethod
    def validate_worktree_mount(cls, value: str) -> str:
        if value not in {"readonly", "rw"}:
            raise ValueError("sandbox.worktree_mount must be one of: readonly, rw")
        return value

    @field_validator("run_mount", "cache_mount")
    @classmethod
    def validate_rw_mount(cls, value: str) -> str:
        if value not in {"rw"}:
            raise ValueError("sandbox run/cache mounts must be rw")
        return value


class TaskConfig(BaseModel):
    task_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)
    change_type: ChangeType
    repo_path: Path
    worktree_path: Path
    allowed_paths: list[str] = Field(default_factory=list)
    forbidden_paths: list[str] = Field(default_factory=list)
    allowed_command_prefixes: list[str] = Field(
        default_factory=lambda: [
            "python",
            "python.exe",
            "py",
            "pytest",
            "ruff",
            "mypy",
            "npm test",
            "npm run test",
            "pnpm test",
            "pnpm run test",
        ]
    )
    check_commands: CheckCommands = Field(default_factory=CheckCommands)
    agent_mode: AgentMode = AgentMode.MOCK
    agent_commands: AgentCommands = Field(default_factory=AgentCommands)
    max_attempts: int = Field(default=3, ge=1)
    max_review_json_retries: int = Field(default=2, ge=0)
    heartbeat_interval_seconds: int = Field(default=30, ge=1)
    command_timeout_seconds: int = Field(default=300, ge=1)
    execution_backend: ExecutionBackend = ExecutionBackend.LOCAL
    sandbox: SandboxConfig = Field(default_factory=SandboxConfig)
    risk_level: str = "medium"
    patch_auto_apply: bool = True
    patch_approval_risk_threshold: int = Field(default=7, ge=0, le=10)
    patch_require_approval_on_delete: bool = True

    @field_validator("allowed_paths", "forbidden_paths")
    @classmethod
    def normalize_paths(cls, paths: list[str]) -> list[str]:
        return [path.replace("\\", "/").strip("/") for path in paths]

    @field_validator("allowed_command_prefixes")
    @classmethod
    def normalize_command_prefixes(cls, prefixes: list[str]) -> list[str]:
        return [prefix.strip() for prefix in prefixes if prefix.strip()]

    @property
    def default_permission_reason(self) -> str | None:
        if self.change_type == ChangeType.CONFIG:
            return "change_type_config_requires_elevated"
        return None
