from __future__ import annotations

from pydantic import BaseModel

from orchestrator.domain.enums import ChangeType, Decision


class QualityReport(BaseModel):
    task_id: str
    attempt: int
    change_type: ChangeType
    hard_check_score: int
    review_schema_valid: bool = True
    review_json_retry_count: int = 0
    review_pass: bool = False
    review_confidence: int = 0
    review_score: int = 0
    diff_risk_score: int = 0
    quality_score: int = 0
    passed: bool = False
    decision: Decision
    reason: str
