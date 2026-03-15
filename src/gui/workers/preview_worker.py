"""Preview 스캔 워커 (빠른 파일 수 카운트)."""
import os
from collections import deque
from pathlib import Path
from typing import Optional, Tuple

from PySide6.QtCore import QObject, QThread, Signal

from app.settings.constants import DEFAULT_TEXT_EXTENSIONS
from application.ports.log_sink import ILogSink
from application.utils.debug_logger import debug_step
from domain.value_objects.preview_stats import PreviewStats


class PreviewWorker(QThread):
    """Preview 스캔 워커 스레드.
    
    빠른 미리보기 정보를 제공하기 위한 경량 스캔.
    os.scandir()만 사용하여 파일 수와 확장자 분포만 카운트.
    """
    
    preview_completed = Signal(PreviewStats)
    """Preview 스캔 완료 시그널."""
    
    preview_error = Signal(str)
    """Preview 스캔 오류 시그널."""
    
    def __init__(
        self,
        folder: Path,
        extensions: Optional[list[str]] = None,
        include_subdirs: bool = True,
        include_hidden: bool = False,
        include_symlinks: bool = True,
        log_sink: Optional[ILogSink] = None,
        parent: Optional[QObject] = None
    ) -> None:
        """Preview 워커 초기화.
        
        Args:
            folder: 스캔할 폴더 경로.
            extensions: 필터링할 확장자 리스트. None이면 기본 텍스트 확장자 사용.
                       빈 리스트 []이면 모든 파일 포함.
            include_subdirs: 하위 폴더 포함 여부.
            include_hidden: 숨김 파일 포함 여부.
            include_symlinks: 심볼릭 링크 포함 여부.
            log_sink: 로그 싱크 (선택적).
            parent: 부모 객체.
        """
        super().__init__(parent)
        self._folder = folder
        # None이면 기본 텍스트 확장자, 빈 리스트는 그대로 유지 (모든 파일)
        self._extensions = extensions if extensions is not None else DEFAULT_TEXT_EXTENSIONS
        self._include_subdirs = include_subdirs
        self._include_hidden = include_hidden
        self._include_symlinks = include_symlinks
        self._log_sink = log_sink
        self._cancelled = False
    
    def cancel(self) -> None:
        """스캔 취소."""
        self._cancelled = True
    
    def run(self) -> None:
        """워커 실행."""
        debug_step(
            self._log_sink,
            "preview_worker_run_start",
            {
                "folder": str(self._folder),
                "extensions": self._extensions,
                "include_subdirs": self._include_subdirs,
                "include_hidden": self._include_hidden,
                "include_symlinks": self._include_symlinks,
            }
        )
        
        try:
            stats = self._scan_folder(self._folder)
            if not self._cancelled:
                debug_step(
                    self._log_sink,
                    "preview_worker_completed",
                    {
                        "estimated_total_files": stats.estimated_total_files,
                        "top_extensions_count": len(stats.top_extensions),
                    }
                )
                self.preview_completed.emit(stats)
        except Exception as e:
            if not self._cancelled:
                debug_step(
                    self._log_sink,
                    "preview_worker_error",
                    {
                        "error": str(e),
                        "error_type": type(e).__name__,
                    }
                )
                self.preview_error.emit(str(e))
    
    def _should_skip_hidden(self, entry: os.DirEntry) -> bool:
        """숨김 파일/폴더 여부로 스킵할지 판단."""
        return not self._include_hidden and entry.name.startswith(".")

    def _should_skip_symlink(self, entry: os.DirEntry) -> bool:
        """심볼릭 링크 제외 설정이면 스킵할지 판단."""
        return not self._include_symlinks and entry.is_symlink()

    def _normalized_extension(self, entry: os.DirEntry) -> Optional[str]:
        """엔트리가 확장자 필터를 통과하면 확장자 문자열, 아니면 None."""
        path = Path(entry.path)
        ext = path.suffix.lower() or "(확장자 없음)"
        if len(self._extensions) != 0 and ext not in self._extensions:
            return None
        return ext

    def _process_entry(
        self, entry: os.DirEntry
    ) -> Tuple[int, Optional[str], Optional[Path]]:
        """단일 scandir 엔트리 처리.
        
        Returns:
            (추가할 파일 수, 확장자 또는 None, 하위 디렉토리 Path 또는 None)
        """
        if self._should_skip_hidden(entry):
            return (0, None, None)
        if entry.is_file(follow_symlinks=False):
            if self._should_skip_symlink(entry):
                return (0, None, None)
            ext = self._normalized_extension(entry)
            if ext is None:
                return (0, None, None)
            return (1, ext, None)
        if entry.is_dir(follow_symlinks=False) and self._include_subdirs:
            if self._should_skip_symlink(entry):
                return (0, None, None)
            return (0, None, Path(entry.path))
        return (0, None, None)

    def _scan_one_dir(
        self, current_dir: Path
    ) -> Tuple[list[Path], int, dict[str, int]]:
        """한 디렉토리만 스캔. (subdirs, 파일 증가분, 확장자 증가분)."""
        subdirs: list[Path] = []
        added_files = 0
        ext_delta: dict[str, int] = {}
        with os.scandir(current_dir) as entries:
            for entry in entries:
                if self._cancelled:
                    break
                add_count, ext, subdir_path = self._process_entry(entry)
                if add_count and ext:
                    added_files += add_count
                    ext_delta[ext] = ext_delta.get(ext, 0) + 1
                if subdir_path is not None:
                    subdirs.append(subdir_path)
        return subdirs, added_files, ext_delta

    def _scan_folder(self, folder: Path) -> PreviewStats:
        """폴더 스캔하여 PreviewStats 생성.
        
        os.scandir()를 사용하여 빠른 순회 수행.
        stat() 호출 없이 파일 수와 확장자만 카운트.
        
        Args:
            folder: 스캔할 폴더.
        
        Returns:
            PreviewStats 객체.
        
        Raises:
            FileNotFoundError: 폴더가 존재하지 않을 때.
            PermissionError: 폴더 접근 권한이 없을 때.
        """
        if not folder.exists():
            raise FileNotFoundError(f"폴더가 존재하지 않습니다: {folder}")
        if not folder.is_dir():
            raise ValueError(f"폴더가 아닙니다: {folder}")

        total_files = 0
        extension_counts: dict[str, int] = {}
        dirs_to_scan: deque[Path] = deque([folder])

        while dirs_to_scan and not self._cancelled:
            current_dir = dirs_to_scan.popleft()
            try:
                subdirs, added_files, ext_delta = self._scan_one_dir(current_dir)
                total_files += added_files
                for ext, count in ext_delta.items():
                    extension_counts[ext] = extension_counts.get(ext, 0) + count
                dirs_to_scan.extend(subdirs)
            except PermissionError:
                continue
            except Exception as e:
                print(f"디렉토리 스캔 오류 ({current_dir}): {e}")
                continue

        return PreviewStats(
            estimated_total_files=total_files,
            top_extensions=extension_counts
        )
