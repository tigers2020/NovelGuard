"""Local perf smoke for queryFileRows (PR-29, non-blocking CI).

Usage:
  PYTHONPATH=src python scripts/perf_file_rows_query.py [--db PATH] [--folder PATH] [--count 10000]
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path


def main() -> int:
    from application.file_row_query import FileRowFilters, NormalizedFileRowsQuery
    from domain.models import FileRecord, make_file_id
    from infrastructure.sqlite_file_rows_page import query_sqlite_file_rows_page
    from infrastructure.sqlite_library_index import SqliteLibraryIndex

    parser = argparse.ArgumentParser(description="Perf smoke for SQLite query_file_rows_page")
    parser.add_argument("--db", type=Path, default=Path("perf_library.db"))
    parser.add_argument("--folder", type=Path, default=Path("perf_lib"))
    parser.add_argument("--count", type=int, default=10_000)
    args = parser.parse_args()

    folder = str(args.folder.resolve())
    index = SqliteLibraryIndex(args.db)
    files = [
        FileRecord(
            id=make_file_id(f"file_{i}.txt", 10, i),
            relative_path=f"batch/file_{i}.txt",
            name=f"file_{i}.txt",
            size_bytes=10,
            modified_at_ns=i,
            extension=".txt",
            content_sha256=f"{i:064x}",
            encoding_status="utf-8",
        )
        for i in range(args.count)
    ]
    index.replace_files(folder, files)

    empty_filters = FileRowFilters()

    def _query(
        *,
        search_term: str | None = None,
        sort_field: str = "path",
    ) -> NormalizedFileRowsQuery:
        return NormalizedFileRowsQuery(
            search_term=search_term,
            sort_field=sort_field,
            sort_direction="asc",
            filters=empty_filters,
            cursor_offset=0,
            limit=100,
            wire_cursor=None,
            preset=None,
        )

    scenarios = [
        ("initial_page", _query()),
        ("search", _query(search_term="file_9")),
        ("name_sort", _query(sort_field="name")),
    ]

    print(f"files={args.count} folder={folder} db={args.db}")
    for label, normalized in scenarios:
        samples: list[float] = []
        with index._connect() as conn:
            for _ in range(5):
                start = time.perf_counter()
                query_sqlite_file_rows_page(conn, folder, normalized)
                samples.append((time.perf_counter() - start) * 1000)
        ordered = sorted(samples)
        p95_index = max(0, int(len(ordered) * 0.95) - 1)
        p95 = ordered[p95_index]
        print(f"  {label}: p95={p95:.1f}ms samples={[round(s, 1) for s in samples]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
