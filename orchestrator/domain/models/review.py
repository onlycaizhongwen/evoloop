from __future__ import annotations

from pydantic import BaseModel, Field

from orchestrator.domain.enums import Severity


class ReviewIssue(BaseModel):
    id: str
    severity: Severity
    category: str
    file: str | None = None
    line: int | None = None
    message: str
    suggestion: str | None = None


class ReviewResult(BaseModel):
    schema_version: str = "1.0"
    task_id: str
    pass_: bool = Field(alias="pass")
    confidence: int = Field(ge=0, le=100)
    summary: str
    issues: list[ReviewIssue] = Field(default_factory=list)
    blocking: bool = False
    recommended_next_action: str = "pass"

    @property
    def has_critical_issue(self) -> bool:
        return any(issue.severity == Severity.CRITICAL for issue in self.issues)
