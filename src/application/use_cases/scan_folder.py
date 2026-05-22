"""스캔 폴더 UseCase."""

import json
import time
from datetime import datetime
from typing import Callable, Optional

from application.constants import DEFAULT_TEXT_EXTENSIONS, Constants
from application.dto.log_entry import LogEntry
from application.dto.run_summary import RunSummary
from application.dto.scan_request import ScanRequest
from application.dto.scan_result import ScanResult
from application.exceptions import IndexPersistenceError
from application.ports.file_scanner import FileScanner
from application.ports.index_repository import IIndexRepository
from application.ports.log_sink import ILogSink
from application.utils.debug_logger import debug_step
from domain.entities.file_entry import FileEntry


class ScanFolderUseCase:
    """스캔 폴더 UseCase."""

    def __init__(
        self,
        scanner: FileScanner,
        index_repository: Optional[IIndexRepository] = None,
        log_sink: Optional[ILogSink] = None,
    ) -> None:
        """UseCase 초기화.

        Args:
            scanner: 파일 스캐너 (Port 인터페이스).
            index_repository: 인덱스 저장소 (선택적).
            log_sink: 로그 싱크 (선택적).
        """
        self._scanner = scanner
        self._index_repository = index_repository
        self._log_sink = log_sink

    def _write_index_error(self, message: str, context: dict) -> None:
        if not self._log_sink:
            return
        self._log_sink.write(
            LogEntry(
                timestamp=datetime.now(),
                level="ERROR",
                message=message,
                context=context,
            )
        )

    def _normalize_extensions(self, request: ScanRequest) -> ScanRequest:
        if request.extensions is None or len(request.extensions) > 0:
            return request
        debug_step(
            self._log_sink,
            "extensions_default_applied",
            {"default_extensions": DEFAULT_TEXT_EXTENSIONS},
        )
        return ScanRequest(
            root_folder=request.root_folder,
            extensions=DEFAULT_TEXT_EXTENSIONS,
            include_subdirs=request.include_subdirs,
            include_hidden=request.include_hidden,
            include_symlinks=request.include_symlinks,
            incremental=request.incremental,
        )

    def _start_index_run(self, request: ScanRequest) -> Optional[int]:
        if not self._index_repository:
            return None
        debug_step(self._log_sink, "run_start_begin")
        try:
            run_id = self._index_repository.start_run(request)
            debug_step(self._log_sink, "run_start_success", {"run_id": run_id})
            return run_id
        except (OSError, IndexPersistenceError, ValueError) as e:
            self._write_index_error(
                f"Failed to start run in index repository: {e}",
                {"error_type": type(e).__name__},
            )
            return None

    def _save_index_files(self, run_id: Optional[int], entries: list[FileEntry]) -> None:
        if not self._index_repository or run_id is None or not entries:
            return
        debug_step(
            self._log_sink,
            "files_save_begin",
            {"run_id": run_id, "entries_count": len(entries)},
        )
        try:
            self._index_repository.upsert_files(run_id, entries)
            debug_step(
                self._log_sink,
                "files_save_success",
                {"run_id": run_id, "entries_count": len(entries)},
            )
        except (OSError, IndexPersistenceError, ValueError) as e:
            self._write_index_error(
                f"Failed to save files to index repository: {e}",
                {"error_type": type(e).__name__, "run_id": run_id},
            )

    def _finalize_index_run(
        self,
        run_id: Optional[int],
        request: ScanRequest,
        result: ScanResult,
        start_time: float,
    ) -> None:
        if not self._index_repository or run_id is None:
            return
        debug_step(self._log_sink, "run_finalize_begin", {"run_id": run_id})
        try:
            options_json = json.dumps(
                {
                    "extensions": request.extensions,
                    "include_subdirs": request.include_subdirs,
                    "include_hidden": request.include_hidden,
                    "include_symlinks": request.include_symlinks,
                    "incremental": request.incremental,
                }
            )
            summary = RunSummary(
                run_id=run_id,
                started_at=datetime.fromtimestamp(start_time),
                finished_at=datetime.now(),
                root_path=request.root_folder,
                options_json=options_json,
                total_files=result.total_files,
                total_bytes=result.total_bytes,
                elapsed_ms=result.elapsed_ms,
                status="completed",
                error_message=None,
            )
            self._index_repository.finalize_run(run_id, summary)
            debug_step(self._log_sink, "run_finalize_success", {"run_id": run_id})
        except (OSError, IndexPersistenceError, TypeError, ValueError) as e:
            self._write_index_error(
                f"Failed to finalize run in index repository: {e}",
                {"error_type": type(e).__name__, "run_id": run_id},
            )

    def execute(
        self,
        request: ScanRequest,
        progress_callback: Optional[Callable[[int, str], None]] = None,
    ) -> ScanResult:
        """스캔 실행.

        Args:
            request: 스캔 요청 DTO.
            progress_callback: 진행률 콜백 (processed_count, message).

        Returns:
            스캔 결과 DTO.
        """
        debug_step(
            self._log_sink,
            "execute_start",
            {
                "root_folder": str(request.root_folder),
                "extensions": request.extensions,
                "include_subdirs": request.include_subdirs,
                "include_hidden": request.include_hidden,
                "include_symlinks": request.include_symlinks,
                "incremental": request.incremental,
                "has_index_repository": self._index_repository is not None,
            },
        )

        start_time = time.time()
        request = self._normalize_extensions(request)
        run_id = self._start_index_run(request)

        # 스캔 실행 (scanner는 주입받음)
        debug_step(self._log_sink, "scan_execution_begin")
        outcome = self._scanner.scan(request, progress_callback)
        entries = outcome.entries
        debug_step(
            self._log_sink,
            "scan_execution_complete",
            {"entries_count": len(entries), "warnings_count": outcome.warnings_count},
        )

        # 결과 계산
        debug_step(self._log_sink, "result_calculation_begin")
        total_bytes = sum(entry.size for entry in entries)
        elapsed_ms = int((time.time() - start_time) * Constants.MILLISECONDS_PER_SECOND)

        result = ScanResult(
            total_files=len(entries),
            total_bytes=total_bytes,
            entries=entries,
            elapsed_ms=elapsed_ms,
            warnings_count=outcome.warnings_count,
            scan_timestamp=datetime.now(),
        )

        debug_step(
            self._log_sink,
            "result_calculation_complete",
            {
                "total_files": result.total_files,
                "total_bytes": total_bytes,
                "elapsed_ms": elapsed_ms,
                "warnings_count": result.warnings_count,
            },
        )

        self._save_index_files(run_id, entries)
        self._finalize_index_run(run_id, request, result, start_time)

        debug_step(
            self._log_sink,
            "execute_complete",
            {
                "total_files": result.total_files,
                "total_bytes": result.total_bytes,
                "elapsed_ms": result.elapsed_ms,
                "run_id": run_id,
            },
        )

        return result
