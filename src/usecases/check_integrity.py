"""무결성 검사 유스케이스."""

from typing import Callable, Optional
from infra.db.file_repository import FileRepository
from infra.encoding.encoding_detector import EncodingDetector
from domain.models.integrity_issue import IntegrityIssue
from common.logging import setup_logging

logger = setup_logging()


class CheckIntegrityUseCase:
    """무결성 검사 유스케이스."""
    
    def __init__(
        self,
        repository: FileRepository,
        encoding_detector: Optional[EncodingDetector] = None
    ) -> None:
        """유스케이스 초기화.
        
        Args:
            repository: FileRepository
            encoding_detector: EncodingDetector (None이면 기본값)
        """
        self.repository = repository
        self.encoding_detector = encoding_detector or EncodingDetector()
    
    def execute(
        self,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> list[IntegrityIssue]:
        """무결성 검사 실행.
        
        Args:
            progress_callback: 진행 상황 콜백
        
        Returns:
            IntegrityIssue 리스트
        """
        issues = []
        records = list(self.repository.list_all())
        issue_id = 1
        
        for idx, record in enumerate(records):
            if progress_callback:
                progress_callback(idx + 1, len(records))
            
            # 인코딩 검사
            if record.is_text:
                if not record.encoding_detected:
                    issue = IntegrityIssue(
                        issue_id=issue_id,
                        file_id=record.file_id,
                        severity="WARN",
                        category="ENCODING",
                        message="인코딩 감지 실패",
                        fixable=False
                    )
                    issues.append(issue)
                    issue_id += 1
                elif record.encoding_confidence and record.encoding_confidence < 0.7:
                    issue = IntegrityIssue(
                        issue_id=issue_id,
                        file_id=record.file_id,
                        severity="WARN",
                        category="ENCODING",
                        message=f"인코딩 감지 신뢰도 낮음: {record.encoding_detected} ({record.encoding_confidence:.2f})",
                        metrics={"confidence": record.encoding_confidence},
                        fixable=False
                    )
                    issues.append(issue)
                    issue_id += 1
            
            # 빈 파일 검사
            if record.size == 0:
                issue = IntegrityIssue(
                    issue_id=issue_id,
                    file_id=record.file_id,
                    severity="INFO",
                    category="TOO_SHORT",
                    message="빈 파일",
                    fixable=True,
                    suggested_fix="DELETE"
                )
                issues.append(issue)
                issue_id += 1
        
        return issues

