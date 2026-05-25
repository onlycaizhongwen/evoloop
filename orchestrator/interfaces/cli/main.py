from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from orchestrator.application.dto.run_task_command import RunTaskCommand
from orchestrator.application.use_cases.run_task import RunTaskUseCase
from orchestrator.application.use_cases.validate_applied_patch import ValidateAppliedPatchUseCase
from orchestrator.config.task_loader import TaskLoader
from orchestrator.domain.services.quality_gate import QualityGate
from orchestrator.domain.services.review_validator import ReviewValidator
from orchestrator.domain.services.safety_policy import SafetyPolicy
from orchestrator.infrastructure.agents.mock_agent import MockAgent
from orchestrator.infrastructure.agents.external_agent import CodexAgent, OmxAgent
from orchestrator.infrastructure.agents.shell_agent import ShellAgent
from orchestrator.infrastructure.agents.omx_patch_agent import OmxPatchAgent
from orchestrator.infrastructure.agents.omx_team_patch_agent import OmxTeamPatchAgent
from orchestrator.infrastructure.checks.fake_check_runner import FakeCheckRunner
from orchestrator.infrastructure.checks.shell_check_runner import ShellCheckRunner
from orchestrator.infrastructure.command.safe_command_runner import SafeCommandRunner
from orchestrator.infrastructure.git.git_diff_provider import GitDiffProvider
from orchestrator.infrastructure.git.static_diff_provider import StaticDiffProvider
from orchestrator.infrastructure.logging.file_heartbeat import FileHeartbeat
from orchestrator.infrastructure.patches.pending_patch_service import PendingPatchService
from orchestrator.infrastructure.persistence.file_state_repository import FileStateRepository
from orchestrator.report.final_report_writer import FinalReportWriter


def build_use_case(agent_mode: str = "mock", real_checks: bool = False, git_diff: bool = False) -> RunTaskUseCase:
    heartbeat = FileHeartbeat()
    command_runner = SafeCommandRunner(heartbeat=heartbeat)
    agent = build_agent(agent_mode, command_runner)
    return RunTaskUseCase(
        task_loader=TaskLoader(),
        safety_policy=SafetyPolicy(),
        state_repository=FileStateRepository(),
        agent=agent,
        check_runner=ShellCheckRunner(command_runner=command_runner) if real_checks else FakeCheckRunner(pass_all=True),
        review_validator=ReviewValidator(),
        quality_gate=QualityGate(),
        diff_provider=GitDiffProvider() if git_diff else StaticDiffProvider(),
        final_report_writer=FinalReportWriter(),
    )


def build_post_apply_validation_use_case(agent_mode: str = "mock", git_diff: bool = False) -> ValidateAppliedPatchUseCase:
    heartbeat = FileHeartbeat()
    command_runner = SafeCommandRunner(heartbeat=heartbeat)
    agent = build_agent(agent_mode, command_runner)
    return ValidateAppliedPatchUseCase(
        task_loader=TaskLoader(),
        state_repository=FileStateRepository(),
        agent=agent,
        check_runner=ShellCheckRunner(command_runner=command_runner),
        review_validator=ReviewValidator(),
        quality_gate=QualityGate(),
        diff_provider=GitDiffProvider() if git_diff else StaticDiffProvider(),
        final_report_writer=FinalReportWriter(),
    )


def build_agent(agent_mode: str, command_runner: SafeCommandRunner):
    if agent_mode == "shell":
        return ShellAgent(command_runner=command_runner)
    if agent_mode == "codex":
        return CodexAgent(command_runner=command_runner)
    if agent_mode == "omx":
        return OmxAgent(command_runner=command_runner)
    if agent_mode == "omx_patch":
        return OmxPatchAgent(command_runner=command_runner)
    if agent_mode == "omx_team_patch":
        return OmxTeamPatchAgent(command_runner=command_runner)
    return MockAgent()


