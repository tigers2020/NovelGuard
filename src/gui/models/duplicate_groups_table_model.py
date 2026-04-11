"""중복 그룹 테이블 모델."""

from typing import TYPE_CHECKING, Any, Optional, Union

from PySide6.QtCore import QAbstractTableModel, QModelIndex, QPersistentModelIndex, Qt

from application.dto.duplicate_group_result import DuplicateGroupResult

if TYPE_CHECKING:
    from gui.models.file_data_store import FileDataStore

_ModelIndex = Union[QModelIndex, QPersistentModelIndex]


class DuplicateGroupsTableModel(QAbstractTableModel):
    """중복 그룹 테이블 모델.

    QAbstractTableModel을 상속하여 중복 그룹 결과를 테이블로 표시.
    """

    # 컬럼 인덱스
    COL_TYPE = 0
    COL_GROUP_ID = 1
    COL_COUNT = 2
    COL_KEEPER = 3
    COL_CONFIDENCE = 4
    COL_KEY_TITLE = 5

    def __init__(self, parent=None, *, file_data_store: "FileDataStore") -> None:
        """중복 그룹 테이블 모델 초기화.

        Args:
            parent: 부모 객체.
            file_data_store: 파일 데이터 저장소 (필수).
        """
        super().__init__(parent)
        self._results: list[DuplicateGroupResult] = []
        self._file_data_store = file_data_store

    def rowCount(self, parent: _ModelIndex = QModelIndex()) -> int:
        """행 수 반환.

        Args:
            parent: 부모 인덱스 (사용하지 않음).

        Returns:
            행 수.
        """
        return len(self._results)

    def columnCount(self, parent: _ModelIndex = QModelIndex()) -> int:
        """컬럼 수 반환.

        Args:
            parent: 부모 인덱스 (사용하지 않음).

        Returns:
            컬럼 수 (6).
        """
        return 6

    def data(self, index: _ModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        """데이터 반환.

        Args:
            index: 모델 인덱스.
            role: 데이터 역할.

        Returns:
            데이터 (역할에 따라 다름).
        """
        if not index.isValid() or index.row() >= len(self._results):
            return None

        result = self._results[index.row()]
        column = index.column()

        if role == Qt.ItemDataRole.DisplayRole:
            if column == self.COL_TYPE:
                return self._format_duplicate_type(result.duplicate_type)
            elif column == self.COL_GROUP_ID:
                return result.group_id
            elif column == self.COL_COUNT:
                return len(result.file_ids)
            elif column == self.COL_KEEPER:
                if result.recommended_keeper_id:
                    keeper_file = self._file_data_store.get_file(result.recommended_keeper_id)
                    if keeper_file:
                        return keeper_file.path.name
                    return f"file_id:{result.recommended_keeper_id}"
                return "-"
            elif column == self.COL_CONFIDENCE:
                return self._format_confidence(result.confidence)
            elif column == self.COL_KEY_TITLE:
                return self._extract_key_title(result)
        elif role == Qt.ItemDataRole.UserRole:
            if column == self.COL_TYPE:
                return result.duplicate_type
            elif column == self.COL_GROUP_ID:
                return result.group_id
            elif column == self.COL_COUNT:
                return len(result.file_ids)
            elif column == self.COL_CONFIDENCE:
                return result.confidence
            elif column == self.COL_KEEPER:
                return result.recommended_keeper_id if result.recommended_keeper_id else 0

        return None

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        """헤더 데이터 반환.

        Args:
            section: 섹션 인덱스 (행 또는 컬럼).
            orientation: 방향 (가로 또는 세로).
            role: 데이터 역할.

        Returns:
            헤더 데이터.
        """
        if role != Qt.ItemDataRole.DisplayRole:
            return None

        if orientation == Qt.Orientation.Horizontal:
            headers = [
                "타입",
                "그룹 ID",
                "파일 수",
                "추천 Keeper",
                "신뢰도",
                "작품명/제목",
            ]
            if 0 <= section < len(headers):
                return headers[section]

        return None

    def set_results(self, results: list[DuplicateGroupResult]) -> None:
        """결과 설정.

        Args:
            results: 중복 그룹 결과 리스트.
        """
        self.beginResetModel()
        self._results = results
        self.endResetModel()

    def get_result(self, row: int) -> Optional[DuplicateGroupResult]:
        """행에 해당하는 결과 반환.

        Args:
            row: 행 인덱스.

        Returns:
            DuplicateGroupResult. 없으면 None.
        """
        if 0 <= row < len(self._results):
            return self._results[row]
        return None

    def _format_duplicate_type(self, type_str: str) -> str:
        """중복 타입 포맷팅.

        Args:
            type_str: 중복 타입 문자열.

        Returns:
            포맷된 문자열 (아이콘 + 텍스트).
        """
        icons = {
            "exact": "🔴",
            "version": "🔵",
            "containment": "🟢",
            "near": "🟡",
        }
        labels = {
            "exact": "완전 중복",
            "version": "버전 관계",
            "containment": "포함 관계",
            "near": "유사 중복",
        }
        icon = icons.get(type_str, "")
        label = labels.get(type_str, type_str)
        return f"{icon} {label}" if icon else label

    def _format_confidence(self, confidence: float) -> str:
        """신뢰도 포맷팅.

        Args:
            confidence: 신뢰도 (0.0 ~ 1.0).

        Returns:
            포맷된 문자열 (예: "95%").
        """
        return f"{confidence * 100:.0f}%"

    def _extract_key_title(self, result: DuplicateGroupResult) -> str:
        """작품명/제목 추출.

        Args:
            result: 중복 그룹 결과.

        Returns:
            작품명/제목 문자열 (evidence에서 추출 또는 파일명 prefix).
        """
        evidence = result.evidence
        if isinstance(evidence, dict):
            series_title = evidence.get("series_title_norm")
            if series_title is not None:
                return str(series_title)

        file_ids = result.file_ids
        if file_ids:
            first_file = self._file_data_store.get_file(file_ids[0])
            if first_file:
                name = first_file.path.stem
                return name

        return f"group_{result.group_id}"
