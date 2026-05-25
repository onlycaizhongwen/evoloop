from __future__ import annotations

import json
from pathlib import Path

from orchestrator.application.dto.run_task_command import RunTaskCommand
from orchestrator.application.use_cases.run_task import RunTaskUseCase
from orchestrator.config.task_loader import TaskLoader
from orchestrator.domain.enums import RunStatus
from orchestrator.domain.services.quality_gate import QualityGate
from orchestrator.domain.services.review_validator import ReviewValidator
from orchestrator.domain.services.safety_policy import SafetyPolicy
from orchestrator.infrastructure.agents.mock_agent import MockAgent
from orchestrator.infrastructure.checks.fake_check_runner import FakeCheckRunner
from orchestrator.infrastructure.git.static_diff_provider import StaticDiffProvider
from orchestrator.infrastructure.persistence.file_state_repository import FileStateRepository
from orchestrator.report.final_report_writer import FinalReportWriter


def build_use_case(base_dir: Path, pass_checks: bool = True, agent: MockAgent | None = None) -> RunTaskUseCase:
    return RunTaskUseCase(
        task_loader=TaskLoader(),
        safety_policy=SafetyPolicy(),
        state_repository=FileStateRepository(base_dir),
        agent=agent or MockAgent(),
        check_runner=FakeCheckRunner(pass_all=pass_checks),
        review_validator=ReviewValidator(),
        quality_gate=QualityGate(),
        diff_provider=StaticDiffProvider(),
        final_report_writer=FinalReportWriter(),
    )


def test_mock_loop_done(tmp_path: Path):
    use_case = build_use_case(tmp_path)
    state = use_case.execute(RunTaskCommand(task_path=Path("examples/task.mock.json")))
    assert state.status == RunStatus.DONE
    assert (tmp_path / state.run_id / "final_report.md").exists()
    assert not (tmp_path / state.run_id / "pending-rules").exists()
    phase_log = (tmp_path / state.run_id / "logs" / "phase.log").read_text(encoding="utf-8")
    assert "phase=code" in phase_log
    assert "phase=hard_checks" in phase_log
    assert "phase=review" in phase_log
    assert "phase=quality_gate" in phase_log
    assert "phase=done" in phase_log


def test_hard_check_failure_short_circuits_reviewer(tmp_path: Path):
    agent = MockAgent()
    use_case = build_use_case(tmp_path, pass_checks=False, agent=agent)
    state = use_case.execute(RunTaskCommand(task_path=Path("examples/task.mock.json")))
    assert state.status == RunStatus.HALTED
    assert agent.reviewer_calls == 0
    proposal = tmp_path / state.run_id / "pending-rules" / "RP-001.md"
    assert proposal.exists()
    content = proposal.read_text(encoding="utf-8")
    assert "hard_check_failure" in content
    assert "test failed" in content
    assert "cluster_key" in content
    index = json.loads((tmp_path / "rule_proposals_index.json").read_text(encoding="utf-8"))
    clusters = list(index["clusters"].values())
    assert len(clusters) == 1
    assert clusters[0]["source"] == "hard_check_failure"
    assert clusters[0]["observed_count"] == 1
    phase_log = (tmp_path / state.run_id / "logs" / "phase.log").read_text(encoding="utf-8")
    assert "phase=hard_checks" in phase_log
    assert "event=halt" in phase_log


def test_malformed_review_final_failure_generates_rule_proposal(tmp_path: Path):
    agent = MockAgent(reviewer_outputs=["not json", "still not json", "``` nope ```"])
    use_case = build_use_case(tmp_path, agent=agent)
    state = use_case.execute(RunTaskCommand(task_path=Path("examples/task.mock.json")))

    assert state.status == RunStatus.HALTED
    attempt_dir = tmp_path / state.run_id / "attempts" / "001"
    assert (attempt_dir / "malformed_review_1.txt").read_text(encoding="utf-8") == "not json"
    assert (attempt_dir / "malformed_review_3.txt").read_text(encoding="utf-8") == "``` nope ```"

    proposal = tmp_path / state.run_id / "pending-rules" / "RP-001.md"
    assert proposal.exists()
    content = proposal.read_text(encoding="utf-8")
    assert "malformed_review_json" in content
    assert "raw outputs saved" in content
    phase_log = (tmp_path / state.run_id / "logs" / "phase.log").read_text(encoding="utf-8")
    assert "phase=review" in phase_log
    assert "event=retry" in phase_log


def test_repeated_rule_proposals_are_clustered(tmp_path: Path):
    first = build_use_case(tmp_path, pass_checks=False).execute(RunTaskCommand(task_path=Path("examples/task.mock.json")))
    second = build_use_case(tmp_path, pass_checks=False).execute(RunTaskCommand(task_path=Path("examples/task.mock.json")))

    index = json.loads((tmp_path / "rule_proposals_index.json").read_text(encoding="utf-8"))
    clusters = list(index["clusters"].values())

    assert len(clusters) == 1
    assert clusters[0]["observed_count"] == 2
    assert first.run_id in clusters[0]["run_ids"]
    assert second.run_id in clusters[0]["run_ids"]

    second_proposal = tmp_path / second.run_id / "pending-rules" / "RP-001.md"
    content = second_proposal.read_text(encoding="utf-8")
    assert "observed_count: `2`" in content
