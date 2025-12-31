"""
경로 해결 모듈

경로 충돌을 처리하고 안전한 경로를 생성하는 기능을 제공합니다.
"""

from pathlib import Path

from utils.logger import get_logger


class PathResolver:
    """경로 해결 클래스.
    
    경로 충돌을 처리하고 안전한 경로를 생성하는 기능을 제공합니다.
    
    Attributes:
        _logger: 로거 인스턴스
    """
    
    def __init__(self) -> None:
        """PathResolver 초기화."""
        self._logger = get_logger("PathResolver")
    
    def resolve_conflict(self, destination: Path) -> Path:
        """경로 충돌을 해결하여 안전한 경로를 반환합니다.
        
        대상 경로가 이미 존재하는 경우 파일명에 번호를 추가하여
        충돌을 피합니다.
        
        Args:
            destination: 원하는 대상 경로
        
        Returns:
            충돌이 없는 안전한 경로
        """
        if not destination.exists():
            return destination
        
        # 경로 충돌 발생 - 번호 추가
        base_name = destination.stem
        extension = destination.suffix
        parent = destination.parent
        counter = 1
        
        while destination.exists():
            new_name = f"{base_name}_{counter}{extension}"
            destination = parent / new_name
            counter += 1
        
        self._logger.warning(
            f"대상 경로 충돌: 경로 변경됨 - {destination}"
        )
        
        return destination
    
    def create_old_versions_folder(self, root_folder: Path, folder_name: str = "old_versions") -> Path:
        """old_versions 폴더를 생성합니다.
        
        Args:
            root_folder: 루트 폴더 경로
            folder_name: 생성할 폴더 이름 (기본값: "old_versions")
        
        Returns:
            생성된 old_versions 폴더 경로
        
        Raises:
            OSError: 폴더 생성 실패 시
        """
        old_versions_folder = root_folder / folder_name
        try:
            old_versions_folder.mkdir(exist_ok=True)
            self._logger.info(f"old_versions 폴더 생성/확인: {old_versions_folder}")
            return old_versions_folder
        except OSError as e:
            self._logger.error(f"old_versions 폴더 생성 실패: {e}", exc_info=True)
            raise
    
    def resolve_destination_path(
        self,
        source_path: Path,
        root_folder: Path,
        destination_folder: Path
    ) -> Path:
        """소스 파일의 목적지 경로를 생성합니다.
        
        상대 경로를 유지하여 목적지 폴더 내에 동일한 구조로 배치합니다.
        
        Args:
            source_path: 소스 파일 경로
            root_folder: 루트 폴더 경로 (상대 경로 계산 기준)
            destination_folder: 목적지 폴더 경로
        
        Returns:
            생성된 목적지 경로
        """
        # 상대 경로 유지 (루트 폴더 기준)
        relative_path = source_path.relative_to(root_folder)
        destination = destination_folder / relative_path
        return destination

