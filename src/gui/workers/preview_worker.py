"""Preview 스캔 워커 (빠른 파일 수 카운트)."""
import os
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, QThread, Signal

from app.settings.constants import DEFAULT_TEXT_EXTENSIONS
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
            parent: 부모 객체.
        """
        super().__init__(parent)
        self._folder = folder
        # None이면 기본 텍스트 확장자, 빈 리스트는 그대로 유지 (모든 파일)
        self._extensions = extensions if extensions is not None else DEFAULT_TEXT_EXTENSIONS
        self._include_subdirs = include_subdirs
        self._include_hidden = include_hidden
        self._include_symlinks = include_symlinks
        self._cancelled = False
    
    def cancel(self) -> None:
        """스캔 취소."""
        self._cancelled = True
    
    def run(self) -> None:
        """워커 실행."""
        try:
            stats = self._scan_folder(self._folder)
            if not self._cancelled:
                self.preview_completed.emit(stats)
        except Exception as e:
            if not self._cancelled:
                self.preview_error.emit(str(e))
    
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
        total_files = 0
        extension_counts: dict[str, int] = {}
        
        if not folder.exists():
            raise FileNotFoundError(f"폴더가 존재하지 않습니다: {folder}")
        
        if not folder.is_dir():
            raise ValueError(f"폴더가 아닙니다: {folder}")
        
        # 재귀적으로 스캔할 디렉토리 스택
        dirs_to_scan = [folder]
        
        while dirs_to_scan and not self._cancelled:
            current_dir = dirs_to_scan.pop(0)
            
            try:
                # os.scandir()로 빠른 순회 (stat 호출 없음)
                with os.scandir(current_dir) as entries:
                    subdirs = []
                    
                    for entry in entries:
                        if self._cancelled:
                            break
                        
                        # 숨김 파일/폴더 필터링
                        if not self._include_hidden and entry.name.startswith('.'):
                            continue
                        
                        # 파일인지 확인 (follow_symlinks=False로 최소 stat)
                        if entry.is_file(follow_symlinks=False):
                            # 심볼릭 링크 확인
                            if not self._include_symlinks and entry.is_symlink():
                                continue
                            
                            # 확장자 추출 및 필터링
                            file_path = Path(entry.path)
                            ext = file_path.suffix.lower()
                            if not ext:
                                ext = "(확장자 없음)"
                            
                            # 확장자 필터링: 리스트가 비어있거나 확장자가 리스트에 있으면 포함
                            if len(self._extensions) == 0 or ext in self._extensions:
                                total_files += 1
                                extension_counts[ext] = extension_counts.get(ext, 0) + 1
                        
                        # 디렉토리인지 확인 (하위 폴더 포함 시에만)
                        elif entry.is_dir(follow_symlinks=False) and self._include_subdirs:
                            # 심볼릭 링크 확인
                            if not self._include_symlinks and entry.is_symlink():
                                continue
                            
                            subdirs.append(Path(entry.path))
                    
                    # 하위 디렉토리를 스택에 추가
                    dirs_to_scan.extend(subdirs)
            
            except PermissionError:
                # 권한이 없는 디렉토리는 건너뛰기
                continue
            except Exception as e:
                # 기타 오류는 로깅만 하고 계속 진행
                print(f"디렉토리 스캔 오류 ({current_dir}): {e}")
                continue
        
        return PreviewStats(
            estimated_total_files=total_files,
            top_extensions=extension_counts
        )
