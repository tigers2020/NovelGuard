"""파일 시스템 스캐너.

파일 스캔 및 경로 처리.
"""

from pathlib import Path
from typing import Iterator, Optional
from common.errors import NovelGuardError
from common.logging import setup_logging

logger = setup_logging()


class FileScanner:
    """파일 시스템 스캐너."""
    
    def __init__(
        self,
        extensions: Optional[list[str]] = None,
        recursive: bool = True,
        include_hidden: bool = False,
        follow_symlinks: bool = True
    ) -> None:
        """파일 스캐너 초기화.
        
        Args:
            extensions: 허용 확장자 리스트 (None이면 모든 파일)
            recursive: 하위 폴더 포함 여부
            include_hidden: 숨김 파일 포함 여부
            follow_symlinks: 심볼릭 링크 따라가기 여부
        """
        self.extensions = extensions
        self.recursive = recursive
        self.include_hidden = include_hidden
        self.follow_symlinks = follow_symlinks
    
    def scan_directory(self, root_path: Path) -> Iterator[Path]:
        """디렉토리 스캔.
        
        Args:
            root_path: 루트 경로
        
        Yields:
            파일 Path
        """
        if not root_path.exists():
            raise NovelGuardError(f"경로가 존재하지 않습니다: {root_path}")
        
        if not root_path.is_dir():
            raise NovelGuardError(f"디렉토리가 아닙니다: {root_path}")
        
        pattern = "**/*" if self.recursive else "*"
        
        try:
            for path in root_path.glob(pattern):
                # 디렉토리는 제외
                if path.is_dir():
                    continue
                
                # 숨김 파일 필터링
                if not self.include_hidden and self._is_hidden(path):
                    continue
                
                # 심볼릭 링크 처리
                if path.is_symlink():
                    if not self.follow_symlinks:
                        continue
                    # 심볼릭 링크의 실제 파일 확인
                    try:
                        real_path = path.resolve()
                        if not real_path.exists():
                            continue
                        path = real_path
                    except Exception as e:
                        logger.warning(f"심볼릭 링크 해석 실패: {path} - {e}")
                        continue
                
                # 확장자 필터링
                if self.extensions:
                    if path.suffix.lower() not in [ext.lower() for ext in self.extensions]:
                        continue
                
                yield path
        except Exception as e:
            logger.error(f"디렉토리 스캔 오류: {root_path} - {e}")
            raise NovelGuardError(f"스캔 실패: {e}") from e
    
    def _is_hidden(self, path: Path) -> bool:
        """숨김 파일 여부 확인.
        
        Args:
            path: 파일 경로
        
        Returns:
            숨김 파일 여부
        """
        # Windows
        import platform
        if platform.system() == "Windows":
            try:
                # 파일 속성에서 숨김 확인
                import win32api
                import win32con
                attrs = win32api.GetFileAttributes(str(path))
                return bool(attrs & win32con.FILE_ATTRIBUTE_HIDDEN)
            except ImportError:
                # win32api가 없으면 이름으로 판단
                return path.name.startswith('.')
        
        # Unix 계열
        return path.name.startswith('.')

