"""파일 시스템 스캐너."""
import os
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

from application.dto.scan_request import ScanRequest
from application.ports.file_scanner import FileScanner
from application.ports.log_sink import ILogSink
from application.utils.debug_logger import debug_step
from domain.entities.file_entry import FileEntry


class FileSystemScanner:
    """파일 시스템 스캐너 - FileScanner Protocol 구현."""
    
    def __init__(self, log_sink: Optional[ILogSink] = None) -> None:
        """스캐너 초기화.
        
        Args:
            log_sink: 로그 싱크 (선택적).
        """
        self._cancelled = False
        self._progress_callback: Optional[Callable[[int, str], None]] = None
        self._log_sink = log_sink
    
    def cancel(self) -> None:
        """스캔 취소."""
        self._cancelled = True
    
    def scan(
        self,
        request: ScanRequest,
        progress_callback: Optional[Callable[[int, str], None]] = None,
    ) -> list[FileEntry]:
        """폴더를 스캔하여 FileEntry 리스트 반환.
        
        Args:
            request: 스캔 요청 DTO.
            progress_callback: 진행률 콜백 (processed_count, message).
        
        Returns:
            FileEntry 리스트.
        
        Raises:
            FileNotFoundError: 폴더가 존재하지 않을 때.
            PermissionError: 폴더 접근 권한이 없을 때.
        """
        debug_step(
            self._log_sink,
            "scan_start",
            {
                "root_folder": str(request.root_folder),
                "extensions": request.extensions,
                "include_subdirs": request.include_subdirs,
                "include_hidden": request.include_hidden,
                "include_symlinks": request.include_symlinks,
            }
        )
        
        self._cancelled = False
        self._progress_callback = progress_callback
        
        root_folder = request.root_folder
        
        # 폴더 검증
        debug_step(self._log_sink, "folder_validation", {"path": str(root_folder)})
        if not root_folder.exists():
            raise FileNotFoundError(f"폴더가 존재하지 않습니다: {root_folder}")
        
        if not root_folder.is_dir():
            raise ValueError(f"폴더가 아닙니다: {root_folder}")
        
        # 확장자 필터 처리 (request에 들어온 값만 사용)
        extensions = request.extensions
        # None이면 전체 파일, list면 필터만 수행
        # 빈 리스트 처리(기본 확장자)는 UseCase에서 수행
        
        debug_step(
            self._log_sink,
            "scan_config",
            {
                "extensions": extensions,
                "include_subdirs": request.include_subdirs,
                "include_hidden": request.include_hidden,
                "include_symlinks": request.include_symlinks,
            }
        )
        
        entries: list[FileEntry] = []
        dirs_to_scan = [root_folder]
        processed_files = 0
        
        debug_step(self._log_sink, "directory_scan_start", {"root_path": str(root_folder)})
        
        while dirs_to_scan and not self._cancelled:
            current_dir = dirs_to_scan.pop(0)
            
            try:
                with os.scandir(current_dir) as it:
                    for entry in it:
                        if self._cancelled:
                            break
                        
                        # 숨김 파일 필터
                        if entry.name.startswith('.') and not request.include_hidden:
                            continue
                        
                        # 심볼릭 링크 처리
                        if entry.is_symlink():
                            if not request.include_symlinks:
                                continue
                            # TODO: 순환 링크 방지 (Phase 2에서 추가)
                        
                        if entry.is_file(follow_symlinks=False):
                            # 확장자 필터
                            if extensions is not None:
                                ext = Path(entry.name).suffix.lower()
                                if ext not in extensions:
                                    continue
                            
                            try:
                                stat = entry.stat(follow_symlinks=False)
                                ext = Path(entry.name).suffix.lower()
                                # 확장자 없으면 빈 문자열
                                file_entry = FileEntry(
                                    path=Path(entry.path),
                                    size=stat.st_size,
                                    mtime=datetime.fromtimestamp(stat.st_mtime),
                                    extension=ext,  # 빈 문자열 가능
                                    is_symlink=entry.is_symlink(),
                                    is_hidden=entry.name.startswith('.'),
                                )
                                entries.append(file_entry)
                                processed_files += 1
                                
                                # 진행률 콜백 및 로그 (매 100개 파일마다)
                                if processed_files % 100 == 0:
                                    total_bytes = sum(e.size for e in entries)
                                    debug_step(
                                        self._log_sink,
                                        "file_processed",
                                        {
                                            "count": processed_files,
                                            "total_bytes": total_bytes,
                                            "current_dir": str(current_dir),
                                        }
                                    )
                                    if self._progress_callback:
                                        self._progress_callback(
                                            processed_files,
                                            f"{processed_files}개 파일 스캔 완료..."
                                        )
                            except (OSError, PermissionError):
                                # 파일 접근 오류는 무시하고 계속
                                continue
                        
                        elif entry.is_dir(follow_symlinks=False) and request.include_subdirs:
                            dirs_to_scan.append(Path(entry.path))
            
            except (PermissionError, OSError) as e:
                # 디렉토리 접근 오류는 무시하고 계속
                debug_step(
                    self._log_sink,
                    "directory_access_error",
                    {
                        "path": str(current_dir),
                        "error": str(e),
                        "error_type": type(e).__name__,
                    }
                )
                continue
        
        total_bytes = sum(e.size for e in entries)
        debug_step(
            self._log_sink,
            "scan_complete",
            {
                "total_files": len(entries),
                "total_bytes": total_bytes,
                "processed_files": processed_files,
                "cancelled": self._cancelled,
            }
        )
        
        return entries
