"""작은 파일 정리 탭."""
from PySide6.QtWidgets import (
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
)

from gui.views.tabs.base_tab import BaseTab


class SmallFileTab(BaseTab):
    """작은 파일 정리 탭."""
    
    def get_title(self) -> str:
        """페이지 제목 반환."""
        return "📏 작은 파일 정리"
    
    def _setup_content(self, layout: QVBoxLayout) -> None:
        """컨텐츠 설정."""
        # 액션 바
        action_bar = self._create_action_bar()
        layout.addLayout(action_bar)
        
        # 프로그레스 섹션
        self._progress_section = self._create_progress_section()
        layout.addWidget(self._progress_section)
        
        # 설정 그룹
        settings_group = self._create_settings_group()
        layout.addWidget(settings_group)
        
        # 결과 그룹
        results_group = self._create_results_group()
        layout.addWidget(results_group)
    
    def _create_action_bar(self) -> QHBoxLayout:
        """액션 바 생성."""
        layout = QHBoxLayout()
        layout.setSpacing(16)
        
        analyze_btn = QPushButton("분석 시작")
        analyze_btn.setObjectName("btnPrimary")
        layout.addWidget(analyze_btn)
        
        delete_btn = QPushButton("선택 파일 삭제")
        delete_btn.setObjectName("btnDanger")
        layout.addWidget(delete_btn)
        
        dry_run_btn = QPushButton("Dry Run")
        dry_run_btn.setObjectName("btnSecondary")
        layout.addWidget(dry_run_btn)
        
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
        
        progress_title = QLabel("작은 파일 분석 진행 중...")
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
    
    def _create_settings_group(self) -> QGroupBox:
        """설정 그룹 생성."""
        group = QGroupBox("파일 크기 기준")
        group.setObjectName("settingsGroup")
        
        layout = QVBoxLayout(group)
        layout.setSpacing(20)
        
        # 작은 파일 임계값
        threshold_layout = QVBoxLayout()
        threshold_layout.setSpacing(8)
        
        threshold_label = QLabel("작은 파일 임계값")
        threshold_label.setObjectName("formLabel")
        threshold_layout.addWidget(threshold_label)
        
        self._size_threshold = QComboBox()
        self._size_threshold.addItems([
            "0 bytes (빈 파일)",
            "< 1 KB",
            "< 10 KB",
            "< 100 KB"
        ])
        self._size_threshold.setCurrentIndex(1)  # < 1 KB
        threshold_layout.addWidget(self._size_threshold)
        
        layout.addLayout(threshold_layout)
        
        return group
    
    def _create_results_group(self) -> QGroupBox:
        """결과 그룹 생성."""
        group = QGroupBox("작은 파일 목록 (0개)")
        group.setObjectName("settingsGroup")
        
        layout = QVBoxLayout(group)
        
        # TODO: 결과 카드 그리드 구현
        placeholder = QLabel("작은 파일 분석 결과가 여기에 표시됩니다.")
        placeholder.setStyleSheet("color: #808080; font-size: 14px; padding: 20px;")
        layout.addWidget(placeholder)
        
        return group
