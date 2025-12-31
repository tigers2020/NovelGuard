"""
파일 정리 결과 집계 모듈

파일 정리 작업의 결과를 집계하는 기능을 제공합니다.
"""

from pathlib import Path
from typing import Any

from utils.logger import get_logger


class OrganizationResultAggregator:
    """파일 정리 결과 집계 클래스.
    
    파일 정리 작업의 결과를 집계하여 딕셔너리 형태로 반환합니다.
    
    Attributes:
        _logger: 로거 인스턴스
    """
    
    def __init__(self) -> None:
        """OrganizationResultAggregator 초기화."""
        self._logger = get_logger("OrganizationResultAggregator")
    
    def create_empty_result(self) -> dict[str, Any]:
        """빈 결과 딕셔너리를 생성합니다.
        
        Returns:
            빈 결과 딕셔너리
        """
        return {
            "moved_count": 0,
            "failed_count": 0,
            "failed_files": [],
            "moved_files": []
        }
    
    def create_error_result(self, error_message: str) -> dict[str, Any]:
        """오류 결과 딕셔너리를 생성합니다.
        
        Args:
            error_message: 오류 메시지
        
        Returns:
            오류 결과 딕셔너리
        """
        result = self.create_empty_result()
        result["error"] = error_message
        return result
    
    def aggregate(
        self,
        moved_files: list[dict[str, str]],
        failed_files: list[Path]
    ) -> dict[str, Any]:
        """파일 정리 결과를 집계합니다.
        
        Args:
            moved_files: 이동된 파일 정보 리스트 (source, destination)
            failed_files: 이동 실패한 파일 경로 리스트
        
        Returns:
            집계된 결과 딕셔너리:
                - moved_count: 이동된 파일 수
                - failed_count: 이동 실패한 파일 수
                - failed_files: 이동 실패한 파일 경로 리스트 (문자열)
                - moved_files: 이동된 파일 정보 리스트
        """
        moved_count = len(moved_files)
        failed_count = len(failed_files)
        
        result = {
            "moved_count": moved_count,
            "failed_count": failed_count,
            "failed_files": [str(f) for f in failed_files],
            "moved_files": moved_files
        }
        
        self._logger.info(
            f"결과 집계 완료: {moved_count}개 이동, {failed_count}개 실패"
        )
        
        return result