def main() -> int:
    argv = sys.argv[1:]
    if not argv or argv[0] not in {"run", "resume", "rules", "patches"}:
        parser = argparse.ArgumentParser(description="Run auto-evolution coding task.")
        _add_run_arguments(parser)
        args = parser.parse_args(argv)
        state = _run_task(Path(args.task), args)
        print(f"run_id={state.run_id} status={state.status} phase={state.current_phase}")
        print(f"run_dir={state.artifacts.get('run_dir')}")
        return 0

    parser = argparse.ArgumentParser(description="Run auto-evolution coding task.")
    subparsers = parser.add_subparsers(dest="command")

    run_parser = subparsers.add_parser("run", help="Run a new task.")
    _add_run_arguments(run_parser)

    resume_parser = subparsers.add_parser("resume", help="Inspect or rerun a previous task from run_state.json.")
    resume_parser.add_argument("--run-id", required=True, help="Existing run id under .omx/runs.")
    resume_parser.add_argument("--rerun", action="store_true", help="Start a fresh run from the previous task.json.")
    _add_run_arguments(resume_parser, task_required=False)

    rules_parser = subparsers.add_parser("rules", help="List or review pending rule proposal clusters.")
    rules_subparsers = rules_parser.add_subparsers(dest="rules_command")
    rules_subparsers.add_parser("list", help="List rule proposal clusters.")
    review_parser = rules_subparsers.add_parser("review", help="Update a rule proposal cluster review status.")
    review_parser.add_argument("--cluster-key", required=True, help="Cluster key from rule_proposals_index.json.")
    review_parser.add_argument("--status", required=True, choices=["pending", "approved", "rejected"])
    review_parser.add_argument("--reviewer", default=None)
    review_parser.add_argument("--note", default=None)

    patches_parser = subparsers.add_parser("patches", help="List, apply, or reject pending patch files.")
    patches_subparsers = patches_parser.add_subparsers(dest="patches_command")
    list_patches_parser = patches_subparsers.add_parser("list", help="List pending patch files.")
    list_patches_parser.add_argument("--run-id", default=None)
    apply_patch_parser = patches_subparsers.add_parser("apply", help="Apply a pending patch file.")
    apply_patch_parser.add_argument("--run-id", required=True)
    apply_patch_parser.add_argument("--patch", required=True)
    apply_patch_parser.add_argument("--reviewer", default=None)
    apply_patch_parser.add_argument("--note", default=None)
    apply_patch_parser.add_argument("--rerun-checks", action="store_true")
    apply_patch_parser.add_argument("--rerun-task", action="store_true")
    reject_patch_parser = patches_subparsers.add_parser("reject", help="Reject a pending patch file.")
    reject_patch_parser.add_argument("--run-id", required=True)
    reject_patch_parser.add_argument("--patch", required=True)
    reject_patch_parser.add_argument("--reviewer", default=None)
    reject_patch_parser.add_argument("--note", default=None)

    args = parser.parse_args(argv)

    if args.command == "resume":
        return _resume(args)
    if args.command == "rules":
        return _rules(args)
    if args.command == "patches":
        return _patches(args)

    if not args.task:
        parser.error("--task is required")
        return 2
    task_path = Path(args.task)

    state = _run_task(task_path, args)
    print(f"run_id={state.run_id} status={state.status} phase={state.current_phase}")
    print(f"run_dir={state.artifacts.get('run_dir')}")
    return 0


def _add_run_arguments(parser: argparse.ArgumentParser, task_required: bool = True) -> None:
    parser.add_argument("--task", required=task_required, help="Path to task.json")
    parser.add_argument("--real-checks", action="store_true", help="Run configured shell check commands.")
    parser.add_argument("--git-diff", action="store_true", help="Use git diff stats instead of static mock diff.")
    parser.add_argument(
        "--agent",
        choices=["mock", "shell", "codex", "omx", "omx_patch", "omx_team_patch"],
        default=None,
        help="Agent adapter to use.",
    )


