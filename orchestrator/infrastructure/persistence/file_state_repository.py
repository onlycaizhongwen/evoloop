from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from orchestrator.domain.models.check_result import HardCheckResult
from orchestrator.domain.models.quality_report import QualityReport
from orchestrator.domain.models.review import ReviewResult
from orchestrator.domain.models.rule_proposal import RuleProposal
from orchestrator.domain.models.run_state import RunState
from orchestrator.domain.models.task import TaskConfig
from orchestrator.domain.services.rule_proposal_index import RuleProposalIndex, RuleProposalIndexService


class FileStateRepository:
    def __init__(self, base_dir: Path | str = ".omx/runs"):
        self.base_dir = Path(base_dir)
        self.rule_proposal_index_service = RuleProposalIndexService()

    def create_run(self, task: TaskConfig) -> RunState:
        run_id = datetime.now().strftime("run-%Y%m%d-%H%M%S-%f")
        run_dir = self.base_dir / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "attempts").mkdir(exist_ok=True)
        state = RunState(
            run_id=run_id,
            task_id=task.task_id,
            max_attempts=task.max_attempts,
            artifacts={
                "run_dir": str(run_dir),
                "task": str(run_dir / "task.json"),
                "run_state": str(run_dir / "run_state.json"),
                "logs": str(run_dir / "logs"),
            },
        )
        (run_dir / "logs").mkdir(exist_ok=True)
        self._write_json(run_dir / "task.json", task.model_dump(mode="json"))
        self.save_state(state)
        return state

    def load_state(self, run_id: str) -> RunState:
        run_dir = self.base_dir / run_id
        payload = json.loads((run_dir / "run_state.json").read_text(encoding="utf-8"))
        return RunState.model_validate(payload)

    def task_path_for_run(self, run_id: str) -> Path:
        return self.base_dir / run_id / "task.json"

    def load_rule_proposal_index(self) -> RuleProposalIndex:
        return self._load_rule_proposal_index()

    def review_rule_proposal_cluster(
        self,
        cluster_key: str,
        status: str,
        reviewer: str | None = None,
        note: str | None = None,
    ):
        index = self._load_rule_proposal_index()
        cluster = self.rule_proposal_index_service.review_cluster(index, cluster_key, status, reviewer, note)
        self._write_rule_proposal_index(index)
        return cluster

    def save_state(self, state: RunState) -> None:
        self._write_json(self._run_dir(state) / "run_state.json", state.model_dump(mode="json"))

    def save_hard_check(self, state: RunState, result: HardCheckResult) -> None:
        attempt_dir = self._attempt_dir(state)
        self._write_json(attempt_dir / "hard_checks.json", result.model_dump(mode="json"))
        self.save_state(state)

    def save_review(self, state: RunState, review: ReviewResult) -> None:
        attempt_dir = self._attempt_dir(state)
        self._write_json(attempt_dir / "review.json", review.model_dump(mode="json", by_alias=True))
        self.save_state(state)

    def save_quality_report(self, state: RunState, report: QualityReport) -> None:
        attempt_dir = self._attempt_dir(state)
        self._write_json(attempt_dir / "quality_report.json", report.model_dump(mode="json"))
        self.save_state(state)

    def save_malformed_review(self, state: RunState, retry_count: int, raw_output: str) -> None:
        attempt_dir = self._attempt_dir(state)
        (attempt_dir / f"malformed_review_{retry_count}.txt").write_text(raw_output, encoding="utf-8")

    def write_final_report(self, state: RunState, content: str) -> None:
        (self._run_dir(state) / "final_report.md").write_text(content, encoding="utf-8")
        self.save_state(state)

    def write_rule_proposal(self, state: RunState, proposal: RuleProposal, content: str) -> None:
        index = self._load_rule_proposal_index()
        self.rule_proposal_index_service.update(index, proposal)
        self._write_rule_proposal_index(index)
        content = content if proposal.cluster_key is None else self._render_indexed_content(proposal, content)
        pending_dir = self._run_dir(state) / "pending-rules"
        pending_dir.mkdir(exist_ok=True)
        path = pending_dir / f"{proposal.proposal_id}.md"
        path.write_text(content, encoding="utf-8")
        state.artifacts["rule_proposal"] = str(path)
        state.artifacts["rule_proposal_index"] = str(self._rule_proposal_index_path())
        self.save_state(state)

    def _run_dir(self, state: RunState) -> Path:
        return Path(state.artifacts["run_dir"])

    def _attempt_dir(self, state: RunState) -> Path:
        attempt_dir = self._run_dir(state) / "attempts" / f"{state.attempt:03d}"
        attempt_dir.mkdir(parents=True, exist_ok=True)
        return attempt_dir

    def _write_json(self, path: Path, payload: dict) -> None:
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def _rule_proposal_index_path(self) -> Path:
        return self.base_dir / "rule_proposals_index.json"

    def _load_rule_proposal_index(self) -> RuleProposalIndex:
        path = self._rule_proposal_index_path()
        if not path.exists():
            return RuleProposalIndex()
        payload = json.loads(path.read_text(encoding="utf-8"))
        return RuleProposalIndex.model_validate(payload)

    def _write_rule_proposal_index(self, index: RuleProposalIndex) -> None:
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._write_json(self._rule_proposal_index_path(), index.model_dump(mode="json"))

    def _render_indexed_content(self, proposal: RuleProposal, content: str) -> str:
        lines = content.splitlines()
        rendered = []
        inserted = False
        for line in lines:
            rendered.append(line)
            if line.startswith("- source:") and not inserted:
                rendered.extend(
                    [
                        f"- cluster_key: `{proposal.cluster_key}`",
                        f"- observed_count: `{proposal.observed_count}`",
                        f"- first_seen_run_id: `{proposal.first_seen_run_id}`",
                        f"- last_seen_run_id: `{proposal.last_seen_run_id}`",
                    ]
                )
                inserted = True
        return "\n".join(rendered) + "\n"
