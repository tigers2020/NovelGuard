"""SQLite-backed LibraryIndexPort."""

from __future__ import annotations

import json
import logging
import sqlite3
import time
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from application.dto_mapper import empty_file_rows_page
from application.file_row_query import NormalizedFileRowsQuery, text_sort_key
from application.library_folder_persistence import normalize_library_folder_path
from application.ports.review_state import LoadedReviewState
from domain.duplicate_near import (
    NearDuplicateGroup,
    NearDuplicatePair,
    NearDuplicateResult,
    NearDuplicateStats,
)
from domain.models import FileRecord
from domain.quality import QualityIssue
from infrastructure.sqlite_file_rows_page import query_sqlite_file_rows_page

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
  encoding_status TEXT,
  name_key TEXT NOT NULL DEFAULT '',
  relative_path_key TEXT NOT NULL DEFAULT '',
  extension_key TEXT NOT NULL DEFAULT '',
  encoding_key TEXT NOT NULL DEFAULT ''
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
CREATE TABLE IF NOT EXISTS near_duplicate_groups (
  folder_path TEXT NOT NULL,
  group_id TEXT NOT NULL,
  near_batch_id TEXT NOT NULL,
  algorithm_version TEXT NOT NULL,
  threshold REAL NOT NULL,
  member_count INTEGER NOT NULL,
  max_similarity REAL NOT NULL,
  created_at TEXT NOT NULL,
  PRIMARY KEY (folder_path, group_id)
);
CREATE TABLE IF NOT EXISTS near_duplicate_group_members (
  folder_path TEXT NOT NULL,
  group_id TEXT NOT NULL,
  file_id TEXT NOT NULL,
  normalized_length INTEGER NOT NULL,
  fingerprint_count INTEGER NOT NULL,
  PRIMARY KEY (folder_path, group_id, file_id)
);
CREATE TABLE IF NOT EXISTS near_duplicate_pairs (
  folder_path TEXT NOT NULL,
  group_id TEXT NOT NULL,
  left_file_id TEXT NOT NULL,
  right_file_id TEXT NOT NULL,
  similarity_score REAL NOT NULL,
  shared_fingerprint_count INTEGER NOT NULL,
  left_fingerprint_count INTEGER NOT NULL,
  right_fingerprint_count INTEGER NOT NULL,
  PRIMARY KEY (folder_path, group_id, left_file_id, right_file_id)
);
CREATE INDEX IF NOT EXISTS idx_near_groups_folder ON near_duplicate_groups(folder_path);
"""

_FILE_KEY_MIGRATION_COLUMNS = (
    "name_key",
    "relative_path_key",
    "extension_key",
    "encoding_key",
)


def _table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return {str(row[1]) for row in rows}


def _file_sort_keys(record: FileRecord) -> tuple[str, str, str, str]:
    return (
        text_sort_key(record.name),
        text_sort_key(record.relative_path),
        text_sort_key(record.extension),
        text_sort_key(record.encoding_status or ""),
    )


def _backfill_file_keys(conn: sqlite3.Connection) -> None:
    rows = conn.execute("""
        SELECT folder_path, id, name, relative_path, extension, encoding_status
        FROM files
        """).fetchall()
    for folder_path, file_id, name, relative_path, extension, encoding_status in rows:
        conn.execute(
            """
            UPDATE files
            SET name_key = ?,
                relative_path_key = ?,
                extension_key = ?,
                encoding_key = ?
            WHERE folder_path = ? AND id = ?
            """,
            (
                text_sort_key(str(name)),
                text_sort_key(str(relative_path)),
                text_sort_key(str(extension)),
                text_sort_key(str(encoding_status or "")),
                folder_path,
                file_id,
            ),
        )


def _migrate_schema(conn: sqlite3.Connection) -> None:
    file_columns = _table_columns(conn, "files")
    if not file_columns:
        return
    for column in _FILE_KEY_MIGRATION_COLUMNS:
        if column not in file_columns:
            conn.execute(f"ALTER TABLE files ADD COLUMN {column} TEXT NOT NULL DEFAULT ''")
    _backfill_file_keys(conn)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS file_review_projection (
          folder_path TEXT NOT NULL,
          file_id TEXT NOT NULL,
          duplicate_group_id TEXT,
          is_keeper INTEGER NOT NULL DEFAULT 0,
          duplicate_group_key TEXT,
          PRIMARY KEY (folder_path, file_id)
        );
        CREATE INDEX IF NOT EXISTS idx_file_review_folder_group_key_id
          ON file_review_projection(folder_path, duplicate_group_key, file_id);
        CREATE INDEX IF NOT EXISTS idx_files_folder_path_id
          ON files(folder_path, relative_path_key, id);
        CREATE INDEX IF NOT EXISTS idx_files_folder_name_id
          ON files(folder_path, name_key, id);
        CREATE INDEX IF NOT EXISTS idx_files_folder_extension_id
          ON files(folder_path, extension_key, id);
        CREATE INDEX IF NOT EXISTS idx_files_folder_size_id
          ON files(folder_path, size_bytes, id);
        CREATE INDEX IF NOT EXISTS idx_files_folder_modified_id
          ON files(folder_path, modified_at_ns, id);
        CREATE INDEX IF NOT EXISTS idx_files_folder_encoding_id
          ON files(folder_path, encoding_key, id);
        """)


