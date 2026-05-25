from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field


class ReplaceTextOperation(BaseModel):
    op: Literal["replace_text"]
    path: str = Field(min_length=1)
    old: str
    new: str


class CreateFileOperation(BaseModel):
    op: Literal["create_file"]
    path: str = Field(min_length=1)
    content: str = ""
    overwrite: bool = False


class DeleteFileOperation(BaseModel):
    op: Literal["delete_file"]
    path: str = Field(min_length=1)
    must_exist: bool = True


class UnifiedDiffOperation(BaseModel):
    op: Literal["unified_diff"]
    path: str = Field(min_length=1)
    diff: str = Field(min_length=1)


PatchOperation = Annotated[
    ReplaceTextOperation | CreateFileOperation | DeleteFileOperation | UnifiedDiffOperation,
    Field(discriminator="op"),
]


class PatchPlan(BaseModel):
    schema_version: str = "1.0"
    task_id: str = Field(min_length=1)
    summary: str = ""
    operations: list[PatchOperation] = Field(default_factory=list)


class PatchApplyResult(BaseModel):
    changed_files: list[str] = Field(default_factory=list)
    created_files: list[str] = Field(default_factory=list)
    deleted_files: list[str] = Field(default_factory=list)
    risk_score: int = 10
    risk_reasons: list[str] = Field(default_factory=list)
