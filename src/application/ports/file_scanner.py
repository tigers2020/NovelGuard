"""파일 스캐너 Port 인터페이스."""
from typing import Protocol, Callable, Optional

from application.dto.scan_request import ScanRequest
from domain.entities.file_entry import FileEntry


class FileScanner(Protocol):
    """파일 스캐너 인터페이스.
    
    파일 시스템을 스캔하여 FileEntry 리스트를 반환하는 인터페이스.
    Infrastructure 계층에서 구현해야 함.
    """
    
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
        """
        ...
    
    def cancel(self) -> None:
        """스캔 취소."""
        ...
