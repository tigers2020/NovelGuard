"""SQLite 인덱스 저장소 구현."""
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

from application.dto.run_summary import RunSummary
from application.dto.scan_request import ScanRequest
from application.dto.ext_stat import ExtStat
from application.ports.index_repository import IIndexRepository
from application.ports.log_sink import ILogSink
from application.utils.debug_logger import debug_step
from domain.entities.file_entry import FileEntry

from infrastructure.db.paths import get_index_db_path
from infrastructure.db.schema import (
    CREATE_TABLE_RUNS,
    CREATE_TABLE_FILES,
    CREATE_INDEX_RUN_EXT,
    CREATE_INDEX_RUN_SIZE,
    CREATE_INDEX_RUN_PATH,
)


class SQLiteIndexRepository:
    """SQLite 기반 인덱스 저장소 - IIndexRepository 구현."""
    
    # order_by 화이트리스트 (SQL injection 방지)
    ALLOWED_ORDER_BY = {
        "path": "path ASC",
        "size_desc": "size DESC",
        "mtime_desc": "mtime DESC",
    }
    
    # 배치 삽입 청크 크기
    CHUNK_SIZE = 2000
    
    def __init__(self, db_path: Optional[Path] = None, log_sink: Optional[ILogSink] = None) -> None:
        """인덱스 저장소 초기화.
        
        Args:
            db_path: DB 파일 경로. None이면 기본 경로 사용.
            log_sink: 로그 싱크 (선택적).
        """
        self._db_path = db_path or get_index_db_path()
        self._log_sink = log_sink
        self._ensure_schema()
    
    def _ensure_schema(self) -> None:
        """스키마가 없으면 생성."""
        conn = self._connect()
        try:
            # executescript는 세미콜론으로 구분된 여러 SQL 문을 실행
            schema_sql = (
                CREATE_TABLE_RUNS + ";\n" +
                CREATE_TABLE_FILES + ";\n" +
                CREATE_INDEX_RUN_EXT + ";\n" +
                CREATE_INDEX_RUN_SIZE + ";\n" +
                CREATE_INDEX_RUN_PATH + ";\n"
            )
            conn.executescript(schema_sql)
            conn.commit()
        finally:
            conn.close()
    
    def _connect(self) -> sqlite3.Connection:
        """DB 커넥션 생성 (메서드 호출마다 새 커넥션).
        
        Returns:
            SQLite 커넥션.
        """
        return sqlite3.connect(str(self._db_path))
    
    def start_run(self, request: ScanRequest) -> int:
        """Run 시작.
        
        Args:
            request: 스캔 요청 DTO.
        
        Returns:
            생성된 run_id.
        """
        debug_step(
            self._log_sink,
            "start_run",
            {
                "root_folder": str(request.root_folder),
                "extensions": request.extensions,
                "include_subdirs": request.include_subdirs,
                "include_hidden": request.include_hidden,
                "include_symlinks": request.include_symlinks,
                "incremental": request.incremental,
            }
        )
        
        conn = self._connect()
        try:
            cursor = conn.cursor()
            options_json = json.dumps({
                "extensions": request.extensions,
                "include_subdirs": request.include_subdirs,
                "include_hidden": request.include_hidden,
                "include_symlinks": request.include_symlinks,
                "incremental": request.incremental,
            })
            cursor.execute(
                "INSERT INTO runs (started_at, root_path, options_json, status) VALUES (?, ?, ?, ?)",
                (
                    datetime.now().isoformat(),
                    str(request.root_folder.as_posix()),
                    options_json,
                    "running",
                )
            )
            conn.commit()
            run_id = cursor.lastrowid
            
            debug_step(
                self._log_sink,
                "start_run_complete",
                {"run_id": run_id}
            )
            
            return run_id
        finally:
            conn.close()
    
    def upsert_files(self, run_id: int, entries: list[FileEntry]) -> None:
        """파일 배치 저장 (upsert).
        
        Args:
            run_id: Run ID.
            entries: 파일 엔트리 리스트.
        """
        if not entries:
            return
        
        debug_step(
            self._log_sink,
            "upsert_files_start",
            {
                "run_id": run_id,
                "total_entries": len(entries),
                "chunk_size": self.CHUNK_SIZE,
                "expected_chunks": (len(entries) + self.CHUNK_SIZE - 1) // self.CHUNK_SIZE,
            }
        )
        
        # 청크 단위로 처리
        chunk_count = 0
        for chunk_start in range(0, len(entries), self.CHUNK_SIZE):
            chunk = entries[chunk_start:chunk_start + self.CHUNK_SIZE]
            self._upsert_files_chunk(run_id, chunk)
            chunk_count += 1
            
            # 청크 완료 로그 (매 5개 청크마다)
            if chunk_count % 5 == 0:
                debug_step(
                    self._log_sink,
                    "upsert_files_progress",
                    {
                        "run_id": run_id,
                        "chunks_processed": chunk_count,
                        "entries_processed": min(chunk_start + self.CHUNK_SIZE, len(entries)),
                        "total_entries": len(entries),
                    }
                )
        
        debug_step(
            self._log_sink,
            "upsert_files_complete",
            {
                "run_id": run_id,
                "total_entries": len(entries),
                "chunks_processed": chunk_count,
            }
        )
    
    def _upsert_files_chunk(self, run_id: int, entries: list[FileEntry]) -> None:
        """파일 청크 저장 (내부 메서드).
        
        Args:
            run_id: Run ID.
            entries: 파일 엔트리 리스트 (청크).
        """
        conn = self._connect()
        try:
            # Upsert SQL: ON CONFLICT DO UPDATE
            sql = """
            INSERT INTO files (run_id, path, size, mtime, ext, is_hidden, is_symlink)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(run_id, path) DO UPDATE SET
                size = excluded.size,
                mtime = excluded.mtime,
                ext = excluded.ext,
                is_hidden = excluded.is_hidden,
                is_symlink = excluded.is_symlink
            """
            
            values = [
                (
                    run_id,
                    entry.path.as_posix(),  # 절대 경로, POSIX 형식
                    entry.size,
                    entry.mtime.isoformat(),  # ISO format
                    entry.extension,
                    1 if entry.is_hidden else 0,  # INTEGER (0/1)
                    1 if entry.is_symlink else 0,  # INTEGER (0/1)
                )
                for entry in entries
            ]
            
            with conn:  # 트랜잭션
                conn.executemany(sql, values)
        finally:
            conn.close()
    
    def finalize_run(self, run_id: int, summary: RunSummary) -> None:
        """Run 완료 처리.
        
        Args:
            run_id: Run ID.
            summary: Run 요약 정보.
        """
        debug_step(
            self._log_sink,
            "finalize_run",
            {
                "run_id": run_id,
                "total_files": summary.total_files,
                "total_bytes": summary.total_bytes,
                "elapsed_ms": summary.elapsed_ms,
                "status": summary.status,
                "error_message": summary.error_message,
            }
        )
        
        conn = self._connect()
        try:
            finished_at = summary.finished_at.isoformat() if summary.finished_at else None
            cursor = conn.cursor()
            cursor.execute(
                """UPDATE runs
                   SET finished_at = ?, total_files = ?, total_bytes = ?, elapsed_ms = ?, status = ?, error_message = ?
                   WHERE run_id = ?""",
                (
                    finished_at,
                    summary.total_files,
                    summary.total_bytes,
                    summary.elapsed_ms,
                    summary.status,
                    summary.error_message,
                    run_id,
                )
            )
            conn.commit()
            
            debug_step(
                self._log_sink,
                "finalize_run_complete",
                {"run_id": run_id}
            )
        finally:
            conn.close()
    
    def get_latest_run_id(self) -> Optional[int]:
        """최신 Run ID 반환.
        
        Returns:
            최신 Run ID. 없으면 None.
        """
        debug_step(self._log_sink, "get_latest_run_id_start")
        
        conn = self._connect()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT run_id FROM runs ORDER BY run_id DESC LIMIT 1")
            row = cursor.fetchone()
            result = row[0] if row else None
            
            debug_step(
                self._log_sink,
                "get_latest_run_id_complete",
                {"run_id": result}
            )
            
            return result
        finally:
            conn.close()
    
    def get_run_summary(self, run_id: int) -> Optional[RunSummary]:
        """Run 요약 정보 조회.
        
        Args:
            run_id: Run ID.
        
        Returns:
            Run 요약 정보. 없으면 None.
        """
        debug_step(
            self._log_sink,
            "get_run_summary_start",
            {"run_id": run_id}
        )
        
        conn = self._connect()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT started_at, finished_at, root_path, options_json, total_files, total_bytes, elapsed_ms, status, error_message FROM runs WHERE run_id = ?",
                (run_id,)
            )
            row = cursor.fetchone()
            if not row:
                debug_step(self._log_sink, "get_run_summary_not_found", {"run_id": run_id})
                return None
            
            started_at, finished_at, root_path, options_json, total_files, total_bytes, elapsed_ms, status, error_message = row
            
            result = RunSummary(
                run_id=run_id,
                started_at=datetime.fromisoformat(started_at),
                finished_at=datetime.fromisoformat(finished_at) if finished_at else None,
                root_path=Path(root_path),
                options_json=options_json,
                total_files=total_files,
                total_bytes=total_bytes,
                elapsed_ms=elapsed_ms,
                status=status,
                error_message=error_message,
            )
            
            debug_step(
                self._log_sink,
                "get_run_summary_complete",
                {
                    "run_id": run_id,
                    "total_files": total_files,
                    "status": status,
                }
            )
            
            return result
        finally:
            conn.close()
    
    def get_ext_distribution(self, run_id: int) -> list[ExtStat]:
        """확장자별 분포 집계.
        
        Args:
            run_id: Run ID.
        
        Returns:
            확장자별 통계 리스트.
        """
        debug_step(
            self._log_sink,
            "get_ext_distribution_start",
            {"run_id": run_id}
        )
        
        conn = self._connect()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT ext, COUNT(*) as count, SUM(size) as total_bytes
                   FROM files
                   WHERE run_id = ?
                   GROUP BY ext
                   ORDER BY count DESC""",
                (run_id,)
            )
            rows = cursor.fetchall()
            result = [
                ExtStat(ext=ext, count=count, total_bytes=total_bytes)
                for ext, count, total_bytes in rows
            ]
            
            debug_step(
                self._log_sink,
                "get_ext_distribution_complete",
                {
                    "run_id": run_id,
                    "ext_count": len(result),
                }
            )
            
            return result
        finally:
            conn.close()
    
    def list_files(
        self,
        run_id: int,
        offset: int = 0,
        limit: int = 200,
        ext: Optional[str] = None,
        min_size: Optional[int] = None,
        max_size: Optional[int] = None,
        order_by: str = "path"
    ) -> list[FileEntry]:
        """파일 목록 조회 (페이지네이션).
        
        Args:
            run_id: Run ID.
            offset: 시작 오프셋 (기본값: 0).
            limit: 최대 개수 (기본값: 200).
            ext: 확장자 필터 (선택적).
            min_size: 최소 크기 필터 (선택적, 바이트).
            max_size: 최대 크기 필터 (선택적, 바이트).
            order_by: 정렬 기준 (기본값: "path", 허용: "path", "size_desc", "mtime_desc").
        
        Returns:
            파일 엔트리 리스트.
        """
        debug_step(
            self._log_sink,
            "list_files_start",
            {
                "run_id": run_id,
                "offset": offset,
                "limit": limit,
                "ext": ext,
                "order_by": order_by,
            }
        )
        
        # order_by 화이트리스트 검증 (SQL injection 방지)
        if order_by not in self.ALLOWED_ORDER_BY:
            raise ValueError(f"Invalid order_by: {order_by}. Allowed: {list(self.ALLOWED_ORDER_BY.keys())}")
        
        order_by_sql = self.ALLOWED_ORDER_BY[order_by]
        
        conn = self._connect()
        try:
            # WHERE 조건 구축
            conditions = ["run_id = ?"]
            params = [run_id]
            
            if ext is not None:
                conditions.append("ext = ?")
                params.append(ext)
            
            if min_size is not None:
                conditions.append("size >= ?")
                params.append(min_size)
            
            if max_size is not None:
                conditions.append("size <= ?")
                params.append(max_size)
            
            where_clause = " AND ".join(conditions)
            
            sql = f"""
            SELECT file_id, path, size, mtime, ext, is_hidden, is_symlink
            FROM files
            WHERE {where_clause}
            ORDER BY {order_by_sql}
            LIMIT ? OFFSET ?
            """
            
            params.extend([limit, offset])
            
            cursor = conn.cursor()
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            
            entries = []
            for file_id, path_str, size, mtime_str, ext, is_hidden, is_symlink in rows:
                entries.append(
                    FileEntry(
                        path=Path(path_str),
                        size=size,
                        mtime=datetime.fromisoformat(mtime_str),
                        extension=ext,
                        file_id=file_id,  # file_id 포함
                        is_hidden=bool(is_hidden),
                        is_symlink=bool(is_symlink),
                    )
                )
            
            debug_step(
                self._log_sink,
                "list_files_complete",
                {
                    "run_id": run_id,
                    "entries_count": len(entries),
                }
            )
            
            return entries
        finally:
            conn.close()
    
    def close(self) -> None:
        """리소스 정리.
        
        메서드 호출마다 커넥션을 생성하므로 특별한 정리 작업은 없음.
        하지만 인터페이스 일관성을 위해 제공.
        """
        pass
