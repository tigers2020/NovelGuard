"""스캔 폴더 UseCase."""
import time
from datetime import datetime
from typing import Callable, Optional

from application.dto.scan_request import ScanRequest
from application.dto.scan_result import ScanResult
from application.ports.file_scanner import FileScanner


class ScanFolderUseCase:
    """스캔 폴더 UseCase."""
    
    def __init__(self, scanner: FileScanner) -> None:
        """UseCase 초기화.
        
        Args:
            scanner: 파일 스캐너 (Port 인터페이스).
        """
        self._scanner = scanner
    
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
        start_time = time.time()
        
        # 기본 확장자 규칙 처리 (빈 리스트면 기본 텍스트 확장자)
        from app.settings.constants import DEFAULT_TEXT_EXTENSIONS
        if request.extensions is not None and len(request.extensions) == 0:
            # request를 수정하지 않고 새 객체 생성 (불변성)
            request = ScanRequest(
                root_folder=request.root_folder,
                extensions=DEFAULT_TEXT_EXTENSIONS,
                include_subdirs=request.include_subdirs,
                include_hidden=request.include_hidden,
                include_symlinks=request.include_symlinks,
                incremental=request.incremental,
            )
        
        # 스캔 실행 (scanner는 주입받음)
        entries = self._scanner.scan(request, progress_callback)
        
        # 결과 계산
        total_bytes = sum(entry.size for entry in entries)
        elapsed_ms = int((time.time() - start_time) * 1000)
        
        result = ScanResult(
            total_files=len(entries),
            total_bytes=total_bytes,
            entries=entries,
            elapsed_ms=elapsed_ms,
            warnings_count=0,  # TODO: Phase 2에서 구현
            scan_timestamp=datetime.now(),
        )
        
        return result
