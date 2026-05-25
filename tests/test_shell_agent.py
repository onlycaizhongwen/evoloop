from __future__ import annotations

import json
import sys
from pathlib import Path

from orchestrator.application.dto.run_task_command import RunTaskCommand
from orchestrator.application.use_cases.run_task import RunTaskUseCase
from orchestrator.config.task_loader import TaskLoader
from orchestrator.domain.enums import ChangeType, RunStatus
from orchestrator.domain.models.task import AgentCommands, CheckCommands, TaskConfig
from orchestrator.domain.services.quality_gate import QualityGate
from orchestrator.domain.services.review_validator import ReviewValidator
from orchestrator.domain.services.safety_policy import SafetyPolicy
from orchestrator.infrastructure.agents.shell_agent import ShellAgent
from orchestrator.infrastructure.checks.fake_check_runner import FakeCheckRunner
from orchestrator.infrastructure.git.static_diff_provider import StaticDiffProvider
from orchestrator.infrastructure.persistence.file_state_repository import FileStateRepository
from orchestrator.report.final_report_writer import FinalReportWriter


def write_task(tmp_path: Path, reviewer_command: str, max_retries: int = 2) -> Path:
    task = TaskConfig(
        task_id="task-shell-001",
        title="Shell task",
        description="Shell task",
        change_type=ChangeType.BUGFIX,
        repo_path=tmp_path,
        worktree_path=tmp_path,
        allowed_paths=["."],
        forbidden_paths=[".env"],
        check_commands=CheckCommands(test=None),
        agent_commands=AgentCommands(reviewer=reviewer_command),
        max_review_json_retries=max_retries,
    )
    path = tmp_path / "task.json"
    path.write_text(json.dumps(task.model_dump(mode="json"), ensure_ascii=False), encoding="utf-8")
    return path


def build_use_case(base_dir: Path) -> RunTaskUseCase:
    return RunTaskUseCase(
        task_loader=TaskLoader(),
        safety_policy=SafetyPolicy(),
        state_repository=FileStateRepository(base_dir),
        agent=ShellAgent(),
        check_runner=FakeCheckRunner(pass_all=True),
        review_validator=ReviewValidator(),
        quality_gate=QualityGate(),
        diff_provider=StaticDiffProvider(),
        final_report_writer=FinalReportWriter(),
    )


def test_shell_agent_reviewer_returns_valid_json(tmp_path: Path):
    script = tmp_path / "reviewer.py"
    script.write_text(
        "import json, sys; print(json.dumps({'schema_version':'1.0','task_id':sys.argv[1],'pass':True,'confidence':90,'summary':'ok','issues':[],'blocking':False,'recommended_next_action':'pass'}))",
        encoding="utf-8",
    )
    task_path = write_task(tmp_path, f"\"{sys.executable}\" \"{script}\" {{task_id}}")
    state = build_use_case(tmp_path / "runs").execute(RunTaskCommand(task_path=task_path))
    assert state.status == RunStatus.DONE


def test_shell_agent_malformed_review_retries(tmp_path: Path):
    script = tmp_path / "reviewer_retry.py"
    counter = tmp_path / "counter.txt"
    script.write_text(
        "\n".join(
            [
                "import json, pathlib, sys",
                f"counter = pathlib.Path(r'{counter}')",
                "value = int(counter.read_text()) if counter.exists() else 0",
                "counter.write_text(str(value + 1))",
                "if value == 0:",
                "    print('not-json')",
                "else:",
                "    print(json.dumps({'schema_version':'1.0','task_id':sys.argv[1],'pass':True,'confidence':90,'summary':'ok','issues':[],'blocking':False,'recommended_next_action':'pass'}))",
            ]
        ),
        encoding="utf-8",
    )
    task_path = write_task(tmp_path, f"\"{sys.executable}\" \"{script}\" {{task_id}}")
    state = build_use_case(tmp_path / "runs").execute(RunTaskCommand(task_path=task_path))
    assert state.status == RunStatus.DONE
    malformed = list((tmp_path / "runs" / state.run_id / "attempts" / "001").glob("malformed_review_*.txt"))
    assert malformed
