from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class RuleProposal(BaseModel):
    proposal_id: str = "RP-001"
    task_id: str
    run_id: str
    source: str
    reason: str
    suggested_rule: str
    scope: str
    evidence: list[str] = Field(default_factory=list)
    review_status: str = "pending"
    created_at: datetime = Field(default_factory=datetime.now)
    cluster_key: str | None = None
    observed_count: int = 1
    first_seen_run_id: str | None = None
    last_seen_run_id: str | None = None
