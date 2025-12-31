"""
파일 그룹핑 모듈

base_title 또는 head anchor를 기반으로 파일을 그룹으로 묶는 기능을 제공합니다.
"""

from typing import Optional, Callable
from collections import defaultdict

from models.file_record import FileRecord
from utils.logger import get_logger
from analyzers.anchor_hash_computer import AnchorHashComputer


class FileGrouper:
    """파일 그룹핑 클래스.
    
    base_title이 있으면 base_title로 그룹핑,
    base_title이 없으면 head anchor로 버킷팅합니다.
    앵커 해시 계산은 병렬 처리로 성능을 최적화합니다.
    
    Attributes:
        _logger: 로거 인스턴스
        _progress_callback: 진행 상황 업데이트 콜백 함수 (선택적)
    """
    
    def __init__(self, progress_callback: Optional[Callable[[str], None]] = None) -> None:
        """FileGrouper 초기화.
        
        Args:
            progress_callback: 진행 상황 업데이트 콜백 함수 (message: str) -> None
        """
        self._logger = get_logger("FileGrouper")
        self._progress_callback = progress_callback
        self._anchor_hash_computer = AnchorHashComputer(progress_callback=progress_callback)
    
    def _update_progress(self, message: str) -> None:
        """진행 상황을 업데이트합니다.
        
        Args:
            message: 진행 상황 메시지
        """
        if self._progress_callback:
            self._progress_callback(message)
        self._logger.debug(message)
    
    def group_files(self, records: list[FileRecord]) -> list[list[FileRecord]]:
        """파일을 그룹으로 묶습니다.
        
        base_title이 있으면 base_title로 그룹핑,
        base_title이 없으면 head anchor로 버킷팅합니다.
        앵커 해시 계산은 병렬 처리로 성능을 최적화합니다.
        
        Args:
            records: FileRecord 리스트
        
        Returns:
            그룹 리스트 (각 그룹은 FileRecord 리스트)
        """
        # 앵커 해시 계산 (병렬 처리)
        records_with_hashes = self._anchor_hash_computer.compute_hashes(records)
        
        # base_title 기준 그룹핑
        base_title_groups: dict[str, list[FileRecord]] = defaultdict(list)
        no_base_title_records: list[FileRecord] = []
        
        for record in records_with_hashes:
            if record.base_title:
                base_title_groups[record.base_title].append(record)
            else:
                no_base_title_records.append(record)
        
        groups: list[list[FileRecord]] = []
        
        # base_title 그룹 추가
        for base_title, group_records in base_title_groups.items():
            if len(group_records) >= 2:
                groups.append(group_records)
                self._logger.debug(
                    f"base_title 그룹: '{base_title}', {len(group_records)}개 파일"
                )
        
        # base_title 없는 파일들은 head anchor로 버킷팅
        if no_base_title_records:
            head_buckets: dict[str, list[FileRecord]] = defaultdict(list)
            for record in no_base_title_records:
                if record.anchor_hashes:
                    head_hash = record.anchor_hashes.get("head", "")
                    if head_hash:
                        head_buckets[head_hash].append(record)
            
            # 버킷 크기 ≥ 2인 것만 그룹으로 추가
            for head_hash, bucket_records in head_buckets.items():
                if len(bucket_records) >= 2:
                    groups.append(bucket_records)
                    self._logger.debug(
                        f"head anchor 버킷: {len(bucket_records)}개 파일"
                    )
        
        self._logger.debug(f"총 {len(groups)}개 그룹 생성")
        return groups

