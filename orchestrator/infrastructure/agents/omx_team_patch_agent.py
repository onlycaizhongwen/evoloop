from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field, ValidationError

from orchestrator.domain.models.check_result import HardCheckResult
from orchestrator.domain.models.quality_report import QualityReport
from orchestrator.domain.models.run_state import RunState
from orchestrator.domain.models.task import TaskConfig
from orchestrator.domain.services.exceptions import MalformedReview
from orchestrator.domain.services.patch_validator import PatchValidator
from orchestrator.infrastructure.agents.external_agent import OmxAgent
from orchestrator.infrastructure.agents.prompt_builder import AgentPromptBuilder
from orchestrator.infrastructure.command.safe_command_runner import SafeCommandRunner
from orchestrator.infrastructure.exceptions import AgentCommandError
from orchestrator.infrastructure.patches.patch_approval import (
    PatchApprovalPolicy,
    PatchApprovalRequired,
    PendingPatchWriter,
)
from orchestrator.infrastructure.patches.patch_applier import PatchApplier, PatchApplyError


class TeamRoleStatus(BaseModel):
    status: str
    artifact: str | None = None
    summary: str = ""


class TeamResult(BaseModel):
    schema_version: str = "1.0"
    task_id: str = Field(min_length=1)
    status: str
    roles: dict[str, TeamRoleStatus] = Field(default_factory=dict)
    artifacts: dict[str, object] = Field(default_factory=dict)
    diagnostics: list[object] = Field(default_factory=list)


