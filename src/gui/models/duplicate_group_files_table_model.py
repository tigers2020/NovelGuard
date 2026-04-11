"""중복 그룹 파일 테이블 모델."""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

from PySide6.QtCore import (
    QAbstractTableModel,
    QModelIndex,
    QPersistentModelIndex,
    Qt,
)

from application.dto.duplicate_group_result import DuplicateGroupResult

if TYPE_CHECKING:
    from gui.models.file_data_store import FileData, FileDataStore


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

    def __init__(self, parent=None, *, file_data_store: "FileDataStore") -> None:
        """중복 그룹 파일 테이블 모델 초기화.

        Args:
            parent: 부모 객체.
            file_data_store: 파일 데이터 저장소 (필수).
        """
        super().__init__(parent)
        self._group_result: Optional[DuplicateGroupResult] = None
        self._file_info_list: list[FileInfo] = []
        self._file_data_store: "FileDataStore" = file_data_store

    def rowCount(self, parent: QModelIndex | QPersistentModelIndex = QModelIndex()) -> int:
        """행 수 반환."""
        return len(self._file_info_list)

    def columnCount(self, parent: QModelIndex | QPersistentModelIndex = QModelIndex()) -> int:
        """컬럼 수 반환."""
        return 6

    def data(
        self,
        index: QModelIndex | QPersistentModelIndex,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        """데이터 반환."""
        if not index.isValid() or index.row() >= len(self._file_info_list):
            return None

        file_info = self._file_info_list[index.row()]
        column = index.column()

        if role == Qt.ItemDataRole.DisplayRole:
            return self._display_cell_value(file_info, column)
        if role == Qt.ItemDataRole.UserRole:
            return self._user_role_cell_value(file_info, column)
        return None

    def _is_recommended_keeper(self, file_id: int) -> bool:
        return bool(self._group_result and self._group_result.recommended_keeper_id == file_id)

    def _display_cell_value(self, file_info: FileInfo, column: int) -> Any:
        if column == self.COL_KEEP:
            return "★" if self._is_recommended_keeper(file_info.file_id) else "-"
        if column == self.COL_NAME:
            return file_info.path.name
        if column == self.COL_PATH:
            return str(file_info.path)
        if column == self.COL_RANGE:
            return file_info.range_str or "—"
        if column == self.COL_SIZE:
            return self._format_size(file_info.size) if file_info.size is not None else "—"
        if column == self.COL_MODIFIED:
            return self._format_datetime(file_info.mtime) if file_info.mtime else "—"
        return None

    def _user_role_cell_value(self, file_info: FileInfo, column: int) -> Any:
        if column == self.COL_KEEP:
            return self._is_recommended_keeper(file_info.file_id)
        if column == self.COL_NAME:
            return file_info.path.name
        if column == self.COL_PATH:
            return str(file_info.path)
        if column == self.COL_SIZE:
            return file_info.size if file_info.size is not None else 0
        if column == self.COL_MODIFIED:
            return file_info.mtime.timestamp() if file_info.mtime else 0
        return None

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        """헤더 데이터 반환."""
        if role != Qt.ItemDataRole.DisplayRole:
            return None

        if orientation == Qt.Orientation.Horizontal:
            headers = ["Keeper", "파일명", "경로", "범위", "크기", "수정일"]
            if 0 <= section < len(headers):
                return headers[section]

        return None

    @staticmethod
    def _evidence_file_row(files_info: Any, file_id: int) -> Optional[dict[str, Any]]:
        raw = files_info.get(str(file_id)) or files_info.get(file_id)
        return raw if isinstance(raw, dict) else None

    @staticmethod
    def _path_from_evidence_row(row: dict[str, Any]) -> Optional[Path]:
        if "path" in row:
            return Path(row["path"])
        if "filename" in row:
            return Path(row["filename"])
        return None

    @staticmethod
    def _mtime_from_evidence_row(row: dict[str, Any]) -> Optional[datetime]:
        if "mtime" not in row:
            return None
        mtime_val = row["mtime"]
        if isinstance(mtime_val, (int, float)):
            return datetime.fromtimestamp(mtime_val)
        if isinstance(mtime_val, str):
            try:
                return datetime.fromisoformat(mtime_val.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                return None
        return None

    def _file_info_for_group_member(
        self,
        file_id: int,
        file_data: Optional["FileData"],
        files_info: Any,
    ) -> FileInfo:
        raw = self._evidence_file_row(files_info, file_id)
        path: Optional[Path] = None
        size: Optional[int] = None
        mtime: Optional[datetime] = None

        if file_data is not None:
            path = file_data.path
            size = file_data.size
            mtime = file_data.mtime
        elif raw is not None:
            path = self._path_from_evidence_row(raw)
            size = raw.get("size")
            mtime = self._mtime_from_evidence_row(raw)

        range_str: Optional[str] = None
        if raw is not None:
            range_str = raw.get("range") or raw.get("range_str")

        if path is None:
            path = Path(f"file_id_{file_id}")

        return FileInfo(file_id=file_id, path=path, size=size, mtime=mtime, range_str=range_str)

    def set_group(self, result: DuplicateGroupResult) -> None:
        """그룹 설정.

        FileDataStore에서 파일 정보를 가져옵니다.
        evidence는 range_str 추출용으로만 사용 (fallback).

        Args:
            result: 중복 그룹 결과.
        """
        self.beginResetModel()
        self._group_result = result

        evidence = result.evidence or {}
        files_info = evidence.get("files", {})

        file_info_list: list[FileInfo] = []
        for file_id in result.file_ids:
            file_data = self._file_data_store.get_file(file_id)
            file_info_list.append(self._file_info_for_group_member(file_id, file_data, files_info))

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
