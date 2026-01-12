"""Blocking Service - 후보군 축소."""
from collections import defaultdict
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from domain.entities.file_entry import FileEntry
from domain.services.filename_parser import FilenameParser
from domain.value_objects.blocking_group import BlockingGroup
from domain.value_objects.filename_parse_result import FilenameParseResult

if TYPE_CHECKING:
    from application.ports.log_sink import ILogSink


class BlockingService:
    """Blocking Service - 후보군 축소 서비스.
    
    파일명 파싱 결과를 기반으로 파일들을 그룹화하여
    중복 탐지의 효율성을 높이는 서비스.
    """
    
    def __init__(
        self,
        filename_parser: Optional[FilenameParser] = None,
        log_sink: Optional["ILogSink"] = None
    ) -> None:
        """BlockingService 초기화.
        
        Args:
            filename_parser: 파일명 파서 (None이면 새로 생성).
            log_sink: 로그 싱크 (선택적, 디버깅 목적).
        """
        self._parser = filename_parser or FilenameParser()
        self._log_sink = log_sink
    
    def create_blocking_groups(
        self,
        files: list[tuple[FileEntry, FilenameParseResult]]
    ) -> list[BlockingGroup]:
        """Blocking Group 생성 (2-3단계 Blocking).
        
        Args:
            files: (FileEntry, FilenameParseResult) 튜플 리스트.
        
        Returns:
            BlockingGroup 리스트. 각 그룹은 같은 작품명과 확장자를 가진 파일들.
        
        Note:
            1차 Blocking: (extension, series_title_norm)
            2차 Blocking: range_start가 있으면 (extension, series_title_norm, range_start)로 세분화
            3차 Blocking: range_unit이 다르면 분리 (권 vs 화)
        """
        # 1차 그룹화: (extension, series_title_norm)
        # confidence가 낮은 파싱 결과는 blocking에서 제외 (폭증 방지)
        MIN_CONFIDENCE_FOR_BLOCKING = 0.7
        primary_groups: dict[tuple[str, str], list[tuple[FileEntry, FilenameParseResult]]] = defaultdict(list)
        
        for file_entry, parse_result in files:
            # confidence가 너무 낮으면 blocking에서 제외
            if parse_result.confidence < MIN_CONFIDENCE_FOR_BLOCKING:
                continue
            group_key = (file_entry.extension, parse_result.series_title_norm)
            primary_groups[group_key].append((file_entry, parse_result))
        
        blocking_groups = []
        
        # 각 1차 그룹 내에서 2-3차 세분화
        for (extension, series_title_norm), file_data in primary_groups.items():
            if len(file_data) < 2:
                # 파일이 1개면 BlockingGroup 생성하지 않음 (중복 가능성 없음)
                continue
            
            # 2차 그룹화: range_start가 있으면 세분화
            # range_start가 None인 항목은 containment/version 탐지에서 제외 (폭증 방지)
            secondary_groups: dict[Optional[int], list[tuple[FileEntry, FilenameParseResult]]] = defaultdict(list)
            
            for file_entry, parse_result in file_data:
                range_start = parse_result.range_start
                secondary_groups[range_start].append((file_entry, parse_result))
            
            # 각 2차 그룹 내에서 3차 세분화 (range_unit이 다르면 분리)
            for range_start, secondary_file_data in secondary_groups.items():
                # range_start가 None이면 containment/version 탐지에서 제외
                if range_start is None:
                    continue
                if len(secondary_file_data) < 2:
                    continue
                
                # 3차 그룹화: range_unit이 다르면 분리
                tertiary_groups: dict[Optional[str], list[tuple[FileEntry, FilenameParseResult]]] = defaultdict(list)
                
                for file_entry, parse_result in secondary_file_data:
                    range_unit = parse_result.range_unit
                    tertiary_groups[range_unit].append((file_entry, parse_result))
                
                # 각 3차 그룹을 BlockingGroup으로 생성
                for range_unit, tertiary_file_data in tertiary_groups.items():
                    if len(tertiary_file_data) < 2:
                        continue
                    
                    # file_id 추출 (file_id가 None인 파일은 제외)
                    file_ids = []
                    skipped_count = 0
                    for file_entry, _ in tertiary_file_data:
                        if file_entry.file_id is not None:
                            file_ids.append(file_entry.file_id)
                        else:
                            skipped_count += 1
                    
                    # file_id가 있는 파일이 2개 미만이면 BlockingGroup 생성하지 않음
                    if len(file_ids) < 2:
                        continue
                    
                    blocking_group = BlockingGroup(
                        series_title_norm=series_title_norm,
                        extension=extension,
                        file_ids=file_ids,
                        range_start=range_start
                    )
                    blocking_groups.append(blocking_group)
        
        return blocking_groups
