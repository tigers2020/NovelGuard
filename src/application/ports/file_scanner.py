"""파일 스캐너 Port 인터페이스."""

from typing import Callable, Optional, Protocol

from application.dto.folder_scan_outcome import FolderScanOutcome
from application.dto.scan_request import ScanRequest


class FileScanner(Protocol):
    """파일 스캐너 인터페이스.

    파일 시스템을 스캔하여 FileEntry 리스트를 반환하는 인터페이스.
    Infrastructure 계층에서 구현해야 함.
    """

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
            스캔된 FileEntry와 비치명적 오류(건너뛴 항목) 건수.
        """
        ...

    def cancel(self) -> None:
        """스캔 취소."""
        ...
