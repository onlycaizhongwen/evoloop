from __future__ import annotations

import json
import sys
from pathlib import Path

from orchestrator.application.dto.run_task_command import RunTaskCommand
from orchestrator.application.use_cases.run_task import RunTaskUseCase
from orchestrator.config.task_loader import TaskLoader
from orchestrator.domain.enums import AgentMode, ChangeType, ExecutionBackend, RunStatus
from orchestrator.domain.models.check_result import CheckCommandResult, HardCheckResult
from orchestrator.domain.models.run_state import RunState
from orchestrator.domain.models.task import AgentCommands, CheckCommands, TaskConfig
from orchestrator.domain.services.quality_gate import QualityGate
from orchestrator.domain.services.review_validator import ReviewValidator
from orchestrator.domain.services.safety_policy import SafetyPolicy
from orchestrator.infrastructure.agents.external_agent import CodexAgent, OmxAgent
from orchestrator.infrastructure.agents.prompt_builder import AgentPromptBuilder
from orchestrator.infrastructure.checks.fake_check_runner import FakeCheckRunner
from orchestrator.infrastructure.git.static_diff_provider import StaticDiffProvider
from orchestrator.infrastructure.persistence.file_state_repository import FileStateRepository
from orchestrator.report.final_report_writer import FinalReportWriter


def write_task(
    tmp_path: Path,
    reviewer_command: str,
    agent_mode: AgentMode = AgentMode.CODEX,
    coder_command: str | None = None,
    fixer_command: str | None = None,
) -> Path:
    task = TaskConfig(
        task_id="task-codex-001",
        title="Codex adapter task",
        description="Exercise external command agent adapter.",
        change_type=ChangeType.BUGFIX,
        repo_path=tmp_path,
        worktree_path=tmp_path,
        allowed_paths=["."],
        forbidden_paths=[".env"],
        check_commands=CheckCommands(test=None),
        agent_mode=agent_mode,
        agent_commands=AgentCommands(coder=coder_command, fixer=fixer_command, reviewer=reviewer_command),
        max_review_json_retries=1,
    )
    path = tmp_path / "task.json"
    path.write_text(json.dumps(task.model_dump(mode="json"), ensure_ascii=False), encoding="utf-8")
    return path


def build_use_case(base_dir: Path, agent) -> RunTaskUseCase:
    return RunTaskUseCase(
        task_loader=TaskLoader(),
        safety_policy=SafetyPolicy(),
        state_repository=FileStateRepository(base_dir),
        agent=agent,
        check_runner=FakeCheckRunner(pass_all=True),
        review_validator=ReviewValidator(),
        quality_gate=QualityGate(),
        diff_provider=StaticDiffProvider(),
        final_report_writer=FinalReportWriter(),
    )


def test_prompt_builder_renders_command_context(tmp_path: Path):
    state = RunState(
        run_id="run-test",
        task_id="task-001",
        attempt=2,
        max_attempts=3,
        artifacts={"run_dir": str(tmp_path)},
    )
    task = TaskConfig(
        task_id="task-001",
        title="Prompt task",
        description="Prompt task",
        change_type=ChangeType.BUGFIX,
        repo_path=tmp_path,
        worktree_path=tmp_path,
    )

    rendered = AgentPromptBuilder().render_command(
        task,
        state,
        "agent --task {task_id} --prompt {prompt_file} --run {run_dir} --attempt {attempt}",
        prompt_file=tmp_path / "prompt.txt",
    )

    assert "--task task-001" in rendered
    assert "--prompt" in rendered
    assert "--attempt 2" in rendered


def test_prompt_builder_renders_file_placeholders_as_absolute_paths(tmp_path: Path):
    run_dir = tmp_path / "runs" / "run-test"
    run_dir.mkdir(parents=True)
    state = RunState(
        run_id="run-test",
        task_id="task-001",
        attempt=1,
        max_attempts=3,
        artifacts={"run_dir": str(run_dir)},
    )
    task = TaskConfig(
        task_id="task-001",
        title="Prompt task",
        description="Prompt task",
        change_type=ChangeType.BUGFIX,
        repo_path=tmp_path,
        worktree_path=tmp_path / "worktree",
    )
    prompt_file = run_dir / "attempts" / "001" / "coder_prompt.txt"

    rendered = AgentPromptBuilder().render_command(
        task,
        state,
        "agent --prompt {prompt_file} --run {run_dir} --attempt-dir {attempt_dir} --task-json {task_json}",
        prompt_file=prompt_file,
    )

    assert str(prompt_file.resolve()) in rendered
    assert str(run_dir.resolve()) in rendered
    assert str((run_dir / "attempts" / "001").resolve()) in rendered
    assert str((run_dir / "task.json").resolve()) in rendered


