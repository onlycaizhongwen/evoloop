from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any


class SQLiteJobRepository:
    def __init__(self, db_path: Path | str = Path(".omx/orchestrator.db")) -> None:
        self.db_path = Path(db_path)

    def create(self, payload: dict[str, Any]) -> None:
        now = datetime.now().isoformat()
        values = {
            "job_id": str(payload["job_id"]),
            "status": str(payload.get("status", "running")),
            "message": str(payload.get("message", "")),
            "task_path": str(payload.get("task_path", "")),
            "run_id": str(payload.get("run_id", "")),
            "started_at": str(payload.get("started_at", now)),
            "finished_at": str(payload.get("finished_at", "")),
            "updated_at": str(payload.get("updated_at", now)),
        }
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO web_jobs (
                    job_id, status, message, task_path, run_id, started_at, finished_at, updated_at
                )
                VALUES (
                    :job_id, :status, :message, :task_path, :run_id, :started_at, :finished_at, :updated_at
                )
                ON CONFLICT(job_id) DO UPDATE SET
                    status=excluded.status,
                    message=excluded.message,
                    task_path=excluded.task_path,
                    run_id=excluded.run_id,
                    started_at=excluded.started_at,
                    finished_at=excluded.finished_at,
                    updated_at=excluded.updated_at
                """,
                values,
            )

    def update(self, job_id: str, **updates: Any) -> None:
        existing = self.get(job_id) or {"job_id": job_id, "started_at": datetime.now().isoformat()}
        existing.update(updates)
        existing["updated_at"] = str(updates.get("updated_at", datetime.now().isoformat()))
        self.create(existing)

    def get(self, job_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT job_id, status, message, task_path, run_id, started_at, finished_at, updated_at
                FROM web_jobs
                WHERE job_id = ?
                """,
                (job_id,),
            ).fetchone()
        return dict(row) if row else None

    def list_recent(self, limit: int = 20) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT job_id, status, message, task_path, run_id, started_at, finished_at, updated_at
                FROM web_jobs
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def list_page(self, *, limit: int = 20, offset: int = 0, status: str | None = None) -> list[dict[str, Any]]:
        query = """
            SELECT job_id, status, message, task_path, run_id, started_at, finished_at, updated_at
            FROM web_jobs
        """
        params: list[Any] = []
        if status:
            query += " WHERE status = ?"
            params.append(status)
        query += " ORDER BY updated_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        with self._connect() as connection:
            rows = connection.execute(query, params).fetchall()
        return [dict(row) for row in rows]

    def list_before(self, *, updated_before: str, statuses: list[str], limit: int = 500) -> list[dict[str, Any]]:
        if not statuses:
            return []
        placeholders = ", ".join("?" for _ in statuses)
        query = f"""
            SELECT job_id, status, message, task_path, run_id, started_at, finished_at, updated_at
            FROM web_jobs
            WHERE updated_at < ? AND status IN ({placeholders})
            ORDER BY updated_at ASC
            LIMIT ?
        """
        params: list[Any] = [updated_before, *statuses, limit]
        with self._connect() as connection:
            rows = connection.execute(query, params).fetchall()
        return [dict(row) for row in rows]

    def list_by_run_ids(self, run_ids: list[str]) -> list[dict[str, Any]]:
        if not run_ids:
            return []
        placeholders = ", ".join("?" for _ in run_ids)
        query = f"""
            SELECT job_id, status, message, task_path, run_id, started_at, finished_at, updated_at
            FROM web_jobs
            WHERE run_id IN ({placeholders})
            ORDER BY updated_at DESC
        """
        with self._connect() as connection:
            rows = connection.execute(query, run_ids).fetchall()
        return [dict(row) for row in rows]

    def count(self, status: str | None = None) -> int:
        query = "SELECT COUNT(*) FROM web_jobs"
        params: list[Any] = []
        if status:
            query += " WHERE status = ?"
            params.append(status)
        with self._connect() as connection:
            row = connection.execute(query, params).fetchone()
        return int(row[0]) if row else 0

    def counts_by_status(self) -> dict[str, int]:
        counts = {"all": self.count(), "running": 0, "done": 0, "failed": 0, "stopped": 0}
        with self._connect() as connection:
            rows = connection.execute("SELECT status, COUNT(*) AS total FROM web_jobs GROUP BY status").fetchall()
        for row in rows:
            status = str(row["status"])
            if status in counts:
                counts[status] = int(row["total"])
        return counts

    def delete(self, job_id: str) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM web_jobs WHERE job_id = ?", (job_id,))

    def _connect(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS web_jobs (
                job_id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                message TEXT NOT NULL DEFAULT '',
                task_path TEXT NOT NULL DEFAULT '',
                run_id TEXT NOT NULL DEFAULT '',
                started_at TEXT NOT NULL DEFAULT '',
                finished_at TEXT NOT NULL DEFAULT '',
                updated_at TEXT NOT NULL DEFAULT ''
            )
            """
        )
        return connection