def _run_task(task_path: Path, args) -> object:
    agent_mode = args.agent or _read_agent_mode(task_path)
    use_case = build_use_case(agent_mode=agent_mode, real_checks=args.real_checks, git_diff=args.git_diff)
    return use_case.execute(RunTaskCommand(task_path=task_path))


def _resume(args) -> int:
    repository = FileStateRepository()
    state = repository.load_state(args.run_id)
    task_path = repository.task_path_for_run(args.run_id)
    print(f"run_id={state.run_id} status={state.status} phase={state.current_phase}")
    print(f"attempt={state.attempt}/{state.max_attempts}")
    print(f"run_dir={state.artifacts.get('run_dir')}")
    print(f"task={task_path}")
    if not args.rerun:
        print("resume_action=inspect")
        print("hint=use resume --run-id <id> --rerun to start a fresh run from this task.json")
        return 0

    args.task = str(task_path)
    rerun_state = _run_task(task_path, args)
    print(f"resume_action=rerun new_run_id={rerun_state.run_id} status={rerun_state.status} phase={rerun_state.current_phase}")
    print(f"new_run_dir={rerun_state.artifacts.get('run_dir')}")
    return 0


def _rules(args) -> int:
    repository = FileStateRepository()
    if args.rules_command == "review":
        cluster = repository.review_rule_proposal_cluster(
            args.cluster_key,
            args.status,
            reviewer=args.reviewer,
            note=args.note,
        )
        print(
            f"cluster_key={cluster.cluster_key} status={cluster.review_status} "
            f"observed_count={cluster.observed_count}"
        )
        return 0

    index = repository.load_rule_proposal_index()
    if not index.clusters:
        print("no_rule_proposal_clusters=true")
        return 0
    for cluster in sorted(index.clusters.values(), key=lambda item: item.last_seen_at, reverse=True):
        print(
            f"cluster_key={cluster.cluster_key} status={cluster.review_status} "
            f"source={cluster.source} observed_count={cluster.observed_count} "
            f"last_seen_run_id={cluster.last_seen_run_id} reason={cluster.reason}"
        )
    return 0


def _patches(args) -> int:
    service = PendingPatchService()
    if args.patches_command == "apply":
        summary = service.apply(
            args.run_id,
            args.patch,
            reviewer=args.reviewer,
            note=args.note,
            rerun_checks=args.rerun_checks,
        )
        if args.rerun_task:
            task_path = FileStateRepository().task_path_for_run(args.run_id)
            agent_mode = _read_agent_mode(task_path)
            rerun_state = build_post_apply_validation_use_case(agent_mode=agent_mode).execute(task_path)
            summary = service.record_rerun_task(args.run_id, args.patch, rerun_state)
        _print_patch_summary(summary)
        return 0
    if args.patches_command == "reject":
        summary = service.reject(args.run_id, args.patch, reviewer=args.reviewer, note=args.note)
        _print_patch_summary(summary)
        return 0

    patches = service.list(run_id=args.run_id)
    if not patches:
        print("no_pending_patches=true")
        return 0
    for patch in patches:
        _print_patch_summary(patch)
    return 0


def _print_patch_summary(summary: dict) -> None:
    print(
        f"patch={summary['patch']} run_id={summary['run_id']} task_id={summary['task_id']} "
        f"status={summary['status']} risk_score={summary['risk_score']} "
        f"ops={summary['ops']} files={summary['files']} checks_status={summary.get('checks_status')} "
        f"checks_passed={summary['checks_passed']} rerun_status={summary.get('rerun_status')} "
        f"rerun_run_id={summary.get('rerun_run_id')} rerun_phase={summary.get('rerun_phase')} "
        f"rerun_attempt={summary.get('rerun_attempt')} rerun_reason={summary.get('rerun_reason')}"
    )


def _read_agent_mode(task_path: Path) -> str:
    payload = json.loads(task_path.read_text(encoding="utf-8"))
    return payload.get("agent_mode", "mock")


if __name__ == "__main__":
    raise SystemExit(main())
