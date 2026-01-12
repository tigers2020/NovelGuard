"""SQLite 데이터베이스 스키마 정의."""

# runs 테이블 생성
CREATE_TABLE_RUNS = """
CREATE TABLE IF NOT EXISTS runs (
    run_id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    root_path TEXT NOT NULL,
    options_json TEXT NOT NULL,
    total_files INTEGER NOT NULL DEFAULT 0,
    total_bytes INTEGER NOT NULL DEFAULT 0,
    elapsed_ms INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'running',
    error_message TEXT
)
"""

# files 테이블 생성 (UNIQUE 제약 포함)
CREATE_TABLE_FILES = """
CREATE TABLE IF NOT EXISTS files (
    file_id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL,
    path TEXT NOT NULL,
    size INTEGER NOT NULL,
    mtime TEXT NOT NULL,
    ext TEXT NOT NULL,
    is_hidden INTEGER NOT NULL DEFAULT 0,
    is_symlink INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (run_id) REFERENCES runs(run_id) ON DELETE CASCADE,
    UNIQUE(run_id, path)
)
"""

# 인덱스 생성
CREATE_INDEX_RUN_EXT = """
CREATE INDEX IF NOT EXISTS idx_files_run_ext ON files(run_id, ext)
"""

CREATE_INDEX_RUN_SIZE = """
CREATE INDEX IF NOT EXISTS idx_files_run_size ON files(run_id, size)
"""

CREATE_INDEX_RUN_PATH = """
CREATE INDEX IF NOT EXISTS idx_files_run_path ON files(run_id, path)
"""

# Upsert 정책: INSERT ... ON CONFLICT DO UPDATE
# 이 SQL은 sqlite_index_repository.py에서 동적으로 생성하여 사용
# 예시:
# INSERT INTO files (run_id, path, size, mtime, ext, is_hidden, is_symlink)
# VALUES (?, ?, ?, ?, ?, ?, ?)
# ON CONFLICT(run_id, path) DO UPDATE SET
#     size = excluded.size,
#     mtime = excluded.mtime,
#     ext = excluded.ext,
#     is_hidden = excluded.is_hidden,
#     is_symlink = excluded.is_symlink
