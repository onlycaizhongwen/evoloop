from __future__ import annotations

import json
from pathlib import Path

import pytest

from orchestrator.infrastructure.persistence.web_job_audit_log import WebJobAuditEvent, WebJobAuditLog


def test_web_job_audit_log_appends_and_lists_recent(tmp_path: Path):
    log = WebJobAuditLog(tmp_path / "web-job-audit.jsonl")

    log.append(WebJobAuditEvent(event_type="first", processed_job_ids=["job-1"]))
    log.append(WebJobAuditEvent(event_type="second", processed_job_ids=["job-2"]))

    records = log.list_recent(limit=1)

    assert len(records) == 1
    assert records[0]["event_type"] == "second"
    assert records[0]["processed_job_ids"] == ["job-2"]


def test_web_job_audit_log_ignores_corrupt_lines(tmp_path: Path):
    path = tmp_path / "web-job-audit.jsonl"
    path.write_text(
        "\n".join(
            [
                "{not json",
                json.dumps({"event_type": "valid", "processed_job_ids": ["job-valid"]}),
                "[]",
            ]
        ),
        encoding="utf-8",
    )

    records = WebJobAuditLog(path).list_recent()

    assert records == [{"event_type": "valid", "processed_job_ids": ["job-valid"]}]


def test_web_job_audit_log_rotates_before_appending_new_event(tmp_path: Path):
    path = tmp_path / "web-job-audit.jsonl"
    old_event = WebJobAuditEvent(event_type="old", processed_job_ids=["job-old"])
    path.write_text(json.dumps(old_event.to_record(), ensure_ascii=False) + "\n", encoding="utf-8")
    log = WebJobAuditLog(path, max_bytes=1, archive_count=2)

    log.append(WebJobAuditEvent(event_type="new", processed_job_ids=["job-new"]))

    active_records = log.list_recent()
    archives = sorted(tmp_path.glob("web-job-audit.*.jsonl"))

    assert [record["event_type"] for record in active_records] == ["new"]
    assert len(archives) == 1
    assert json.loads(archives[0].read_text(encoding="utf-8").splitlines()[0])["event_type"] == "old"


def test_web_job_audit_log_prunes_old_archives(tmp_path: Path):
    path = tmp_path / "web-job-audit.jsonl"
    log = WebJobAuditLog(path, max_bytes=1, archive_count=1)

    for index in range(3):
        path.write_text("x" * 10, encoding="utf-8")
        log.append(WebJobAuditEvent(event_type=f"event-{index}"))

    archives = sorted(tmp_path.glob("web-job-audit.*.jsonl"))

    assert len(archives) == 1


def test_web_job_audit_log_surfaces_rotation_failures(tmp_path: Path, monkeypatch):
    path = tmp_path / "web-job-audit.jsonl"
    path.write_text("x" * 10, encoding="utf-8")
    log = WebJobAuditLog(path, max_bytes=1)

    def fail_replace(self, target):
        raise OSError("cannot rotate audit log")

    monkeypatch.setattr(Path, "replace", fail_replace)

    with pytest.raises(OSError, match="cannot rotate audit log"):
        log.append(WebJobAuditEvent(event_type="new"))
