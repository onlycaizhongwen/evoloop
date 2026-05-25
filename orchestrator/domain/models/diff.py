from __future__ import annotations

from pydantic import BaseModel


class DiffStats(BaseModel):
    changed_files: int = 0
    total_changed_lines: int = 0
    max_file_changed_lines: int = 0
    deleted_files: int = 0
    only_tests_changed: bool = False
    source_changed_without_tests: bool = False
    touches_forbidden_path: bool = False
