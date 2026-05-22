"""헤더 컴포넌트 (브랜드 + 서브타이틀)."""

from typing import Optional

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget


class HeaderWidget(QWidget):
    """헤더 위젯 — 제목 및 서브타이틀 (작업 지표는 WorkTab CompactBar)."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("header")
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(12)

        title_block = QVBoxLayout()
        title_block.setSpacing(4)

        title_label = QLabel("NovelGuard")
        title_label.setObjectName("headerTitle")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_block.addWidget(title_label)

        subtitle = QLabel("텍스트 소설 파일 정리 · 중복 탐지 · 안전 이동")
        subtitle.setObjectName("headerSubtitle")
        title_block.addWidget(subtitle)

        layout.addLayout(title_block)
        layout.addStretch()
