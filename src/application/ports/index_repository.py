"""인덱스 저장소 Port 인터페이스."""
from typing import Protocol, Optional

from application.dto.run_summary import RunSummary
from application.dto.scan_request import ScanRequest
from application.dto.ext_stat import ExtStat
from domain.entities.file_entry import FileEntry


class IIndexRepository(Protocol):
    """인덱스 저장소 인터페이스.
    
    스캔 결과를 영속화하고 조회하는 인터페이스.
    Infrastructure 계층에서 구현해야 함.
    """
    
    def start_run(self, request: ScanRequest) -> int:
        """Run 시작.
        
        Args:
            request: 스캔 요청 DTO.
        
        Returns:
            생성된 run_id.
        """
        ...
    
    def upsert_files(self, run_id: int, entries: list[FileEntry]) -> None:
        """파일 배치 저장 (upsert).
        
        Args:
            run_id: Run ID.
            entries: 파일 엔트리 리스트.
        """
        ...
    
    def finalize_run(self, run_id: int, summary: RunSummary) -> None:
        """Run 완료 처리.
        
        Args:
            run_id: Run ID.
            summary: Run 요약 정보.
        """
        ...
    
    def get_latest_run_id(self) -> Optional[int]:
        """최신 Run ID 반환.
        
        Returns:
            최신 Run ID. 없으면 None.
        """
        ...
    
    def get_run_summary(self, run_id: int) -> Optional[RunSummary]:
        """Run 요약 정보 조회.
        
        Args:
            run_id: Run ID.
        
        Returns:
            Run 요약 정보. 없으면 None.
        """
        ...
    
    def get_ext_distribution(self, run_id: int) -> list[ExtStat]:
        """확장자별 분포 집계.
        
        Args:
            run_id: Run ID.
        
        Returns:
            확장자별 통계 리스트.
        """
        ...
    
    def list_files(
        self,
        run_id: int,
        offset: int = 0,
        limit: int = 200,
        ext: Optional[str] = None,
        min_size: Optional[int] = None,
        max_size: Optional[int] = None,
        order_by: str = "path"
    ) -> list[FileEntry]:
        """파일 목록 조회 (페이지네이션).
        
        Args:
            run_id: Run ID.
            offset: 시작 오프셋 (기본값: 0).
            limit: 최대 개수 (기본값: 200).
            ext: 확장자 필터 (선택적).
            min_size: 최소 크기 필터 (선택적, 바이트).
            max_size: 최대 크기 필터 (선택적, 바이트).
            order_by: 정렬 기준 (기본값: "path", 허용: "path", "size_desc", "mtime_desc").
        
        Returns:
            파일 엔트리 리스트.
        """
        ...
    
    def close(self) -> None:
        """리소스 정리.
        
        DB 커넥션 등을 정리합니다.
        """
        ...
