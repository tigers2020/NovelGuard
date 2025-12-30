"""
파일 정리 유틸리티 모듈

중복 파일을 정리하는 기능을 제공합니다.
"""

from pathlib import Path
from typing import Optional, Any
import shutil
import logging

from models.file_record import FileRecord
from analyzers.duplicate_group import DuplicateGroup
from utils.logger import get_logger


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
        self._old_versions_folder = root_folder / self.OLD_VERSIONS_FOLDER_NAME
    
    def create_old_versions_folder(self) -> Path:
        """old_versions 폴더를 생성합니다.
        
        Returns:
            생성된 old_versions 폴더 경로
        
        Raises:
            OSError: 폴더 생성 실패 시
        """
        try:
            self._old_versions_folder.mkdir(exist_ok=True)
            self._logger.info(f"old_versions 폴더 생성/확인: {self._old_versions_folder}")
            return self._old_versions_folder
        except OSError as e:
            self._logger.error(f"old_versions 폴더 생성 실패: {e}", exc_info=True)
            raise
    
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
        if not source.exists():
            error_msg = f"원본 파일이 없습니다: {source}"
            self._logger.error(error_msg)
            raise FileNotFoundError(error_msg)
        
        if dry_run:
            self._logger.debug(f"[DRY-RUN] 파일 이동 시뮬레이션: {source} -> {destination}")
            return True
        
        # 대상 경로가 이미 존재하는 경우 번호 추가
        if destination.exists():
            base_name = destination.stem
            extension = destination.suffix
            parent = destination.parent
            counter = 1
            
            while destination.exists():
                new_name = f"{base_name}_{counter}{extension}"
                destination = parent / new_name
                counter += 1
            
            self._logger.warning(
                f"대상 경로 충돌: 원본 경로로 변경됨 - {destination}"
            )
        
        try:
            # 부모 디렉토리 생성 (필요한 경우)
            destination.parent.mkdir(parents=True, exist_ok=True)
            
            # 파일 이동
            shutil.move(str(source), str(destination))
            self._logger.info(f"파일 이동 완료: {source} -> {destination}")
            return True
            
        except OSError as e:
            error_msg = f"파일 이동 실패: {source} -> {destination}, 오류: {e}"
            self._logger.error(error_msg, exc_info=True)
            raise
    
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
            return {
                "moved_count": 0,
                "failed_count": 0,
                "failed_files": [],
                "moved_files": []
            }
        
        # old_versions 폴더 생성 (dry_run이 아니면)
        if not dry_run:
            try:
                self.create_old_versions_folder()
            except OSError as e:
                self._logger.error(f"old_versions 폴더 생성 실패: {e}")
                return {
                    "moved_count": 0,
                    "failed_count": 0,
                    "failed_files": [],
                    "moved_files": [],
                    "error": f"폴더 생성 실패: {e}"
                }
        
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
                    # 상대 경로 유지 (루트 폴더 기준)
                    relative_path = duplicate.path.relative_to(self._root_folder)
                    destination = self._old_versions_folder / relative_path
                    
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
        
        result = {
            "moved_count": moved_count,
            "failed_count": failed_count,
            "failed_files": [str(f) for f in failed_files],
            "moved_files": moved_files
        }
        
        self._logger.info(
            f"파일 정리 완료: {moved_count}개 이동, {failed_count}개 실패"
        )
        
        return result