class OmxTeamPatchAgent(OmxAgent):
    def __init__(
        self,
        command_runner: SafeCommandRunner | None = None,
        prompt_builder: AgentPromptBuilder | None = None,
        patch_validator: PatchValidator | None = None,
        patch_applier: PatchApplier | None = None,
        approval_policy: PatchApprovalPolicy | None = None,
        pending_patch_writer: PendingPatchWriter | None = None,
    ):
        super().__init__(command_runner=command_runner, prompt_builder=prompt_builder)
        self.patch_validator = patch_validator or PatchValidator()
        self.patch_applier = patch_applier or PatchApplier()
        self.approval_policy = approval_policy or PatchApprovalPolicy()
        self.pending_patch_writer = pending_patch_writer or PendingPatchWriter()
        self.adapter_name = "omx_team_patch"
        self._review_outputs: dict[str, str] = {}

    def run_coder(self, task: TaskConfig, state: RunState) -> None:
        command = task.agent_commands.patch_coder or task.agent_commands.coder
        if not command:
            self._append_agent_log(state, "team patch coder: skipped; command not configured\n")
            return

        prompt = self._build_team_prompt(task, state)
        prompt_file = self.prompt_builder.write_prompt_file(state, "team", prompt)
        raw_output = self._run_command(task, state, command, "team", prompt_file=prompt_file)
        raw_output_path = self._write_team_raw_output(state, raw_output)

        try:
            team_result = self._parse_team_result(raw_output, task)
            patch_payload = self._required_artifact(team_result, "patch_plan")
            review_payload = self._required_artifact(team_result, "review")
            patch_raw = json.dumps(patch_payload, ensure_ascii=False)
            plan = self.patch_validator.parse_and_validate(patch_raw, task)
            result = self.patch_applier.apply(task, plan, dry_run=True)
            self._review_outputs[state.run_id] = json.dumps(review_payload, ensure_ascii=False)
            self._write_team_artifacts(state, team_result)
            if self.approval_policy.requires_approval(task, result):
                pending_path = self.pending_patch_writer.write(state, "team_patch_coder", plan, result)
                state.artifacts["pending_patch"] = str(pending_path)
                raise PatchApprovalRequired(f"patch requires approval: {pending_path}")
            result = self.patch_applier.apply(task, plan)
        except (MalformedReview, PatchApplyError, PatchApprovalRequired, ValueError, ValidationError) as exc:
            self._write_team_diagnostics(state, raw_output, exc, raw_output_path)
            raise AgentCommandError(str(exc)) from exc

        self._append_agent_log(
            state,
            (
                f"adapter={self.adapter_name}\nrole=team\nteam_status={team_result.status}\n"
                f"patch_summary={plan.summary}\nchanged_files={result.changed_files}\n"
                f"created_files={result.created_files}\ndeleted_files={result.deleted_files}\n"
                f"risk_score={result.risk_score}\nrisk_reasons={result.risk_reasons}\n---\n"
            ),
        )

    def run_fixer(self, task: TaskConfig, state: RunState, reason: HardCheckResult | QualityReport) -> None:
        command = task.agent_commands.patch_fixer or task.agent_commands.fixer
        if not command:
            self._append_agent_log(state, "team patch fixer: skipped; command not configured\n")
            return
        reason_file = self.prompt_builder.write_reason_file(state, reason)
        prompt = self._build_team_prompt(task, state, reason_file=reason_file, reason=reason)
        prompt_file = self.prompt_builder.write_prompt_file(state, "team_fixer", prompt)
        raw_output = self._run_command(task, state, command, "team_fixer", reason_file=reason_file, prompt_file=prompt_file)
        raw_output_path = self._write_team_raw_output(state, raw_output, role="team_fixer")
        try:
            team_result = self._parse_team_result(raw_output, task)
            patch_payload = team_result.artifacts.get("fix_patch_plan") or self._required_artifact(
                team_result,
                "patch_plan",
            )
            patch_raw = json.dumps(patch_payload, ensure_ascii=False)
            plan = self.patch_validator.parse_and_validate(patch_raw, task)
            result = self.patch_applier.apply(task, plan)
            self._write_team_artifacts(state, team_result, role="team_fixer")
        except (MalformedReview, PatchApplyError, ValueError, ValidationError) as exc:
            self._write_team_diagnostics(state, raw_output, exc, raw_output_path, role="team_fixer")
            raise AgentCommandError(str(exc)) from exc
        self._append_agent_log(
            state,
            (
                f"adapter={self.adapter_name}\nrole=team_fixer\nteam_status={team_result.status}\n"
                f"patch_summary={plan.summary}\nchanged_files={result.changed_files}\n"
                f"created_files={result.created_files}\ndeleted_files={result.deleted_files}\n---\n"
            ),
        )

    def run_reviewer(self, task: TaskConfig, state: RunState, repair_prompt: str | None = None) -> str:
        if repair_prompt:
            self._review_outputs.pop(state.run_id, None)
            return super().run_reviewer(task, state, repair_prompt=repair_prompt)
        cached = self._review_outputs.get(state.run_id)
        if cached:
            self._append_agent_log(state, "adapter=omx_team_patch\nrole=reviewer\nsource=team_result_cache\n---\n")
            return cached
        return super().run_reviewer(task, state, repair_prompt=repair_prompt)

    def _build_team_prompt(
        self,
        task: TaskConfig,
        state: RunState,
        *,
        reason_file: Path | None = None,
        reason: HardCheckResult | QualityReport | None = None,
    ) -> str:
        lines = [
            "You are an OMX team orchestrating a controlled coding task.",
            "Do not edit files directly. Return only team_result JSON.",
            f"Task ID: {task.task_id}",
            f"Title: {task.title}",
            f"Change type: {task.change_type}",
            f"Attempt: {state.attempt}/{state.max_attempts}",
            f"Worktree: {task.worktree_path}",
            f"Allowed paths: {task.allowed_paths}",
            f"Forbidden paths: {task.forbidden_paths}",
            "",
            "Description:",
            task.description,
            "",
            self.prompt_builder._render_allowed_file_snapshot(task),
            "",
            "Required final artifacts: artifacts.patch_plan and artifacts.review.",
            "patch_plan must match the existing PatchPlan schema.",
            "review must match the existing review.json schema.",
        ]
        if reason_file and reason:
            lines.extend(["", f"Failure reason file: {reason_file}", self._summarize_reason(reason)])
        lines.extend(
            [
                "",
                "Return JSON shape:",
                '{"schema_version":"1.0","task_id":"'
                + task.task_id
                + '","status":"completed","roles":{},"artifacts":{"patch_plan":{},"review":{}},"diagnostics":[]}',
            ]
        )
        return "\n".join(lines)

    def _summarize_reason(self, reason: HardCheckResult | QualityReport) -> str:
        if isinstance(reason, HardCheckResult):
            return reason.first_failure_reason() or "hard check failed"
        return reason.reason

    def _parse_team_result(self, raw_output: str, task: TaskConfig) -> TeamResult:
        try:
            payload = json.loads(self._extract_json(raw_output))
            result = TeamResult.model_validate(payload)
        except (json.JSONDecodeError, ValidationError) as exc:
            raise MalformedReview(f"team_result_json_malformed: {exc}") from exc
        if result.task_id != task.task_id:
            raise MalformedReview(f"team task_id mismatch: expected={task.task_id} actual={result.task_id}")
        if result.status not in {"completed", "partial"}:
            raise ValueError(f"team result status is not usable: {result.status}")
        return result

    def _required_artifact(self, result: TeamResult, name: str) -> object:
        artifact = result.artifacts.get(name)
        if artifact is None:
            raise ValueError(f"team result missing artifacts.{name}")
        return artifact

    def _extract_json(self, raw_output: str) -> str:
        text = raw_output.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            text = "\n".join(lines).strip()
        if text.startswith("{"):
            return text
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            return text[start : end + 1]
        return text

    def _attempt_dir(self, state: RunState) -> Path:
        path = self.prompt_builder.run_dir(state) / f"attempts/{state.attempt:03d}"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _write_team_raw_output(self, state: RunState, raw_output: str, role: str = "team") -> Path:
        path = self._attempt_dir(state) / f"{role}_result_raw_output.txt"
        path.write_text(raw_output, encoding="utf-8")
        return path

    def _write_team_artifacts(self, state: RunState, result: TeamResult, role: str = "team") -> None:
        path = self._attempt_dir(state) / f"{role}_result.json"
        path.write_text(json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2), encoding="utf-8")
        state.artifacts[f"{role}_result"] = str(path)

    def _write_team_diagnostics(
        self,
        state: RunState,
        raw_output: str,
        error: Exception,
        raw_output_path: Path,
        role: str = "team",
    ) -> None:
        path = self._attempt_dir(state) / f"{role}_diagnostics.json"
        payload = {
            "role": role,
            "error_type": type(error).__name__,
            "error": str(error),
            "raw_output_path": str(raw_output_path),
            "raw_output_preview": raw_output[:1000],
        }
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        state.artifacts[f"{role}_diagnostics"] = str(path)
