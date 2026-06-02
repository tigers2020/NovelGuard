"""SQLite-backed LibraryIndexPort."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from application.ports.review_state import LoadedReviewState
from domain.models import FileRecord
from domain.quality import QualityIssue

_SCHEMA = """
CREATE TABLE IF NOT EXISTS files (
  id TEXT PRIMARY KEY,
  folder_path TEXT NOT NULL,
  relative_path TEXT NOT NULL,
  name TEXT NOT NULL,
  size_bytes INTEGER NOT NULL,
  modified_at_ns INTEGER NOT NULL,
  extension TEXT NOT NULL,
  content_sha256 TEXT,
  encoding_status TEXT
);
CREATE INDEX IF NOT EXISTS idx_files_folder ON files(folder_path);
CREATE TABLE IF NOT EXISTS quality_issues (
  folder_path TEXT NOT NULL,
  issue_id TEXT NOT NULL,
  file_id TEXT NOT NULL,
  path TEXT NOT NULL,
  severity TEXT NOT NULL,
  kind TEXT NOT NULL,
  message TEXT NOT NULL,
  evidence_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  PRIMARY KEY (folder_path, issue_id)
);
CREATE INDEX IF NOT EXISTS idx_quality_issues_folder ON quality_issues(folder_path);
CREATE TABLE IF NOT EXISTS review_group_state (
  folder_path TEXT NOT NULL,
  group_id TEXT NOT NULL,
  keeper_file_id TEXT,
  group_status TEXT,
  updated_at TEXT NOT NULL,
  PRIMARY KEY (folder_path, group_id)
);
CREATE TABLE IF NOT EXISTS review_member_state (
  folder_path TEXT NOT NULL,
  file_id TEXT NOT NULL,
  member_status TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  PRIMARY KEY (folder_path, file_id)
);
CREATE INDEX IF NOT EXISTS idx_review_group_folder ON review_group_state(folder_path);
CREATE INDEX IF NOT EXISTS idx_review_member_folder ON review_member_state(folder_path);
"""


class SqliteLibraryIndex:
    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._current_folder: str | None = None
        db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(_SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def clear(self) -> None:
        self._current_folder = None
        with self._connect() as conn:
            conn.execute("DELETE FROM files")
            conn.execute("DELETE FROM quality_issues")
            conn.execute("DELETE FROM review_group_state")
            conn.execute("DELETE FROM review_member_state")

    def replace_files(self, folder_path: str, files: list[FileRecord]) -> None:
        self._current_folder = folder_path
        with self._connect() as conn:
            conn.execute("DELETE FROM files WHERE folder_path = ?", (folder_path,))
            conn.executemany(
                """
                INSERT INTO files (
                  id, folder_path, relative_path, name, size_bytes, modified_at_ns,
                  extension, content_sha256, encoding_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        f.id,
                        folder_path,
                        f.relative_path,
                        f.name,
                        f.size_bytes,
                        f.modified_at_ns,
                        f.extension,
                        f.content_sha256,
                        f.encoding_status,
                    )
                    for f in files
                ],
            )

    @property
    def folder_path(self) -> str | None:
        return self._current_folder

    def files(self) -> list[FileRecord]:
        if self._current_folder is None:
            return []
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, relative_path, name, size_bytes, modified_at_ns, extension,
                       content_sha256, encoding_status
                FROM files WHERE folder_path = ?
                ORDER BY relative_path
                """,
                (self._current_folder,),
            ).fetchall()
        return [
            FileRecord(
                id=row[0],
                relative_path=row[1],
                name=row[2],
                size_bytes=row[3],
                modified_at_ns=row[4],
                extension=row[5],
                content_sha256=row[6],
                encoding_status=row[7],
            )
            for row in rows
        ]

    def file_count(self) -> int:
        return len(self.files())

    def total_bytes(self) -> int:
        return sum(f.size_bytes for f in self.files())

    def replace_quality_issues(self, folder_path: str, issues: list[QualityIssue]) -> None:
        created_at = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            conn.execute("DELETE FROM quality_issues WHERE folder_path = ?", (folder_path,))
            conn.executemany(
                """
                INSERT INTO quality_issues (
                  folder_path, issue_id, file_id, path, severity, kind, message,
                  evidence_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        folder_path,
                        issue.issue_id,
                        issue.file_id,
                        issue.path,
                        issue.severity,
                        issue.kind,
                        issue.message,
                        json.dumps(issue.evidence),
                        created_at,
                    )
                    for issue in issues
                ],
            )

    def quality_issues(self) -> list[QualityIssue]:
        if self._current_folder is None:
            return []
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT issue_id, file_id, path, severity, kind, message, evidence_json
                FROM quality_issues
                WHERE folder_path = ?
                ORDER BY path, kind
                """,
                (self._current_folder,),
            ).fetchall()
        return [
            QualityIssue(
                issue_id=row[0],
                file_id=row[1],
                path=row[2],
                severity=row[3],  # type: ignore[arg-type]
                kind=row[4],  # type: ignore[arg-type]
                message=row[5],
                evidence=json.loads(row[6]),
            )
            for row in rows
        ]

    def load_review_state(self, folder_path: str) -> LoadedReviewState:
        with self._connect() as conn:
            group_rows = conn.execute(
                """
                SELECT group_id, keeper_file_id, group_status
                FROM review_group_state WHERE folder_path = ?
                """,
                (folder_path,),
            ).fetchall()
            member_rows = conn.execute(
                """
                SELECT file_id, member_status
                FROM review_member_state WHERE folder_path = ?
                """,
                (folder_path,),
            ).fetchall()
        groups = {row[0]: (row[1], row[2]) for row in group_rows}
        members = {row[0]: row[1] for row in member_rows}
        return LoadedReviewState(groups=groups, members=members)

    def upsert_review_group(
        self,
        folder_path: str,
        group_id: str,
        *,
        keeper_file_id: str | None = None,
        group_status: str | None = None,
        clear_keeper: bool = False,
        clear_status: bool = False,
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT keeper_file_id, group_status
                FROM review_group_state
                WHERE folder_path = ? AND group_id = ?
                """,
                (folder_path, group_id),
            ).fetchone()
            prev_keeper = row[0] if row else None
            prev_status = row[1] if row else None
            new_keeper = (
                None
                if clear_keeper
                else (keeper_file_id if keeper_file_id is not None else prev_keeper)
            )
            new_status = (
                None
                if clear_status
                else (group_status if group_status is not None else prev_status)
            )
            conn.execute(
                """
                INSERT INTO review_group_state (
                  folder_path, group_id, keeper_file_id, group_status, updated_at
                ) VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(folder_path, group_id) DO UPDATE SET
                  keeper_file_id = excluded.keeper_file_id,
                  group_status = excluded.group_status,
                  updated_at = excluded.updated_at
                """,
                (folder_path, group_id, new_keeper, new_status, now),
            )

    def delete_review_group(self, folder_path: str, group_id: str) -> bool:
        with self._connect() as conn:
            cursor = conn.execute(
                "DELETE FROM review_group_state WHERE folder_path = ? AND group_id = ?",
                (folder_path, group_id),
            )
            return cursor.rowcount > 0

    def upsert_review_member(self, folder_path: str, file_id: str, member_status: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO review_member_state (
                  folder_path, file_id, member_status, updated_at
                ) VALUES (?, ?, ?, ?)
                ON CONFLICT(folder_path, file_id) DO UPDATE SET
                  member_status = excluded.member_status,
                  updated_at = excluded.updated_at
                """,
                (folder_path, file_id, member_status, now),
            )

    def delete_review_member(self, folder_path: str, file_id: str) -> bool:
        with self._connect() as conn:
            cursor = conn.execute(
                "DELETE FROM review_member_state WHERE folder_path = ? AND file_id = ?",
                (folder_path, file_id),
            )
            return cursor.rowcount > 0

    def clear_review_state(self, folder_path: str) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM review_group_state WHERE folder_path = ?", (folder_path,))
            conn.execute("DELETE FROM review_member_state WHERE folder_path = ?", (folder_path,))

    def prune_review_state(
        self,
        folder_path: str,
        valid_group_ids: set[str],
        valid_file_ids: set[str],
    ) -> None:
        with self._connect() as conn:
            if valid_group_ids:
                placeholders = ",".join("?" for _ in valid_group_ids)
                conn.execute(
                    f"""
                    DELETE FROM review_group_state
                    WHERE folder_path = ? AND group_id NOT IN ({placeholders})
                    """,
                    (folder_path, *valid_group_ids),
                )
            else:
                conn.execute(
                    "DELETE FROM review_group_state WHERE folder_path = ?",
                    (folder_path,),
                )
            if valid_file_ids:
                placeholders = ",".join("?" for _ in valid_file_ids)
                conn.execute(
                    f"""
                    DELETE FROM review_member_state
                    WHERE folder_path = ? AND file_id NOT IN ({placeholders})
                    """,
                    (folder_path, *valid_file_ids),
                )
            else:
                conn.execute(
                    "DELETE FROM review_member_state WHERE folder_path = ?",
                    (folder_path,),
                )
