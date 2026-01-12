"""파일 이동 워커 스레드."""
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, QThread, Signal

from application.dto.log_entry import LogEntry
from application.ports.log_sink import ILogSink
from application.use_cases.move_duplicate_files import MoveDuplicateFilesUseCase, MoveOperation
from application.utils.debug_logger import debug_step


class FileMoveWorker(QThread):
    """파일 이동 워커 스레드.
    
    QThread를 상속하여 별도 스레드에서 파일 이동 작업을 수행.
    """
    
    move_progress = Signal(int, int, str)
    """이동 진행률 시그널 (processed_count, total_count, current_file)."""
    
    move_completed = Signal(int, int, list, list)
    """이동 완료 시그널 (moved_count, error_count, error_list, moved_file_ids)."""
    
    move_error = Signal(str)
    """이동 오류 시그널."""
    
    def __init__(
        self,
        use_case: MoveDuplicateFilesUseCase,
        scan_folder: Path,
        log_sink: Optional[ILogSink] = None,
        parent: Optional[QObject] = None
    ) -> None:
        """파일 이동 워커 초기화.
        
        Args:
            use_case: 파일 이동 UseCase.
            scan_folder: 스캔 폴더 경로.
            log_sink: 로그 싱크 (선택적).
            parent: 부모 객체.
        """
        super().__init__(parent)
        self._use_case = use_case
        self._scan_folder = scan_folder
        self._log_sink = log_sink
        self._cancelled = False
    
    def cancel(self) -> None:
        """파일 이동 취소."""
        debug_step(self._log_sink, "file_move_worker_cancel")
        self._cancelled = True
    
    def run(self) -> None:
        """워커 실행."""
        debug_step(
            self._log_sink,
            "file_move_worker_run_start",
            {
                "scan_folder": str(self._scan_folder)
            }
        )
        
        try:
            # 이동 작업 목록 생성 (dry_run=False는 execute에서 실제로 사용하지 않음)
            move_operations = self._use_case.execute(self._scan_folder, dry_run=False)
            
            if not move_operations:
                # 이동할 파일이 없음
                self.move_completed.emit(0, 0, [], [])
                return
            
            total_count = len(move_operations)
            moved_count = 0
            error_count = 0
            error_list: list[tuple[Path, str]] = []  # (파일 경로, 에러 메시지)
            moved_file_ids: list[int] = []  # 이동 성공한 file_id 리스트
            
            for idx, operation in enumerate(move_operations):
                if self._cancelled:
                    debug_step(self._log_sink, "file_move_worker_cancelled")
                    break
                
                # 진행률 업데이트
                self.move_progress.emit(idx, total_count, str(operation.source_path))
                
                try:
                    # 대상 폴더 생성
                    target_dir = operation.target_path.parent
                    target_dir.mkdir(parents=True, exist_ok=True)
                    
                    # 파일 이동
                    shutil.move(str(operation.source_path), str(operation.target_path))
                    moved_count += 1
                    moved_file_ids.append(operation.file_id)
                    
                    if self._log_sink:
                        self._log_sink.write(LogEntry(
                            timestamp=datetime.now(),
                            level="INFO",
                            message=f"파일 이동 완료: {operation.source_path} → {operation.target_path}",
                            context={
                                "file_id": operation.file_id,
                                "source_path": str(operation.source_path),
                                "target_path": str(operation.target_path)
                            }
                        ))
                
                except Exception as e:
                    error_count += 1
                    error_msg = str(e)
                    error_list.append((operation.source_path, error_msg))
                    
                    if self._log_sink:
                        self._log_sink.write(LogEntry(
                            timestamp=datetime.now(),
                            level="ERROR",
                            message=f"파일 이동 실패: {operation.source_path} - {error_msg}",
                            context={
                                "file_id": operation.file_id,
                                "source_path": str(operation.source_path),
                                "target_path": str(operation.target_path),
                                "error": error_msg,
                                "error_type": type(e).__name__
                            }
                        ))
            
            # 완료 시그널
            debug_step(
                self._log_sink,
                "file_move_worker_completed",
                {
                    "total_count": total_count,
                    "moved_count": moved_count,
                    "error_count": error_count
                }
            )
            self.move_completed.emit(moved_count, error_count, error_list, moved_file_ids)
        
        except Exception as e:
            error_msg = f"파일 이동 작업 오류: {str(e)}"
            debug_step(
                self._log_sink,
                "file_move_worker_error",
                {
                    "error": error_msg,
                    "error_type": type(e).__name__
                }
            )
            if self._log_sink:
                self._log_sink.write(LogEntry(
                    timestamp=datetime.now(),
                    level="ERROR",
                    message=error_msg,
                    context={
                        "error": str(e),
                        "error_type": type(e).__name__
                    }
                ))
            self.move_error.emit(error_msg)
