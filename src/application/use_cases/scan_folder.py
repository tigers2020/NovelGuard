"""스캔 폴더 UseCase."""
import json
import time
from datetime import datetime
from typing import Callable, Optional

from application.dto.run_summary import RunSummary
from application.dto.scan_request import ScanRequest
from application.dto.scan_result import ScanResult
from application.dto.log_entry import LogEntry
from application.ports.file_scanner import FileScanner
from application.ports.index_repository import IIndexRepository
from application.ports.log_sink import ILogSink
from application.utils.debug_logger import debug_step


class ScanFolderUseCase:
    """스캔 폴더 UseCase."""
    
    def __init__(
        self,
        scanner: FileScanner,
        index_repository: Optional[IIndexRepository] = None,
        log_sink: Optional[ILogSink] = None
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
            }
        )
        
        start_time = time.time()
        run_id: Optional[int] = None
        
        # 기본 확장자 규칙 처리 (빈 리스트면 기본 텍스트 확장자)
        from app.settings.constants import DEFAULT_TEXT_EXTENSIONS
        if request.extensions is not None and len(request.extensions) == 0:
            debug_step(
                self._log_sink,
                "extensions_default_applied",
                {"default_extensions": DEFAULT_TEXT_EXTENSIONS}
            )
            # request를 수정하지 않고 새 객체 생성 (불변성)
            request = ScanRequest(
                root_folder=request.root_folder,
                extensions=DEFAULT_TEXT_EXTENSIONS,
                include_subdirs=request.include_subdirs,
                include_hidden=request.include_hidden,
                include_symlinks=request.include_symlinks,
                incremental=request.incremental,
            )
        
        # Run 시작 (index_repository가 있으면)
        if self._index_repository:
            debug_step(self._log_sink, "run_start_begin")
            try:
                run_id = self._index_repository.start_run(request)
                debug_step(
                    self._log_sink,
                    "run_start_success",
                    {"run_id": run_id}
                )
            except Exception as e:
                # DB 저장 실패는 로그만 기록하고 계속 진행
                if self._log_sink:
                    self._log_sink.write(LogEntry(
                        timestamp=datetime.now(),
                        level="ERROR",
                        message=f"Failed to start run in index repository: {e}",
                        context={"error_type": type(e).__name__}
                    ))
        
        # 스캔 실행 (scanner는 주입받음)
        debug_step(self._log_sink, "scan_execution_begin")
        entries = self._scanner.scan(request, progress_callback)
        debug_step(
            self._log_sink,
            "scan_execution_complete",
            {"entries_count": len(entries)}
        )
        
        # 결과 계산
        debug_step(self._log_sink, "result_calculation_begin")
        total_bytes = sum(entry.size for entry in entries)
        from app.settings.constants import Constants
        elapsed_ms = int((time.time() - start_time) * Constants.MILLISECONDS_PER_SECOND)
        
        result = ScanResult(
            total_files=len(entries),
            total_bytes=total_bytes,
            entries=entries,
            elapsed_ms=elapsed_ms,
            warnings_count=0,  # TODO: Phase 2에서 구현
            scan_timestamp=datetime.now(),
        )
        
        debug_step(
            self._log_sink,
            "result_calculation_complete",
            {
                "total_files": result.total_files,
                "total_bytes": total_bytes,
                "elapsed_ms": elapsed_ms,
            }
        )
        
        # 파일 저장 (run_id가 있고 entries가 있으면)
        if self._index_repository and run_id is not None and entries:
            debug_step(
                self._log_sink,
                "files_save_begin",
                {"run_id": run_id, "entries_count": len(entries)}
            )
            try:
                self._index_repository.upsert_files(run_id, entries)
                debug_step(
                    self._log_sink,
                    "files_save_success",
                    {"run_id": run_id, "entries_count": len(entries)}
                )
            except Exception as e:
                # DB 저장 실패는 로그만 기록하고 계속 진행
                if self._log_sink:
                    self._log_sink.write(LogEntry(
                        timestamp=datetime.now(),
                        level="ERROR",
                        message=f"Failed to save files to index repository: {e}",
                        context={"error_type": type(e).__name__, "run_id": run_id}
                    ))
        
        # Run 완료 처리 (run_id가 있으면)
        if self._index_repository and run_id is not None:
            debug_step(self._log_sink, "run_finalize_begin", {"run_id": run_id})
            try:
                options_json = json.dumps({
                    "extensions": request.extensions,
                    "include_subdirs": request.include_subdirs,
                    "include_hidden": request.include_hidden,
                    "include_symlinks": request.include_symlinks,
                    "incremental": request.incremental,
                })
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
                debug_step(
                    self._log_sink,
                    "run_finalize_success",
                    {"run_id": run_id}
                )
            except Exception as e:
                # DB 저장 실패는 로그만 기록하고 계속 진행
                if self._log_sink:
                    self._log_sink.write(LogEntry(
                        timestamp=datetime.now(),
                        level="ERROR",
                        message=f"Failed to finalize run in index repository: {e}",
                        context={"error_type": type(e).__name__, "run_id": run_id}
                    ))
        
        debug_step(
            self._log_sink,
            "execute_complete",
            {
                "total_files": result.total_files,
                "total_bytes": result.total_bytes,
                "elapsed_ms": result.elapsed_ms,
                "run_id": run_id,
            }
        )
        
        return result
