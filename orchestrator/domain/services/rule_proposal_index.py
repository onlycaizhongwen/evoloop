from __future__ import annotations

from datetime import datetime
from hashlib import sha1

from pydantic import BaseModel, Field

from orchestrator.domain.models.rule_proposal import RuleProposal


class RuleProposalCluster(BaseModel):
    cluster_key: str
    source: str
    reason: str
    observed_count: int = 0
    first_seen_at: datetime = Field(default_factory=datetime.now)
    last_seen_at: datetime = Field(default_factory=datetime.now)
    first_seen_run_id: str
    last_seen_run_id: str
    run_ids: list[str] = Field(default_factory=list)
    task_ids: list[str] = Field(default_factory=list)
    review_status: str = "pending"
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None
    review_note: str | None = None


class RuleProposalIndex(BaseModel):
    schema_version: str = "1.0"
    clusters: dict[str, RuleProposalCluster] = Field(default_factory=dict)


class RuleProposalIndexService:
    VALID_REVIEW_STATUSES = {"pending", "approved", "rejected"}

    def update(self, index: RuleProposalIndex, proposal: RuleProposal) -> RuleProposalCluster:
        cluster_key = self.cluster_key(proposal.source, proposal.reason)
        now = datetime.now()
        cluster = index.clusters.get(cluster_key)
        if cluster is None:
            cluster = RuleProposalCluster(
                cluster_key=cluster_key,
                source=proposal.source,
                reason=proposal.reason,
                first_seen_at=now,
                last_seen_at=now,
                first_seen_run_id=proposal.run_id,
                last_seen_run_id=proposal.run_id,
                run_ids=[],
                task_ids=[],
            )
            index.clusters[cluster_key] = cluster

        cluster.observed_count += 1
        cluster.last_seen_at = now
        cluster.last_seen_run_id = proposal.run_id
        if proposal.run_id not in cluster.run_ids:
            cluster.run_ids.append(proposal.run_id)
        if proposal.task_id not in cluster.task_ids:
            cluster.task_ids.append(proposal.task_id)

        proposal.cluster_key = cluster.cluster_key
        proposal.observed_count = cluster.observed_count
        proposal.first_seen_run_id = cluster.first_seen_run_id
        proposal.last_seen_run_id = cluster.last_seen_run_id
        return cluster

    def cluster_key(self, source: str, reason: str) -> str:
        normalized = f"{source.strip().lower()}::{reason.strip().lower()}"
        digest = sha1(normalized.encode("utf-8")).hexdigest()[:12]
        return f"rpc-{digest}"

    def review_cluster(
        self,
        index: RuleProposalIndex,
        cluster_key: str,
        status: str,
        reviewer: str | None = None,
        note: str | None = None,
    ) -> RuleProposalCluster:
        if status not in self.VALID_REVIEW_STATUSES:
            allowed = ", ".join(sorted(self.VALID_REVIEW_STATUSES))
            raise ValueError(f"invalid review status: {status}; allowed={allowed}")
        cluster = index.clusters.get(cluster_key)
        if cluster is None:
            raise KeyError(f"rule proposal cluster not found: {cluster_key}")
        cluster.review_status = status
        cluster.reviewed_by = reviewer
        cluster.reviewed_at = datetime.now()
        cluster.review_note = note
        return cluster
