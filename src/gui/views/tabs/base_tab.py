"""기본 탭 클래스."""
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)


class BaseTab(QWidget):
    """기본 탭 위젯 - 모든 탭의 기본 클래스."""
    
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """기본 탭 초기화."""
        super().__init__(parent)
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        """UI 설정."""
        # 스크롤 영역
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        # 컨텐츠 위젯
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(32, 32, 32, 32)
        content_layout.setSpacing(24)
        
        # 페이지 제목
        self._page_title = self._create_page_title()
        content_layout.addWidget(self._page_title)
        
        # 컨텐츠 추가 (서브클래스에서 구현)
        self._setup_content(content_layout)
        
        content_layout.addStretch()
        
        scroll_area.setWidget(content_widget)
        
        # 메인 레이아웃
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addWidget(scroll_area)
    
    def _create_page_title(self) -> QLabel:
        """페이지 제목 생성."""
        title = QLabel(self.get_title())
        title.setObjectName("pageTitle")
        return title
    
    def _setup_content(self, layout: QVBoxLayout) -> None:
        """컨텐츠 설정 (서브클래스에서 구현)."""
        placeholder = QLabel("컨텐츠 구현 예정...")
        placeholder.setStyleSheet("color: #808080; font-size: 14px;")
        layout.addWidget(placeholder)
    
    def get_title(self) -> str:
        """페이지 제목 반환 (서브클래스에서 구현)."""
        raise NotImplementedError("Subclass must implement get_title")
