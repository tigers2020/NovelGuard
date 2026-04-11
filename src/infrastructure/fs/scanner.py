"""파일 시스템 스캐너."""
import os
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

from application.dto.folder_scan_outcome import FolderScanOutcome
from application.dto.scan_request import ScanRequest
from application.ports.file_scanner import FileScanner
from application.ports.log_sink import ILogSink
from application.utils.debug_logger import debug_step
from domain.entities.file_entry import FileEntry


def _validate_root_folder(root_folder: Path, log_sink: Optional[ILogSink]) -> None:
    """루트 폴더 존재 및 디렉터리 여부 검증. 실패 시 예외 발생."""
    debug_step(log_sink, "folder_validation", {"path": str(root_folder)})
    if not root_folder.exists():
        raise FileNotFoundError(f"폴더가 존재하지 않습니다: {root_folder}")
    if not root_folder.is_dir():
        raise ValueError(f"폴더가 아닙니다: {root_folder}")


def _should_skip_entry(entry: os.DirEntry[str], request: ScanRequest) -> bool:
    """숨김/심볼릭 링크 설정에 따라 엔트리 스킵 여부 반환."""
    if entry.name.startswith(".") and not request.include_hidden:
        return True
    # 심볼릭 링크: 미포함 설정이면 스킵. Phase 2에서 순환 링크 방지 추가 예정.
    if entry.is_symlink() and not request.include_symlinks:
        return True
    return False


def _extension_matches(name: str, extensions: Optional[list[str]]) -> bool:
    """확장자 필터 일치 여부. extensions가 None이면 항상 True."""
    if extensions is None:
        return True
    return Path(name).suffix.lower() in extensions


def _try_make_file_entry(entry: os.DirEntry[str]) -> Optional[FileEntry]:
    """엔트리로부터 FileEntry 생성. 접근 오류 시 None 반환."""
    try:
        stat = entry.stat(follow_symlinks=False)
        ext = Path(entry.name).suffix.lower()
        return FileEntry(
            path=Path(entry.path),
            size=stat.st_size,
            mtime=datetime.fromtimestamp(stat.st_mtime),
            extension=ext,
            is_symlink=entry.is_symlink(),
            is_hidden=entry.name.startswith("."),
        )
    except OSError:
        return None


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
    ) -> FolderScanOutcome:
        """폴더를 스캔하여 엔트리와 경고 수를 반환.

        Args:
            request: 스캔 요청 DTO.
            progress_callback: 진행률 콜백 (processed_count, message).

        Returns:
            스캔 결과(엔트리 + 비치명적 오류 건수).

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
            },
        )
        self._cancelled = False
        self._progress_callback = progress_callback
        root_folder = request.root_folder

        _validate_root_folder(root_folder, self._log_sink)

        extensions = request.extensions
        debug_step(
            self._log_sink,
            "scan_config",
            {
                "extensions": extensions,
                "include_subdirs": request.include_subdirs,
                "include_hidden": request.include_hidden,
                "include_symlinks": request.include_symlinks,
            },
        )

        entries: list[FileEntry] = []
        dirs_to_scan: deque[Path] = deque([root_folder])
        processed_files = 0
        total_bytes = 0
        warnings_count = 0
        debug_step(self._log_sink, "directory_scan_start", {"root_path": str(root_folder)})

        while dirs_to_scan and not self._cancelled:
            current_dir = dirs_to_scan.popleft()
            try:
                files_delta, bytes_delta, warn_delta = self._process_directory(
                    current_dir, request, extensions, entries, dirs_to_scan
                )
                warnings_count += warn_delta
                old_count = processed_files
                processed_files += files_delta
                total_bytes += bytes_delta
                n = (old_count // 100 + 1) * 100
                while n <= processed_files:
                    self._emit_progress(n, total_bytes, current_dir)
                    n += 100
            except OSError as e:
                warnings_count += 1
                debug_step(
                    self._log_sink,
                    "directory_access_error",
                    {"path": str(current_dir), "error": str(e), "error_type": type(e).__name__},
                )

        debug_step(
            self._log_sink,
            "scan_complete",
            {
                "total_files": len(entries),
                "total_bytes": total_bytes,
                "processed_files": processed_files,
                "warnings_count": warnings_count,
                "cancelled": self._cancelled,
            },
        )
        return FolderScanOutcome(entries=entries, warnings_count=warnings_count)

    def _process_directory(
        self,
        current_dir: Path,
        request: ScanRequest,
        extensions: Optional[list[str]],
        entries: list[FileEntry],
        dirs_to_scan: deque[Path],
    ) -> tuple[int, int, int]:
        """한 디렉터리 스캔: 처리 파일 수·바이트·경고 증가분 반환."""
        files_delta = 0
        bytes_delta = 0
        warnings_delta = 0
        with os.scandir(current_dir) as it:
            for entry in it:
                if self._cancelled:
                    break
                if _should_skip_entry(entry, request):
                    continue
                if entry.is_file(follow_symlinks=False):
                    if not _extension_matches(entry.name, extensions):
                        continue
                    file_entry = _try_make_file_entry(entry)
                    if file_entry is None:
                        warnings_delta += 1
                        continue
                    entries.append(file_entry)
                    files_delta += 1
                    bytes_delta += file_entry.size
                elif entry.is_dir(follow_symlinks=False) and request.include_subdirs:
                    dirs_to_scan.append(Path(entry.path))
        return files_delta, bytes_delta, warnings_delta

    def _emit_progress(self, processed_files: int, total_bytes: int, current_dir: Path) -> None:
        """진행 로그 및 콜백 호출 (매 100개마다)."""
        debug_step(
            self._log_sink,
            "file_processed",
            {"count": processed_files, "total_bytes": total_bytes, "current_dir": str(current_dir)},
        )
        if self._progress_callback:
            self._progress_callback(processed_files, f"{processed_files}개 파일 스캔 완료...")
