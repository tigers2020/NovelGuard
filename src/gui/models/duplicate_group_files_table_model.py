"""중복 그룹 파일 테이블 모델."""
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, TYPE_CHECKING

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt

from application.dto.duplicate_group_result import DuplicateGroupResult

if TYPE_CHECKING:
    from gui.models.file_data_store import FileDataStore


@dataclass
class FileInfo:
    """파일 정보 (Phase A: DuplicateGroupResult 기반)."""
    file_id: int
    path: Path
    size: Optional[int] = None
    mtime: Optional[datetime] = None
    range_str: Optional[str] = None


class DuplicateGroupFilesTableModel(QAbstractTableModel):
    """중복 그룹 파일 테이블 모델.
    
    FileDataStore를 단일 데이터 소스로 사용.
    evidence는 range_str 추출용으로만 사용 (fallback).
    """
    
    # 컬럼 인덱스
    COL_KEEP = 0
    COL_NAME = 1
    COL_PATH = 2
    COL_RANGE = 3
    COL_SIZE = 4
    COL_MODIFIED = 5
    
    def __init__(self, parent=None, file_data_store: "FileDataStore" = None) -> None:
        """중복 그룹 파일 테이블 모델 초기화.
        
        Args:
            parent: 부모 객체.
            file_data_store: 파일 데이터 저장소 (필수).
        """
        super().__init__(parent)
        if file_data_store is None:
            raise ValueError("file_data_store is required")
        self._group_result: Optional[DuplicateGroupResult] = None
        self._file_info_list: list[FileInfo] = []
        self._file_data_store = file_data_store
    
    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """행 수 반환."""
        return len(self._file_info_list)
    
    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """컬럼 수 반환."""
        return 6
    
    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:
        """데이터 반환."""
        if not index.isValid() or index.row() >= len(self._file_info_list):
            return None
        
        file_info = self._file_info_list[index.row()]
        column = index.column()
        
        if role == Qt.DisplayRole:
            if column == self.COL_KEEP:
                if self._group_result and self._group_result.recommended_keeper_id == file_info.file_id:
                    return "★"
                return "-"
            elif column == self.COL_NAME:
                return file_info.path.name
            elif column == self.COL_PATH:
                return str(file_info.path)
            elif column == self.COL_RANGE:
                return file_info.range_str or "—"
            elif column == self.COL_SIZE:
                if file_info.size is not None:
                    return self._format_size(file_info.size)
                return "—"
            elif column == self.COL_MODIFIED:
                if file_info.mtime:
                    return self._format_datetime(file_info.mtime)
                return "—"
        elif role == Qt.UserRole:
            # 정렬을 위한 원본 데이터
            if column == self.COL_KEEP:
                return self._group_result.recommended_keeper_id == file_info.file_id if self._group_result else False
            elif column == self.COL_NAME:
                return file_info.path.name
            elif column == self.COL_PATH:
                return str(file_info.path)
            elif column == self.COL_SIZE:
                return file_info.size if file_info.size is not None else 0
            elif column == self.COL_MODIFIED:
                return file_info.mtime.timestamp() if file_info.mtime else 0
        
        return None
    
    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole) -> Any:
        """헤더 데이터 반환."""
        if role != Qt.DisplayRole:
            return None
        
        if orientation == Qt.Horizontal:
            headers = [
                "Keeper",
                "파일명",
                "경로",
                "범위",
                "크기",
                "수정일"
            ]
            if 0 <= section < len(headers):
                return headers[section]
        
        return None
    
    def set_group(self, result: DuplicateGroupResult) -> None:
        """그룹 설정.
        
        FileDataStore에서 파일 정보를 가져옵니다.
        evidence는 range_str 추출용으로만 사용 (fallback).
        
        Args:
            result: 중복 그룹 결과.
        """
        self.beginResetModel()
        self._group_result = result
        
        # file_ids 기반으로 FileInfo 생성 (FileDataStore에서 정보 가져오기)
        file_info_list: list[FileInfo] = []
        evidence = result.evidence or {}
        files_info = evidence.get("files", {})  # evidence.files[file_id] 형태 (range_str 추출용)
        
        for file_id in result.file_ids:
            # FileDataStore에서 파일 정보 가져오기
            file_data = None
            if self._file_data_store:
                file_data = self._file_data_store.get_file(file_id)
            
            path = None
            size = None
            mtime = None
            range_str = None
            
            if file_data:
                # FileDataStore에서 직접 가져오기
                path = file_data.path
                size = file_data.size
                mtime = file_data.mtime
            else:
                # FileDataStore에 없는 경우만 evidence fallback (예외 처리)
                evidence_file_data = files_info.get(str(file_id)) or files_info.get(file_id)
                if evidence_file_data:
                    if "path" in evidence_file_data:
                        path = Path(evidence_file_data["path"])
                    elif "filename" in evidence_file_data:
                        path = Path(evidence_file_data["filename"])
                    
                    size = evidence_file_data.get("size")
                    if "mtime" in evidence_file_data:
                        mtime_val = evidence_file_data["mtime"]
                        if isinstance(mtime_val, (int, float)):
                            mtime = datetime.fromtimestamp(mtime_val)
                        elif isinstance(mtime_val, str):
                            try:
                                mtime = datetime.fromisoformat(mtime_val.replace("Z", "+00:00"))
                            except:
                                pass
            
            # range_str은 evidence에서만 추출 (파일명 파싱 결과)
            evidence_file_data = files_info.get(str(file_id)) or files_info.get(file_id)
            if evidence_file_data:
                range_str = evidence_file_data.get("range") or evidence_file_data.get("range_str")
            
            # path가 없으면 file_id 기반 임시 경로
            if path is None:
                path = Path(f"file_id_{file_id}")
            
            file_info = FileInfo(
                file_id=file_id,
                path=path,
                size=size,
                mtime=mtime,
                range_str=range_str
            )
            file_info_list.append(file_info)
        
        # keeper를 맨 앞으로 정렬
        if result.recommended_keeper_id:
            file_info_list.sort(key=lambda fi: fi.file_id != result.recommended_keeper_id)
        
        self._file_info_list = file_info_list
        self.endResetModel()
    
    def get_file_info(self, row: int) -> Optional[FileInfo]:
        """행에 해당하는 파일 정보 반환."""
        if 0 <= row < len(self._file_info_list):
            return self._file_info_list[row]
        return None
    
    def clear(self) -> None:
        """테이블 초기화."""
        self.beginResetModel()
        self._group_result = None
        self._file_info_list = []
        self.endResetModel()
    
    def _format_size(self, size_bytes: int) -> str:
        """파일 크기 포맷팅."""
        from app.settings.constants import Constants
        
        if size_bytes < Constants.BYTES_PER_KB:
            return f"{size_bytes} B"
        elif size_bytes < Constants.BYTES_PER_MB:
            return f"{size_bytes / Constants.BYTES_PER_KB:.1f} KB"
        elif size_bytes < Constants.BYTES_PER_GB:
            return f"{size_bytes / Constants.BYTES_PER_MB:.1f} MB"
        else:
            return f"{size_bytes / Constants.BYTES_PER_GB:.1f} GB"
    
    def _format_datetime(self, dt: datetime) -> str:
        """날짜/시간 포맷팅."""
        return dt.strftime("%Y-%m-%d %H:%M")
