"""헤더 컴포넌트 (통계 표시)."""

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)


class HeaderWidget(QWidget):
    """헤더 위젯 - 제목 및 통계 표시."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """헤더 위젯 초기화."""
        super().__init__(parent)
        self.setObjectName("header")
        self._setup_ui()
        self._set_default_values()

    def _setup_ui(self) -> None:
        """UI 설정."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(24)

        title_widget = QWidget()
        title_layout = QHBoxLayout(title_widget)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(12)

        title_label = QLabel("NovelGuard")
        title_label.setObjectName("headerTitle")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_layout.addWidget(title_label)

        layout.addWidget(title_widget)
        layout.addStretch()

        stats_widget = QWidget()
        stats_layout = QHBoxLayout(stats_widget)
        stats_layout.setContentsMargins(0, 0, 0, 0)
        stats_layout.setSpacing(24)

        self._total_files_label = self._create_stat_item("총 파일", "0")
        stats_layout.addWidget(self._total_files_label)

        self._duplicate_groups_label = self._create_stat_item("중복 그룹", "0")
        stats_layout.addWidget(self._duplicate_groups_label)

        self._saved_size_label = self._create_stat_item("절감 용량", "0 GB")
        stats_layout.addWidget(self._saved_size_label)

        self._integrity_issues_label = self._create_stat_item("이슈 파일", "0")
        stats_layout.addWidget(self._integrity_issues_label)

        layout.addWidget(stats_widget)

    def _create_stat_item(self, label_text: str, value_text: str) -> QWidget:
        """통계 항목 위젯 생성."""
        widget = QWidget()
        widget.setObjectName("statChip")
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignmentFlag.AlignRight)

        label = QLabel(label_text)
        label.setObjectName("statLabel")
        layout.addWidget(label)

        value = QLabel(value_text)
        value.setObjectName("statValue")
        layout.addWidget(value)

        return widget

    def _set_default_values(self) -> None:
        """기본 값 설정."""
        self.update_stats(0, 0, 0.0, 0)

    def update_stats(
        self,
        total_files: int,
        duplicate_groups: int,
        saved_gb: float,
        integrity_issues: int,
    ) -> None:
        """통계 정보 업데이트 (4-chip header)."""
        total_value = self._total_files_label.findChild(QLabel, "statValue")
        if total_value:
            total_value.setText(f"{total_files:,}")

        duplicate_groups_value = self._duplicate_groups_label.findChild(QLabel, "statValue")
        if duplicate_groups_value:
            duplicate_groups_value.setText(f"{duplicate_groups:,}")

        saved_value = self._saved_size_label.findChild(QLabel, "statValue")
        if saved_value:
            saved_value.setText(f"{saved_gb:.1f} GB")

        integrity_issues_value = self._integrity_issues_label.findChild(QLabel, "statValue")
        if integrity_issues_value:
            integrity_issues_value.setText(f"{integrity_issues:,}")
