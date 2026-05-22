"""Job Runner Port 인터페이스."""

from typing import Callable, Optional, Protocol

from application.dto.duplicate_detection_request import DuplicateDetectionRequest
from application.dto.integrity_check_request import IntegrityCheckRequest
from application.dto.job_types import JobEvent, JobStatus
from application.dto.scan_request import ScanRequest
from application.dto.utf8_convert_request import Utf8ConvertRequest


class IJobRunner(Protocol):
    """Job Runner 인터페이스.

    작업 실행을 표준화하는 인터페이스.
    Application 레이어는 Qt를 모르므로, 순수 callback/event dispatcher 형태.
    GUI는 ``subscribe(JobEvent)``로 진행/완료 등을 구독한다.
    """

    def start_scan(self, request: ScanRequest) -> int:
        """스캔 작업 시작.

        Args:
            request: 스캔 요청 DTO.

        Returns:
            Job ID.
        """
        ...

    def start_integrity_check(self, request: IntegrityCheckRequest) -> int:
        """무결성 검사 작업 시작."""
        ...

    def start_utf8_convert(self, request: Utf8ConvertRequest) -> int:
        """UTF-8 변환 작업 시작."""
        ...

    def start_duplicate_detection(self, request: DuplicateDetectionRequest) -> int:
        """중복 탐지 작업 시작.

        Args:
            request: 중복 탐지 요청 DTO.

        Returns:
            Job ID.
        """
        ...

    def cancel(self, job_id: int) -> None:
        """작업 취소.

        Args:
            job_id: Job ID.
        """
        ...

    def get_status(self, job_id: int) -> Optional[JobStatus]:
        """작업 상태 조회.

        Args:
            job_id: Job ID.

        Returns:
            Job 상태. 없으면 None.
        """
        ...

    def subscribe(self, listener: Callable[[JobEvent], None]) -> None:
        """이벤트 리스너 등록.

        Args:
            listener: 이벤트 리스너 함수.
        """
        ...
