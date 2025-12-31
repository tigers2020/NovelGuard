"""
파일 정리 유틸리티 모듈

중복 파일을 정리하는 기능을 제공합니다.
"""

from pathlib import Path
from typing import Optional, Any
import logging

from models.file_record import FileRecord
from analyzers.duplicate_group import DuplicateGroup
from utils.logger import get_logger
from utils.file_mover import FileMover
from utils.path_resolver import PathResolver
from utils.organization_result_aggregator import OrganizationResultAggregator


class FileOrganizer:
    """파일 정리 클래스.
    
    중복 파일을 old_versions 폴더로 이동시키는 기능을 제공합니다.
    
    Attributes:
        _logger: 로거 인스턴스
        _old_versions_folder: old_versions 폴더 경로
    """
    
    OLD_VERSIONS_FOLDER_NAME = "old_versions"
    
    def __init__(self, root_folder: Path) -> None:
        """FileOrganizer 초기화.
        
        Args:
            root_folder: 파일 정리를 수행할 루트 폴더 경로
        """
        self._logger = get_logger("FileOrganizer")
        self._root_folder = root_folder
        
        # 분리된 책임 클래스들 초기화
        self._mover = FileMover()
        self._path_resolver = PathResolver()
        self._result_aggregator = OrganizationResultAggregator()
    
    def move_file_safely(self, source: Path, destination: Path, dry_run: bool = False) -> bool:
        """파일을 안전하게 이동합니다.
        
        경로 충돌이 발생하면 파일명에 번호를 추가하여 처리합니다.
        
        Args:
            source: 이동할 원본 파일 경로
            destination: 이동할 대상 경로
            dry_run: True이면 실제 이동 없이 시뮬레이션만 수행
        
        Returns:
            이동 성공 여부 (dry_run이면 항상 True)
        
        Raises:
            FileNotFoundError: 원본 파일이 없을 때
            OSError: 파일 이동 실패 시
        """
        # 경로 충돌 해결
        safe_destination = self._path_resolver.resolve_conflict(destination)
        
        # 파일 이동
        return self._mover.move(source, safe_destination, dry_run=dry_run)
    
    def organize_duplicates(
        self,
        duplicate_groups: list[DuplicateGroup],
        dry_run: bool = False
    ) -> dict[str, Any]:
        """중복 파일을 정리합니다.
        
        각 그룹에서 keep_file은 유지하고, 나머지는 old_versions 폴더로 이동시킵니다.
        
        Args:
            duplicate_groups: 중복 그룹 리스트
            dry_run: True이면 실제 이동 없이 시뮬레이션만 수행
        
        Returns:
            정리 결과 딕셔너리:
                - moved_count: 이동된 파일 수
                - failed_count: 이동 실패한 파일 수
                - failed_files: 이동 실패한 파일 경로 리스트
                - moved_files: 이동된 파일 정보 리스트 (source, destination)
        """
        if not duplicate_groups:
            self._logger.info("정리할 중복 그룹이 없습니다.")
            return self._result_aggregator.create_empty_result()
        
        # old_versions 폴더 생성 (dry_run이 아니면)
        old_versions_folder: Optional[Path] = None
        if not dry_run:
            try:
                old_versions_folder = self._path_resolver.create_old_versions_folder(
                    self._root_folder, self.OLD_VERSIONS_FOLDER_NAME
                )
            except OSError as e:
                self._logger.error(f"old_versions 폴더 생성 실패: {e}")
                return self._result_aggregator.create_error_result(f"폴더 생성 실패: {e}")
        
        moved_count = 0
        failed_count = 0
        failed_files: list[Path] = []
        moved_files: list[dict[str, str]] = []
        
        for group_idx, group in enumerate(duplicate_groups, 1):
            if not group.keep_file:
                self._logger.warning(f"그룹 {group_idx}: keep_file이 없어 스킵합니다.")
                continue
            
            keep_file = group.keep_file
            duplicates = [f for f in group.members if f != keep_file]
            
            if not duplicates:
                self._logger.debug(f"그룹 {group_idx}: 이동할 중복 파일이 없습니다.")
                continue
            
            self._logger.debug(
                f"그룹 {group_idx}: keep_file={keep_file.name}, "
                f"duplicates={len(duplicates)}개"
            )
            
            # 각 중복 파일을 old_versions 폴더로 이동
            for duplicate in duplicates:
                try:
                    # 목적지 경로 생성 (PathResolver 사용)
                    if old_versions_folder:
                        destination = self._path_resolver.resolve_destination_path(
                            duplicate.path,
                            self._root_folder,
                            old_versions_folder
                        )
                    else:
                        # dry_run 모드: 임시 경로 생성
                        destination = self._path_resolver.resolve_destination_path(
                            duplicate.path,
                            self._root_folder,
                            self._root_folder / self.OLD_VERSIONS_FOLDER_NAME
                        )
                    
                    # 파일 이동
                    success = self.move_file_safely(
                        duplicate.path,
                        destination,
                        dry_run=dry_run
                    )
                    
                    if success:
                        moved_count += 1
                        moved_files.append({
                            "source": str(duplicate.path),
                            "destination": str(destination)
                        })
                        
                except Exception as e:
                    failed_count += 1
                    failed_files.append(duplicate.path)
                    self._logger.error(
                        f"파일 이동 실패: {duplicate.path}, 오류: {e}",
                        exc_info=True
                    )
        
        # 결과 집계
        result = self._result_aggregator.aggregate(moved_files, failed_files)
        
        self._logger.info(
            f"파일 정리 완료: {result['moved_count']}개 이동, {result['failed_count']}개 실패"
        )
        
        return result

