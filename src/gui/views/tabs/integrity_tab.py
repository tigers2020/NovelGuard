"""무결성 확인 탭."""
from typing import Optional

from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
)

from gui.views.tabs.base_tab import BaseTab


class IntegrityTab(BaseTab):
    """무결성 확인 탭."""
    
    def get_title(self) -> str:
        """페이지 제목 반환."""
        return "✓ 무결성 확인"
    
    def _setup_content(self, layout: QVBoxLayout) -> None:
        """컨텐츠 설정."""
        # 액션 바
        action_bar = self._create_action_bar()
        layout.addLayout(action_bar)
        
        # 프로그레스 섹션
        self._progress_section = self._create_progress_section()
        layout.addWidget(self._progress_section)
        
        # 통계 그리드
        stats_grid = self._create_stats_grid()
        layout.addLayout(stats_grid)
    
    def _create_action_bar(self) -> QHBoxLayout:
        """액션 바 생성."""
        layout = QHBoxLayout()
        layout.setSpacing(16)
        
        check_btn = QPushButton("무결성 검사")
        check_btn.setObjectName("btnPrimary")
        layout.addWidget(check_btn)
        
        fix_btn = QPushButton("자동 수정")
        fix_btn.setObjectName("btnSuccess")
        layout.addWidget(fix_btn)
        
        layout.addStretch()
        
        return layout
    
    def _create_progress_section(self) -> QGroupBox:
        """프로그레스 섹션 생성."""
        group = QGroupBox()
        group.setTitle("")
        
        layout = QVBoxLayout(group)
        layout.setSpacing(12)
        
        # 프로그레스 헤더
        progress_header = QHBoxLayout()
        progress_header.setContentsMargins(0, 0, 0, 0)
        
        progress_title = QLabel("무결성 검사 진행 중...")
        progress_title.setObjectName("progressTitle")
        progress_header.addWidget(progress_title)
        
        progress_header.addStretch()
        
        self._progress_percent = QLabel("0%")
        self._progress_percent.setObjectName("progressPercent")
        progress_header.addWidget(self._progress_percent)
        
        layout.addLayout(progress_header)
        
        # 프로그레스 바
        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_bar.setTextVisible(False)
        layout.addWidget(self._progress_bar)
        
        # 프로그레스 정보
        self._progress_info = QLabel("대기 중...")
        self._progress_info.setObjectName("progressInfo")
        self._progress_info.setStyleSheet("font-size: 12px; color: #808080;")
        layout.addWidget(self._progress_info)
        
        # 항상 보이도록 설정
        group.setVisible(True)
        
        return group
    
    def _create_stats_grid(self) -> QVBoxLayout:
        """통계 그리드 생성."""
        layout = QVBoxLayout()
        layout.setSpacing(16)
        
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(16)
        
        # 정상 파일
        normal_card = self._create_stat_card("정상 파일", "0", "95.5%", "#10b981")
        stats_layout.addWidget(normal_card)
        
        # 경고
        warning_card = self._create_stat_card("경고", "0", None, "#f59e0b")
        stats_layout.addWidget(warning_card)
        
        # 오류
        error_card = self._create_stat_card("오류", "0", None, "#ef4444")
        stats_layout.addWidget(error_card)
        
        layout.addLayout(stats_layout)
        
        return layout
    
    def _create_stat_card(self, label: str, value: str, unit: Optional[str], color: str) -> QGroupBox:
        """통계 카드 생성."""
        card = QGroupBox()
        card.setStyleSheet(f"""
            QGroupBox {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {color}, stop:1 {color}dd);
                border: none;
                border-radius: 12px;
                padding: 20px;
                color: white;
            }}
        """)
        
        layout = QVBoxLayout(card)
        layout.setSpacing(8)
        
        label_widget = QLabel(label)
        label_widget.setStyleSheet("background: transparent; font-size: 13px; opacity: 0.9; color: white;")
        layout.addWidget(label_widget)
        
        value_widget = QLabel(value)
        value_widget.setStyleSheet("background: transparent; font-size: 32px; font-weight: 700; color: white;")
        layout.addWidget(value_widget)
        
        if unit:
            unit_widget = QLabel(unit)
            unit_widget.setStyleSheet("background: transparent; font-size: 14px; opacity: 0.9; color: white;")
            layout.addWidget(unit_widget)
        
        return card