class SqliteLibraryIndex:
    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._current_folder: str | None = None
        db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(_SCHEMA)
            _migrate_schema(conn)
            conn.commit()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA busy_timeout=5000")
        return conn

    def _storage_folder_path(self, folder_path: str) -> str:
        return normalize_library_folder_path(folder_path)

    def clear(self) -> None:
        self._current_folder = None
        with self._connect() as conn:
            conn.execute("DELETE FROM files")
            conn.execute("DELETE FROM quality_issues")
            conn.execute("DELETE FROM review_group_state")
            conn.execute("DELETE FROM review_member_state")
            conn.execute("DELETE FROM near_duplicate_groups")
            conn.execute("DELETE FROM near_duplicate_group_members")
            conn.execute("DELETE FROM near_duplicate_pairs")
            conn.execute("DELETE FROM file_review_projection")

    def activate_library_folder(self, folder_path: str) -> None:
        self._current_folder = self._storage_folder_path(folder_path)

    def replace_files(
        self,
        folder_path: str,
        files: list[FileRecord],
        *,
        on_save_progress: Callable[[int, int], None] | None = None,
    ) -> None:
        folder_path = self._storage_folder_path(folder_path)
        self._current_folder = folder_path
        total = len(files)
        insert_sql = """
                INSERT INTO files (
                  id, folder_path, relative_path, name, size_bytes, modified_at_ns,
                  extension, content_sha256, encoding_status,
                  name_key, relative_path_key, extension_key, encoding_key
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
        batch_size = 800
        with self._connect() as conn:
            conn.execute("DELETE FROM files WHERE folder_path = ?", (folder_path,))
            conn.commit()
            saved = 0
            for offset in range(0, total, batch_size):
                chunk = files[offset : offset + batch_size]
                conn.executemany(
                    insert_sql,
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
                            *_file_sort_keys(f),
                        )
                        for f in chunk
                    ],
                )
                conn.commit()
                saved += len(chunk)
                if on_save_progress is not None:
                    on_save_progress(saved, total)

    def append_files_batch(
        self,
        folder_path: str,
        files: list[FileRecord],
        *,
        reset: bool = False,
    ) -> None:
        if not files and not reset:
            return
        folder_path = self._storage_folder_path(folder_path)
        self._current_folder = folder_path
        insert_sql = """
                INSERT INTO files (
                  id, folder_path, relative_path, name, size_bytes, modified_at_ns,
                  extension, content_sha256, encoding_status,
                  name_key, relative_path_key, extension_key, encoding_key
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
        with self._connect() as conn:
            if reset:
                conn.execute(
                    "DELETE FROM files WHERE folder_path = ?",
                    (folder_path,),
                )
            if files:
                conn.executemany(
                    insert_sql,
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
                            *_file_sort_keys(f),
                        )
                        for f in files
                    ],
                )
            conn.commit()

    def replace_file_review_projection(
        self,
        folder_path: str,
        rows: list[tuple[str, str | None, bool, str | None]],
    ) -> None:
        """Replace 1:1 review enrichment rows for folder (file_id, group_id, is_keeper, group_key)."""
        with self._connect() as conn:
            conn.execute(
                "DELETE FROM file_review_projection WHERE folder_path = ?",
                (folder_path,),
            )
            if not rows:
                return
            conn.executemany(
                """
                INSERT INTO file_review_projection (
                  folder_path, file_id, duplicate_group_id, is_keeper, duplicate_group_key
                ) VALUES (?, ?, ?, ?, ?)
                """,
                [
                    (
                        folder_path,
                        file_id,
                        duplicate_group_id,
                        1 if is_keeper else 0,
                        duplicate_group_key,
                    )
                    for file_id, duplicate_group_id, is_keeper, duplicate_group_key in rows
                ],
            )

    def query_file_rows_page(self, normalized: NormalizedFileRowsQuery) -> dict[str, Any]:
        if self._current_folder is None:
            return empty_file_rows_page(normalized.wire_cursor)
        t0 = time.perf_counter()
        with self._connect() as conn:
            page = query_sqlite_file_rows_page(conn, self._current_folder, normalized)
        elapsed_ms = int((time.perf_counter() - t0) * 1000)
        logging.getLogger(__name__).debug(
            "%s",
            json.dumps(
                {
                    "event": "sqlite_query",
                    "query_type": "file_rows_page",
                    "query_ms": elapsed_ms,
                    "row_count": len(page.get("rows", [])),
                    "limit": normalized.limit,
                    "offset": normalized.cursor_offset,
                }
            ),
        )
        return page

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
        if self._current_folder is None:
            return 0
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) FROM files WHERE folder_path = ?",
                (self._current_folder,),
            ).fetchone()
        return int(row[0]) if row else 0

    def total_bytes(self) -> int:
        if self._current_folder is None:
            return 0
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COALESCE(SUM(size_bytes), 0) FROM files WHERE folder_path = ?",
                (self._current_folder,),
            ).fetchone()
        return int(row[0]) if row else 0

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

    def replace_near_duplicate_results(self, folder_path: str, result: NearDuplicateResult) -> None:
        created_at = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            conn.execute("DELETE FROM near_duplicate_pairs WHERE folder_path = ?", (folder_path,))
            conn.execute(
                "DELETE FROM near_duplicate_group_members WHERE folder_path = ?",
                (folder_path,),
            )
            conn.execute("DELETE FROM near_duplicate_groups WHERE folder_path = ?", (folder_path,))
            for group in result.groups:
                conn.execute(
                    """
                    INSERT INTO near_duplicate_groups (
                      folder_path, group_id, near_batch_id, algorithm_version, threshold,
                      member_count, max_similarity, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        folder_path,
                        group.group_id,
                        result.near_batch_id,
                        result.algorithm_version,
                        result.threshold,
                        len(group.member_file_ids),
                        group.max_similarity,
                        created_at,
                    ),
                )
                for file_id in group.member_file_ids:
                    conn.execute(
                        """
                        INSERT INTO near_duplicate_group_members (
                          folder_path, group_id, file_id, normalized_length, fingerprint_count
                        ) VALUES (?, ?, ?, ?, ?)
                        """,
                        (folder_path, group.group_id, file_id, 0, 0),
                    )
                for pair in group.pairs:
                    conn.execute(
                        """
                        INSERT INTO near_duplicate_pairs (
                          folder_path, group_id, left_file_id, right_file_id,
                          similarity_score, shared_fingerprint_count,
                          left_fingerprint_count, right_fingerprint_count
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            folder_path,
                            group.group_id,
                            pair.left_file_id,
                            pair.right_file_id,
                            pair.similarity_score,
                            pair.shared_fingerprint_count,
                            pair.left_fingerprint_count,
                            pair.right_fingerprint_count,
                        ),
                    )

    def load_near_duplicate_result(self, folder_path: str) -> NearDuplicateResult | None:
        with self._connect() as conn:
            group_rows = conn.execute(
                """
                SELECT group_id, near_batch_id, algorithm_version, threshold,
                       member_count, max_similarity
                FROM near_duplicate_groups
                WHERE folder_path = ?
                ORDER BY group_id
                """,
                (folder_path,),
            ).fetchall()
            if not group_rows:
                return None

            near_batch_id = str(group_rows[0][1])
            algorithm_version = str(group_rows[0][2])
            threshold = float(group_rows[0][3])

            groups: list[NearDuplicateGroup] = []
            for row in group_rows:
                group_id = str(row[0])
                pair_rows = conn.execute(
                    """
                    SELECT left_file_id, right_file_id, similarity_score,
                           shared_fingerprint_count, left_fingerprint_count,
                           right_fingerprint_count
                    FROM near_duplicate_pairs
                    WHERE folder_path = ? AND group_id = ?
                    """,
                    (folder_path, group_id),
                ).fetchall()
                member_rows = conn.execute(
                    """
                    SELECT file_id FROM near_duplicate_group_members
                    WHERE folder_path = ? AND group_id = ?
                    ORDER BY file_id
                    """,
                    (folder_path, group_id),
                ).fetchall()
                pairs = tuple(
                    NearDuplicatePair(
                        left_file_id=str(pair_row[0]),
                        right_file_id=str(pair_row[1]),
                        similarity_score=float(pair_row[2]),
                        shared_fingerprint_count=int(pair_row[3]),
                        left_fingerprint_count=int(pair_row[4]),
                        right_fingerprint_count=int(pair_row[5]),
                    )
                    for pair_row in pair_rows
                )
                groups.append(
                    NearDuplicateGroup(
                        group_id=group_id,
                        member_file_ids=tuple(str(member_row[0]) for member_row in member_rows),
                        pairs=pairs,
                        max_similarity=float(row[5]),
                    )
                )

        return NearDuplicateResult(
            near_batch_id=near_batch_id,
            algorithm_version=algorithm_version,
            threshold=threshold,
            groups=tuple(groups),
            stats=NearDuplicateStats(
                eligible_file_count=0,
                skipped_file_count=0,
                bucket_count=0,
                candidate_pair_count=0,
                accepted_pair_count=0,
                group_count=len(groups),
            ),
        )

    def clear_near_duplicate_results(self, folder_path: str) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM near_duplicate_pairs WHERE folder_path = ?", (folder_path,))
            conn.execute(
                "DELETE FROM near_duplicate_group_members WHERE folder_path = ?",
                (folder_path,),
            )
            conn.execute("DELETE FROM near_duplicate_groups WHERE folder_path = ?", (folder_path,))
