"""SQLite job queue for automation workers."""

from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from automation.runners.worker_lock import clear_lock, lock_holder_alive


@dataclass(frozen=True)
class JobRecord:
    row_id: int
    payload: dict[str, Any]


class JobQueue:
    _TERMINAL = frozenset({"succeeded", "failed"})
    _DEFAULT_STALE_SECONDS = 3600.0

    def __init__(self, db_path: Path, *, stale_seconds: float | None = None) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._stale_seconds = (
            float(stale_seconds) if stale_seconds is not None else self._DEFAULT_STALE_SECONDS
        )
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
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
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_jobs_status_created ON jobs(status, created_at)"
            )
            conn.commit()

    def stats(self) -> dict[str, int]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT status, COUNT(*) AS c FROM jobs GROUP BY status"
            ).fetchall()
        out = {"queued": 0, "running": 0, "succeeded": 0, "failed": 0}
        for row in rows:
            key = str(row["status"])
            if key in out:
                out[key] = int(row["c"])
        return out

    def _is_stale_running(self, conn: sqlite3.Connection, row_id: int) -> bool:
        row = conn.execute(
            "SELECT started_at FROM jobs WHERE id = ? AND status = 'running'",
            (row_id,),
        ).fetchone()
        if row is None or row["started_at"] is None:
            return True
        return (time.time() - float(row["started_at"])) > self._stale_seconds

    def _requeue_running(self, conn: sqlite3.Connection, row_id: int) -> None:
        conn.execute(
            """
            UPDATE jobs
            SET status = 'queued', started_at = NULL
            WHERE id = ? AND status = 'running'
            """,
            (row_id,),
        )

    def enqueue(self, payload: dict[str, Any]) -> str:
        """Insert job. Re-queue when the same job_id previously failed."""
        job_id = str(payload["id"])
        now = time.time()
        payload_json = json.dumps(payload, ensure_ascii=False)
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id, status FROM jobs WHERE job_id = ? ORDER BY id DESC LIMIT 1",
                (job_id,),
            ).fetchone()
            if row is not None:
                status = str(row["status"])
                row_id = int(row["id"])
                if status == "running":
                    if self._is_stale_running(conn, row_id):
                        self._requeue_running(conn, row_id)
                        conn.commit()
                    else:
                        raise RuntimeError(f"Job already active: {job_id}")
                elif status == "queued":
                    raise RuntimeError(f"Job already active: {job_id}")
                elif status == "succeeded":
                    raise RuntimeError(f"Job already succeeded: {job_id}")
                elif status == "failed":
                    conn.execute(
                        """
                        UPDATE jobs
                        SET status = 'queued', payload = ?, created_at = ?,
                            started_at = NULL, finished_at = NULL, result = NULL, log_path = NULL
                        WHERE id = ?
                        """,
                        (payload_json, now, row_id),
                    )
                    conn.commit()
                    return job_id

            conn.execute(
                """
                INSERT INTO jobs (job_id, status, payload, created_at)
                VALUES (?, 'queued', ?, ?)
                """,
                (job_id, payload_json, now),
            )
            conn.commit()
        return job_id

    def claim_next(self) -> JobRecord | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT id, payload FROM jobs
                WHERE status = 'queued'
                ORDER BY created_at ASC
                LIMIT 1
                """
            ).fetchone()
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

    def release_stale_running(
        self,
        *,
        stale_seconds: float,
        job_id: str | None = None,
        force: bool = False,
    ) -> list[str]:
        released: list[str] = []
        now = time.time()
        with self._connect() as conn:
            query = "SELECT id, job_id, started_at FROM jobs WHERE status = 'running'"
            params: list[Any] = []
            if job_id:
                query += " AND job_id = ?"
                params.append(job_id)
            rows = conn.execute(query, params).fetchall()
            for row in rows:
                row_id = int(row["id"])
                jid = str(row["job_id"])
                started = row["started_at"]
                age = now - float(started or 0)
                if force or age >= stale_seconds:
                    if force:
                        conn.execute(
                            """
                            UPDATE jobs
                            SET status = 'failed', finished_at = ?,
                                result = ?
                            WHERE id = ? AND status = 'running'
                            """,
                            (
                                now,
                                json.dumps(
                                    {"status": "failed", "error": "released by admin"},
                                    ensure_ascii=False,
                                ),
                                row_id,
                            ),
                        )
                    else:
                        self._requeue_running(conn, row_id)
                    released.append(jid)
            conn.commit()
        return released

    def recover_orphaned_running(self, locks_dir: Path) -> list[str]:
        """Re-queue running jobs when worker lock is absent or stale."""
        alive, _ = lock_holder_alive(locks_dir)
        if alive:
            return []
        released = self.release_stale_running(stale_seconds=0)
        if released:
            clear_lock(locks_dir)
        return released

    def reset_job(self, job_id: str) -> bool:
        with self._connect() as conn:
            cur = conn.execute("DELETE FROM jobs WHERE job_id = ?", (job_id,))
            conn.commit()
            return cur.rowcount > 0

    def requeue_row(self, row_id: int) -> None:
        with self._connect() as conn:
            self._requeue_running(conn, row_id)
            conn.commit()
