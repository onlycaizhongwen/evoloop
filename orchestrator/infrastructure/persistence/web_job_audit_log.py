from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class WebJobAuditEvent:
    event_type: str
    selected_job_ids: list[str] = field(default_factory=list)
    processed_job_ids: list[str] = field(default_factory=list)
    skipped_job_ids: list[str] = field(default_factory=list)
    failed_job_ids: list[str] = field(default_factory=list)
    run_ids: list[str] = field(default_factory=list)
    message: str = ""
    actor: str = "web"
    request_context: dict[str, Any] = field(default_factory=dict)
    details: dict[str, Any] = field(default_factory=dict)
    event_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_record(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "created_at": self.created_at,
            "actor": self.actor,
            "request_context": self.request_context,
            "selected_job_ids": self.selected_job_ids,
            "processed_job_ids": self.processed_job_ids,
            "skipped_job_ids": self.skipped_job_ids,
            "failed_job_ids": self.failed_job_ids,
            "run_ids": self.run_ids,
            "message": self.message,
            "details": self.details,
        }


class WebJobAuditLog:
    def __init__(
        self,
        path: Path | str = Path(".omx/web-job-audit.jsonl"),
        *,
        max_bytes: int | None = 5 * 1024 * 1024,
        archive_count: int = 5,
    ) -> None:
        self.path = Path(path)
        self.max_bytes = max_bytes
        self.archive_count = max(0, archive_count)

    def append(self, event: WebJobAuditEvent) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._rotate_if_needed()
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event.to_record(), ensure_ascii=False, sort_keys=True))
            handle.write("\n")

    def list_recent(self, limit: int = 50) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        records: list[dict[str, Any]] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(record, dict):
                records.append(record)
        return records[-limit:][::-1]

    def _rotate_if_needed(self) -> None:
        if self.max_bytes is None or self.max_bytes <= 0:
            return
        if not self.path.exists() or self.path.stat().st_size < self.max_bytes:
            return
        self.path.replace(self._archive_path())
        self._prune_archives()

    def _archive_path(self) -> Path:
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
        return self.path.with_name(f"{self.path.stem}.{timestamp}{self.path.suffix}")

    def _prune_archives(self) -> None:
        if self.archive_count <= 0:
            for archive_path in self._archive_paths():
                archive_path.unlink()
            return
        for archive_path in self._archive_paths()[self.archive_count :]:
            archive_path.unlink()

    def _archive_paths(self) -> list[Path]:
        pattern = f"{self.path.stem}.*{self.path.suffix}"
        return sorted(self.path.parent.glob(pattern), reverse=True)
