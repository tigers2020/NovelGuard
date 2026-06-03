"""SQLite job queue for automation workers."""

from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class JobRecord:
    row_id: int
    payload: dict[str, Any]


class JobQueue:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT NOT NULL UNIQUE,
                    status TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    started_at REAL,
                    finished_at REAL,
                    result TEXT,
                    log_path TEXT
                )
                """)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_jobs_status_created ON jobs(status, created_at)"
            )
            conn.commit()

    def enqueue(self, payload: dict[str, Any]) -> str:
        job_id = str(payload["id"])
        now = time.time()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO jobs (job_id, status, payload, created_at)
                VALUES (?, 'queued', ?, ?)
                """,
                (job_id, json.dumps(payload, ensure_ascii=False), now),
            )
            conn.commit()
        return job_id

    def claim_next(self) -> JobRecord | None:
        with self._connect() as conn:
            row = conn.execute("""
                SELECT id, payload FROM jobs
                WHERE status = 'queued'
                ORDER BY created_at ASC
                LIMIT 1
                """).fetchone()
            if row is None:
                return None
            now = time.time()
            updated = conn.execute(
                """
                UPDATE jobs SET status = 'running', started_at = ?
                WHERE id = ? AND status = 'queued'
                """,
                (now, row["id"]),
            )
            conn.commit()
            if updated.rowcount != 1:
                return None
        payload = json.loads(row["payload"])
        return JobRecord(row_id=int(row["id"]), payload=payload)

    def complete(
        self,
        row_id: int,
        *,
        status: str,
        result: dict[str, Any],
        log_path: str | None = None,
    ) -> None:
        now = time.time()
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE jobs
                SET status = ?, finished_at = ?, result = ?, log_path = ?
                WHERE id = ?
                """,
                (
                    status,
                    now,
                    json.dumps(result, ensure_ascii=False),
                    log_path,
                    row_id,
                ),
            )
            conn.commit()
