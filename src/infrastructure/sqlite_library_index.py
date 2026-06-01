"""SQLite-backed LibraryIndexPort."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from domain.models import FileRecord

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
