from __future__ import annotations

import json
from pathlib import Path

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


class OmxPatchAgent(OmxAgent):
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
        self.adapter_name = "omx_patch"

    def run_coder(self, task: TaskConfig, state: RunState) -> None:
        command = task.agent_commands.patch_coder or task.agent_commands.coder
        if not command:
            self._append_agent_log(state, "patch coder: skipped; command not configured\n")
            return
        prompt = self.prompt_builder.build_patch_coder_prompt(task, state)
        prompt_file = self.prompt_builder.write_prompt_file(state, "patch_coder", prompt)
        self._run_patch_command(task, state, command, "patch_coder", prompt_file=prompt_file)

    def run_fixer(self, task: TaskConfig, state: RunState, reason: HardCheckResult | QualityReport) -> None:
        command = task.agent_commands.patch_fixer or task.agent_commands.fixer
        if not command:
            self._append_agent_log(state, "patch fixer: skipped; command not configured\n")
            return
        reason_file = self.prompt_builder.write_reason_file(state, reason)
        prompt = self.prompt_builder.build_patch_fixer_prompt(task, state, reason, reason_file)
        prompt_file = self.prompt_builder.write_prompt_file(state, "patch_fixer", prompt)
        self._run_patch_command(task, state, command, "patch_fixer", reason_file=reason_file, prompt_file=prompt_file)

    def _run_patch_command(
        self,
        task: TaskConfig,
        state: RunState,
        command: str,
        role: str,
        reason_file: Path | None = None,
        prompt_file: Path | None = None,
    ) -> None:
        raw_output = self._run_command(
            task,
            state,
            command,
            role,
            reason_file=reason_file,
            prompt_file=prompt_file,
        )
        diagnostics_path = self._write_patch_raw_output(state, role, raw_output)
        try:
            plan = self.patch_validator.parse_and_validate(raw_output, task)
            result = self.patch_applier.apply(task, plan, dry_run=True)
            if self.approval_policy.requires_approval(task, result):
                pending_path = self.pending_patch_writer.write(state, role, plan, result)
                state.artifacts["pending_patch"] = str(pending_path)
                raise PatchApprovalRequired(f"patch requires approval: {pending_path}")
            result = self.patch_applier.apply(task, plan)
        except (MalformedReview, PatchApplyError, PatchApprovalRequired) as exc:
            self._write_patch_diagnostics(state, role, raw_output, exc, diagnostics_path)
            raise AgentCommandError(str(exc)) from exc
        self._append_agent_log(
            state,
            (
                f"adapter={self.adapter_name}\nrole={role}\npatch_summary={plan.summary}\n"
                f"changed_files={result.changed_files}\ncreated_files={result.created_files}\n"
                f"deleted_files={result.deleted_files}\nrisk_score={result.risk_score}\n"
                f"risk_reasons={result.risk_reasons}\n---\n"
            ),
        )

    def _write_patch_raw_output(self, state: RunState, role: str, raw_output: str) -> Path:
        attempt_dir = self.prompt_builder.run_dir(state) / f"attempts/{state.attempt:03d}"
        attempt_dir.mkdir(parents=True, exist_ok=True)
        path = attempt_dir / f"{role}_patch_raw_output.txt"
        path.write_text(raw_output, encoding="utf-8")
        return path

    def _write_patch_diagnostics(
        self,
        state: RunState,
        role: str,
        raw_output: str,
        error: Exception,
        raw_output_path: Path,
    ) -> None:
        attempt_dir = self.prompt_builder.run_dir(state) / f"attempts/{state.attempt:03d}"
        path = attempt_dir / f"{role}_patch_diagnostics.json"
        payload = {
            "role": role,
            "error_type": type(error).__name__,
            "error": str(error),
            "raw_output_path": str(raw_output_path),
            "raw_output_preview": raw_output[:1000],
        }
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        state.artifacts["patch_diagnostics"] = str(path)
