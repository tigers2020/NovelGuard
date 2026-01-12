"""사이드바 컴포넌트 (네비게이션 메뉴)."""
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QButtonGroup,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class SidebarWidget(QWidget):
    """사이드바 위젯 - 네비게이션 메뉴."""
    
    # 탭 전환 시그널
    tab_changed = Signal(str)  # tab_name
    
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """사이드바 위젯 초기화."""
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(280)
        
        self._button_group = QButtonGroup(self)
        self._button_group.setExclusive(True)
        
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        """UI 설정."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(32)
        
        # 메인 작업 섹션
        main_section = self._create_nav_section(
            "메인 작업",
            [
                ("scan", "📁", "파일 스캔"),
                ("duplicate", "🔍", "중복 파일 정리"),
                ("small", "📏", "작은 파일 정리"),
                ("integrity", "✓", "무결성 확인"),
                ("encoding", "🔤", "인코딩 통일"),
            ]
        )
        layout.addLayout(main_section)
        
        # 관리 섹션
        management_section = self._create_nav_section(
            "관리",
            [
                ("stats", "📊", "통계 및 리포트"),
                ("logs", "📝", "작업 로그"),
                ("undo", "↩️", "Undo/Rollback"),
                ("settings", "⚙️", "설정"),
            ]
        )
        layout.addLayout(management_section)
        
        layout.addStretch()
    
    def _create_nav_section(self, title: str, items: list[tuple[str, str, str]]) -> QVBoxLayout:
        """네비게이션 섹션 생성."""
        section_layout = QVBoxLayout()
        section_layout.setSpacing(12)
        
        # 섹션 제목
        from PySide6.QtWidgets import QLabel
        title_text = QLabel(title.upper())
        title_text.setObjectName("navTitle")
        title_font = QFont()
        title_font.setPointSize(9)
        title_font.setBold(True)
        title_text.setFont(title_font)
        section_layout.addWidget(title_text)
        
        # 네비게이션 항목
        for tab_name, icon, label in items:
            nav_button = self._create_nav_button(tab_name, icon, label)
            self._button_group.addButton(nav_button)
            section_layout.addWidget(nav_button)
            
            # 첫 번째 항목을 기본 선택
            if tab_name == "scan":
                nav_button.setChecked(True)
        
        return section_layout
    
    def _create_nav_button(self, tab_name: str, icon: str, label: str) -> QPushButton:
        """네비게이션 버튼 생성."""
        button = QPushButton(f"{icon} {label}")
        button.setObjectName("navItem")
        button.setCheckable(True)
        button.setFlat(True)
        button.setCursor(Qt.PointingHandCursor)
        
        # 탭 이름을 버튼에 저장 (속성으로)
        button.setProperty("tab_name", tab_name)
        
        # 버튼 클릭 시 탭 전환 시그널 발생
        button.clicked.connect(lambda checked, name=tab_name: self._on_tab_clicked(name))
        
        return button
    
    def _on_tab_clicked(self, tab_name: str) -> None:
        """탭 클릭 핸들러."""
        self.tab_changed.emit(tab_name)
    
    def set_active_tab(self, tab_name: str) -> None:
        """활성 탭 설정."""
        for button in self._button_group.buttons():
            if button.property("tab_name") == tab_name:
                button.setChecked(True)
                break
