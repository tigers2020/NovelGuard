"""
스캔 결과 관리 모듈

스캔 결과를 관리하고 JSON 파일로 저장하는 기능을 제공합니다.
"""

from pathlib import Path
from typing import Optional
from datetime import datetime
import json

from models.file_record import FileRecord
from utils.logger import get_logger
from utils.constants import DEFAULT_ENCODING, JSON_INDENT


class ScanResultManager:
    """스캔 결과 관리 클래스.
    
    스캔 결과를 관리하고 JSON 파일로 저장하는 기능을 제공합니다.
    
    Attributes:
        _logger: 로거 인스턴스
        _scanned_files: 스캔된 파일 리스트
        _folder_path: 스캔한 폴더 경로
    """
    
    def __init__(self) -> None:
        """ScanResultManager 초기화."""
        self._logger = get_logger("ScanResultManager")
        self._scanned_files: list[FileRecord] = []
        self._folder_path: Optional[Path] = None
    
    def set_scan_results(
        self,
        scanned_files: list[FileRecord],
        folder_path: Optional[Path] = None
    ) -> None:
        """스캔 결과를 설정합니다.
        
        Args:
            scanned_files: 스캔된 파일 리스트
            folder_path: 스캔한 폴더 경로 (선택적)
        """
        self._scanned_files = scanned_files
        self._folder_path = folder_path
    
    def get_scanned_files(self) -> list[FileRecord]:
        """스캔된 파일 리스트를 반환합니다.
        
        Returns:
            스캔된 파일 리스트
        """
        return self._scanned_files
    
    def clear(self) -> None:
        """스캔 결과를 초기화합니다."""
        self._scanned_files = []
        self._folder_path = None
    
    def save_to_json(self) -> Optional[str]:
        """스캔 결과를 JSON 파일로 저장합니다.
        
        SAVE 폴더에 타임스탬프가 포함된 파일명으로 저장합니다.
        FileRecord는 Pydantic 모델이므로 model_dump()를 사용하여 딕셔너리로 변환합니다.
        
        Returns:
            저장된 JSON 파일명. 저장 실패 시 None.
        """
        if not self._scanned_files:
            self._logger.warning("저장할 스캔 결과가 없습니다.")
            return None
        
        try:
            # SAVE 폴더 생성 (프로젝트 루트 기준)
            project_root = Path(__file__).parent.parent.parent.parent
            save_dir = project_root / "SAVE"
            save_dir.mkdir(exist_ok=True)
            
            # 타임스탬프 포함 파일명 생성
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            json_filename = f"scan_results_{timestamp}.json"
            json_path = save_dir / json_filename
            
            # FileRecord 리스트를 딕셔너리 리스트로 변환
            # Path 객체는 문자열로 변환하고, episode_range 튜플은 리스트로 변환
            records_data = []
            for record in self._scanned_files:
                record_dict = record.model_dump()
                # Path 객체를 문자열로 변환
                record_dict["path"] = str(record_dict["path"])
                # episode_range 튜플을 리스트로 변환 (JSON 호환)
                if record_dict.get("episode_range") is not None:
                    record_dict["episode_range"] = list(record_dict["episode_range"])
                records_data.append(record_dict)
            
            # 메타데이터 포함 JSON 구조
            json_data = {
                "scan_info": {
                    "scan_time": datetime.now().isoformat(),
                    "folder_path": str(self._folder_path) if self._folder_path else None,
                    "total_files": len(self._scanned_files),
                },
                "files": records_data
            }
            
            # JSON 파일로 저장 (UTF-8 인코딩, 들여쓰기 포함)
            with open(json_path, "w", encoding=DEFAULT_ENCODING) as f:
                json.dump(json_data, f, ensure_ascii=False, indent=JSON_INDENT)
            
            self._logger.info(f"스캔 결과 JSON 저장 완료: {json_path}")
            return json_filename
            
        except Exception as e:
            self._logger.error(f"스캔 결과 JSON 저장 중 오류: {e}", exc_info=True)
            return None