def test_prompt_builder_maps_file_placeholders_to_docker_paths(tmp_path: Path):
    run_dir = tmp_path / "runs" / "run-test"
    run_dir.mkdir(parents=True)
    state = RunState(
        run_id="run-test",
        task_id="task-001",
        attempt=1,
        max_attempts=3,
        artifacts={"run_dir": str(run_dir)},
    )
    task = TaskConfig(
        task_id="task-001",
        title="Prompt task",
        description="Prompt task",
        change_type=ChangeType.BUGFIX,
        repo_path=tmp_path,
        worktree_path=tmp_path / "worktree",
        execution_backend=ExecutionBackend.DOCKER,
    )
    prompt_file = run_dir / "attempts" / "001" / "coder_prompt.txt"

    rendered = AgentPromptBuilder().render_command(
        task,
        state,
        (
            "agent --prompt {prompt_file} --run {run_dir} --attempt-dir {attempt_dir} "
            "--task-json {task_json} --worktree {worktree}"
        ),
        prompt_file=prompt_file,
    )

    assert "--prompt /run/attempts/001/coder_prompt.txt" in rendered
    assert "--run /run" in rendered
    assert "--attempt-dir /run/attempts/001" in rendered
    assert "--task-json /run/task.json" in rendered
    assert "--worktree /worktree" in rendered
    assert str(run_dir.resolve()) not in rendered


