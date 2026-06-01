"""SQLite-backed LibraryIndexPort."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

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
