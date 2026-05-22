"""Blocking Service - 후보군 축소."""

from collections import defaultdict
from typing import Optional

from domain.entities.file_entry import FileEntry
from domain.services.filename_parser import FilenameParser
from domain.value_objects.blocking_group import BlockingGroup
from domain.value_objects.filename_parse_result import FilenameParseResult

_FileParsePair = tuple[FileEntry, FilenameParseResult]


class BlockingService:
    """Blocking Service - 후보군 축소 서비스.

    파일명 파싱 결과를 기반으로 파일들을 그룹화하여
    중복 탐지의 효율성을 높이는 서비스.
    """

    def __init__(self, filename_parser: Optional[FilenameParser] = None) -> None:
        """BlockingService 초기화.

        Args:
            filename_parser: 파일명 파서 (None이면 새로 생성).
        """
        self._parser = filename_parser or FilenameParser()

    def create_blocking_groups(
        self,
        files: list[_FileParsePair],
        min_confidence: float = 0.7,
    ) -> list[BlockingGroup]:
        """Blocking Group 생성 (2-3단계 Blocking).

        Args:
            files: (FileEntry, FilenameParseResult) 튜플 리스트.
            min_confidence: 이 값 미만의 파싱 confidence는 blocking에서 제외. 기본 0.7.

        Returns:
            BlockingGroup 리스트. 각 그룹은 같은 작품명과 확장자를 가진 파일들.

        Note:
            1차 Blocking: (extension, series_title_norm)
            2차 Blocking: range_start가 있으면 (extension, series_title_norm, range_start)로 세분화
            3차 Blocking: range_unit이 다르면 분리 (권 vs 화)
        """
        primary_groups = self._build_primary_groups(files, min_confidence)
        blocking_groups: list[BlockingGroup] = []

        for (extension, series_title_norm), file_data in primary_groups.items():
            if len(file_data) < 2:
                continue
            secondary_groups = self._group_by_range_start(file_data)
            for range_start, secondary_file_data in secondary_groups.items():
                self._process_secondary_group(
                    blocking_groups,
                    extension,
                    series_title_norm,
                    range_start,
                    secondary_file_data,
                )

        return blocking_groups

    def _build_primary_groups(
        self,
        files: list[_FileParsePair],
        min_confidence: float,
    ) -> dict[tuple[str, str], list[_FileParsePair]]:
        primary_groups: dict[tuple[str, str], list[_FileParsePair]] = defaultdict(list)
        for file_entry, parse_result in files:
            if parse_result.confidence < min_confidence:
                continue
            group_key = (file_entry.extension, parse_result.series_title_norm)
            primary_groups[group_key].append((file_entry, parse_result))
        return primary_groups

    def _group_by_range_start(
        self,
        file_data: list[_FileParsePair],
    ) -> dict[Optional[int], list[_FileParsePair]]:
        secondary_groups: dict[Optional[int], list[_FileParsePair]] = defaultdict(list)
        for file_entry, parse_result in file_data:
            secondary_groups[parse_result.range_start].append((file_entry, parse_result))
        return secondary_groups

    def _process_secondary_group(
        self,
        blocking_groups: list[BlockingGroup],
        extension: str,
        series_title_norm: str,
        range_start: Optional[int],
        secondary_file_data: list[_FileParsePair],
    ) -> None:
        if range_start is None or len(secondary_file_data) < 2:
            return

        tertiary_groups: dict[Optional[str], list[_FileParsePair]] = defaultdict(list)
        for file_entry, parse_result in secondary_file_data:
            tertiary_groups[parse_result.range_unit].append((file_entry, parse_result))

        for tertiary_file_data in tertiary_groups.values():
            self._maybe_append_blocking_group(
                blocking_groups,
                extension,
                series_title_norm,
                range_start,
                tertiary_file_data,
            )

    def _maybe_append_blocking_group(
        self,
        blocking_groups: list[BlockingGroup],
        extension: str,
        series_title_norm: str,
        range_start: int,
        tertiary_file_data: list[_FileParsePair],
    ) -> None:
        if len(tertiary_file_data) < 2:
            return
        file_ids = [fe.file_id for fe, _ in tertiary_file_data if fe.file_id is not None]
        if len(file_ids) < 2:
            return
        blocking_groups.append(
            BlockingGroup(
                series_title_norm=series_title_norm,
                extension=extension,
                file_ids=file_ids,
                range_start=range_start,
            )
        )