def test_docker_agent_patch_smoke_script_compiles():
    script = Path("scripts/run_docker_agent_patch_smoke.py")

    completed = __import__("subprocess").run(
        [sys.executable, "-m", "py_compile", str(script)],
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr


def test_patch_prompt_includes_allowed_file_snapshot(tmp_path: Path):
    source = tmp_path / "calculator.py"
    source.write_text("def add(a, b):\n    return a - b\n", encoding="utf-8")
    state = RunState(
        run_id="run-test",
        task_id="task-001",
        attempt=1,
        max_attempts=3,
        artifacts={"run_dir": str(tmp_path / "run")},
    )
    task = TaskConfig(
        task_id="task-001",
        title="Patch task",
        description="Fix add",
        change_type=ChangeType.BUGFIX,
        repo_path=tmp_path,
        worktree_path=tmp_path,
        allowed_paths=["calculator.py"],
    )

    prompt = AgentPromptBuilder().build_patch_coder_prompt(task, state)

    assert "--- file: calculator.py ---" in prompt
    assert "return a - b" in prompt


def test_codex_agent_adapter_runs_reviewer_command_and_writes_prompt(tmp_path: Path):
    script = tmp_path / "reviewer.py"
    script.write_text(
        "\n".join(
            [
                "import json, pathlib, sys",
                "prompt = pathlib.Path(sys.argv[2])",
                "assert 'Reviewer agent' in prompt.read_text(encoding='utf-8')",
                "print(json.dumps({'schema_version':'1.0','task_id':sys.argv[1],'pass':True,'confidence':90,'summary':'ok','issues':[],'blocking':False,'recommended_next_action':'pass'}))",
            ]
        ),
        encoding="utf-8",
    )
    task_path = write_task(tmp_path, f"\"{sys.executable}\" \"{script}\" {{task_id}} {{prompt_file}}")

    state = build_use_case(tmp_path / "runs", CodexAgent()).execute(RunTaskCommand(task_path=task_path))

    assert state.status == RunStatus.DONE
    prompt_file = tmp_path / "runs" / state.run_id / "attempts" / "001" / "reviewer_prompt.txt"
    assert prompt_file.exists()
    assert "task-codex-001" in prompt_file.read_text(encoding="utf-8")


def test_codex_agent_adapter_runs_coder_command_and_writes_prompt(tmp_path: Path):
    script = tmp_path / "coder.py"
    reviewer_script = tmp_path / "reviewer_ok.py"
    marker = tmp_path / "coder_marker.txt"
    script.write_text(
        "\n".join(
            [
                "import pathlib, sys",
                "prompt = pathlib.Path(sys.argv[1])",
                "marker = pathlib.Path(sys.argv[2])",
                "text = prompt.read_text(encoding='utf-8')",
                "assert 'Coder agent' in text",
                "assert 'task-codex-001' in text",
                "marker.write_text(text, encoding='utf-8')",
            ]
        ),
        encoding="utf-8",
    )
    reviewer_script.write_text(
        "\n".join(
            [
                "import json",
                "print(json.dumps({'schema_version':'1.0','task_id':'task-codex-001','pass':True,'confidence':90,'summary':'ok','issues':[],'blocking':False,'recommended_next_action':'pass'}))",
            ]
        ),
        encoding="utf-8",
    )
    task_path = write_task(
        tmp_path,
        reviewer_command=f"\"{sys.executable}\" \"{reviewer_script}\"",
        coder_command=f"\"{sys.executable}\" \"{script}\" {{prompt_file}} \"{marker}\"",
    )

    state = build_use_case(tmp_path / "runs", CodexAgent()).execute(RunTaskCommand(task_path=task_path))

    assert state.status == RunStatus.DONE
    assert marker.exists()
    assert "Apply the smallest safe code change" in marker.read_text(encoding="utf-8")


def test_codex_agent_adapter_runs_fixer_command_with_reason_file(tmp_path: Path):
    script = tmp_path / "fixer.py"
    marker = tmp_path / "fixer_marker.txt"
    script.write_text(
        "\n".join(
            [
                "import json, pathlib, sys",
                "prompt = pathlib.Path(sys.argv[1])",
                "reason = pathlib.Path(sys.argv[2])",
                "marker = pathlib.Path(sys.argv[3])",
                "assert 'Fixer agent' in prompt.read_text(encoding='utf-8')",
                "payload = json.loads(reason.read_text(encoding='utf-8'))",
                "marker.write_text(payload['commands'][0]['name'], encoding='utf-8')",
            ]
        ),
        encoding="utf-8",
    )
    state = RunState(
        run_id="run-fixer",
        task_id="task-codex-001",
        attempt=1,
        max_attempts=2,
        artifacts={"run_dir": str(tmp_path / "runs" / "run-fixer")},
    )
    task = TaskLoader().load(
        write_task(
            tmp_path,
            reviewer_command=f"\"{sys.executable}\" -c \"print('{{}}')\"",
            fixer_command=f"\"{sys.executable}\" \"{script}\" {{prompt_file}} {{reason_file}} \"{marker}\"",
        )
    )
    reason = HardCheckResult(
        commands=[
            CheckCommandResult(
                name="pytest",
                passed=False,
                command="python -m pytest",
                stdout="failed",
            )
        ],
    )

    CodexAgent().run_fixer(task, state, reason)

    assert marker.read_text(encoding="utf-8") == "pytest"
    reason_file = tmp_path / "runs" / "run-fixer" / "attempts" / "001" / "fix_reason.json"
    assert reason_file.exists()


def test_codex_agent_adapter_nonzero_exit_halts_run(tmp_path: Path):
    task_path = write_task(
        tmp_path,
        reviewer_command=f"\"{sys.executable}\" -c \"import sys; sys.exit(7)\"",
    )

    state = build_use_case(tmp_path / "runs", CodexAgent()).execute(RunTaskCommand(task_path=task_path))

    assert state.status == RunStatus.HALTED
    agent_log = tmp_path / "runs" / state.run_id / "logs" / "agent.log"
    assert "exit_code=7" in agent_log.read_text(encoding="utf-8")


def test_omx_agent_adapter_uses_adapter_name_in_log(tmp_path: Path):
    script = tmp_path / "reviewer.py"
    script.write_text(
        "import json, sys; print(json.dumps({'schema_version':'1.0','task_id':sys.argv[1],'pass':True,'confidence':90,'summary':'ok','issues':[],'blocking':False,'recommended_next_action':'pass'}))",
        encoding="utf-8",
    )
    task_path = write_task(tmp_path, f"\"{sys.executable}\" \"{script}\" {{task_id}}", AgentMode.OMX)

    state = build_use_case(tmp_path / "runs", OmxAgent()).execute(RunTaskCommand(task_path=task_path))

    assert state.status == RunStatus.DONE
    agent_log = tmp_path / "runs" / state.run_id / "logs" / "agent.log"
    assert "adapter=omx" in agent_log.read_text(encoding="utf-8")
