"""메인 윈도우 GUI 구현.

sample.html을 기반으로 한 PySide6 GUI 구현.
"""

# 표준 라이브러리
from pathlib import Path
from typing import Optional

# 로컬
from gui.models.result_table_model import ResultTableModel
from gui.stores.app_state import StateManager, AppState, ProgressState
from gui.stores.result_store import ResultStore
from gui.view_models.file_row import FileRow

# 서드파티
from PySide6.QtCore import Qt, QSize, Signal, QThread, QTimer, QSettings
from PySide6.QtGui import QFont, QIcon, QPalette, QColor
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QPushButton,
    QLabel,
    QProgressBar,
    QTextEdit,
    QLineEdit,
    QCheckBox,
    QComboBox,
    QGroupBox,
    QScrollArea,
    QFrame,
    QFileDialog,
    QMessageBox,
    QSlider,
    QSpinBox,
    QStackedWidget,
    QButtonGroup,
    QTableView,
    QSplitter,
    QHeaderView,
    QAbstractItemView,
)


class MainWindow(QMainWindow):
    """메인 윈도우 클래스.
    
    sample.html의 디자인을 기반으로 한 PySide6 GUI 구현.
    """

    def __init__(self) -> None:
        """메인 윈도우 초기화."""
        super().__init__()
        self.setWindowTitle("텍스트 정리 프로그램")
        self.setMinimumSize(1400, 800)
        
        # QSettings 초기화
        self.settings = QSettings("NovelGuard", "NovelGuard")
        
        # 설정 키 상수
        self.SETTING_LAST_FOLDER = "last_folder"
        self.SETTING_EXTENSIONS = "extensions"
        self.SETTING_SCAN_OPTIONS = "scan_options"
        
        # UI 위젯 참조 저장용
        self.folder_input: Optional[QLineEdit] = None
        self.ext_input: Optional[QLineEdit] = None
        self.scan_checkboxes: dict[str, QCheckBox] = {}
        self.scan_btn: Optional[QPushButton] = None
        self.stop_btn: Optional[QPushButton] = None
        
        # 진행률 위젯 참조 저장용
        self.progress_stage_label: Optional[QLabel] = None
        self.progress_overall_bar: Optional[QProgressBar] = None
        self.progress_stage_bar: Optional[QProgressBar] = None
        self.progress_info_label: Optional[QLabel] = None
        self.progress_file_label: Optional[QLabel] = None
        
        # 상태 관리자 초기화
        self.state_manager = StateManager(self)
        self.state_manager.stateChanged.connect(self._update_ui_state)
        self.state_manager.progressUpdated.connect(self._update_progress)
        
        # ResultStore 초기화
        self.result_store = ResultStore()
        
        # 중앙 위젯 설정
        central_widget = QWidget()
        central_widget.setStyleSheet("background-color: #1a1a1a;")
        self.setCentralWidget(central_widget)
        
        # 메인 레이아웃
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 헤더 생성
        header = self._create_header()
        main_layout.addWidget(header)
        
        # 메인 콘텐츠 영역 (사이드바 + 콘텐츠)
        content_widget = QWidget()
        content_layout = QHBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        
        # 사이드바 생성
        sidebar, nav_buttons = self._create_sidebar()
        content_layout.addWidget(sidebar)
        
        # 스택 위젯 생성 (탭 전환용)
        self.stacked_widget = QStackedWidget()
        self.stacked_widget.setStyleSheet("""
            QStackedWidget {
                border: none;
                background-color: #1a1a1a;
            }
        """)
        
        # 각 탭 페이지 생성
        self._create_pages()
        
        # 네비게이션 버튼과 페이지 연결
        self._connect_navigation(nav_buttons)
        
        content_layout.addWidget(self.stacked_widget, stretch=1)
        
        main_layout.addWidget(content_widget, stretch=1)
        
        # 스타일 적용
        self._apply_styles()
        
    def _create_header(self) -> QWidget:
        """헤더 위젯 생성.
        
        Returns:
            헤더 위젯
        """
        header = QWidget()
        header.setFixedHeight(100)
        header.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #6366f1, stop:1 #8b5cf6);
                color: white;
                border-bottom: 1px solid #2a2a2a;
            }
        """)
        
        layout = QHBoxLayout(header)
        layout.setContentsMargins(32, 24, 32, 24)
        
        # 제목
        title_label = QLabel("📁 텍스트 정리 프로그램")
        title_font = QFont()
        title_font.setPointSize(20)
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)
        
        layout.addStretch()
        
        # 통계 영역
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(24)
        
        # 총 파일
        total_files = self._create_stat_item("총 파일", "12,458")
        stats_layout.addWidget(total_files)
        
        # 처리 완료
        processed = self._create_stat_item("처리 완료", "5,623")
        stats_layout.addWidget(processed)
        
        # 절감 용량
        saved = self._create_stat_item("절감 용량", "2.3 GB")
        stats_layout.addWidget(saved)
        
        layout.addLayout(stats_layout)
        
        return header
    
    def _create_stat_item(self, label: str, value: str) -> QWidget:
        """통계 항목 위젯 생성.
        
        Args:
            label: 라벨 텍스트
            value: 값 텍스트
            
        Returns:
            통계 항목 위젯
        """
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        label_widget = QLabel(label)
        label_widget.setStyleSheet("""
            QLabel {
                color: rgba(255, 255, 255, 230);
                font-size: 12px;
            }
        """)
        layout.addWidget(label_widget)
        
        value_widget = QLabel(value)
        value_font = QFont()
        value_font.setPointSize(18)
        value_font.setBold(True)
        value_widget.setFont(value_font)
        value_widget.setStyleSheet("color: white;")
        layout.addWidget(value_widget)
        
        return widget
    
    def _create_sidebar(self) -> tuple[QWidget, dict[str, QPushButton]]:
        """사이드바 위젯 생성.
        
        Returns:
            (사이드바 위젯, 네비게이션 버튼 딕셔너리)
        """
        sidebar = QWidget()
        sidebar.setFixedWidth(280)
        sidebar.setStyleSheet("""
            QWidget {
                background-color: #121212;
                border-right: 1px solid #2a2a2a;
            }
        """)
        
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(32)
        
        # 네비게이션 버튼 저장용
        nav_buttons = {}
        
        # 메인 작업 섹션
        main_items = [
            ("📁", "파일 스캔", "scan", True),
            ("🔍", "중복 파일 정리", "duplicate", False),
            ("📏", "작은 파일 정리", "small", False),
            ("✓", "무결성 확인", "integrity", False),
            ("🔤", "인코딩 통일", "encoding", False),
        ]
        main_section, main_btns = self._create_nav_section("메인 작업", main_items)
        layout.addWidget(main_section)
        nav_buttons.update(main_btns)
        
        # 관리 섹션
        manage_items = [
            ("📊", "통계 및 리포트", "stats", False),
            ("📝", "작업 로그", "log", False),
            ("↩️", "Undo/Rollback", "undo", False),
            ("⚙️", "설정", "settings", False),
        ]
        manage_section, manage_btns = self._create_nav_section("관리", manage_items)
        layout.addWidget(manage_section)
        nav_buttons.update(manage_btns)
        
        layout.addStretch()
        
        return sidebar, nav_buttons
    
    def _create_nav_section(self, title: str, items: list[tuple[str, str, str, bool]]) -> tuple[QWidget, dict[str, QPushButton]]:
        """네비게이션 섹션 생성.
        
        Args:
            title: 섹션 제목
            items: (아이콘, 텍스트, 키, 활성화 여부) 튜플 리스트
            
        Returns:
            (네비게이션 섹션 위젯, 버튼 딕셔너리)
        """
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        
        # 제목
        title_label = QLabel(title)
        title_label.setStyleSheet("""
            QLabel {
                font-size: 12px;
                font-weight: bold;
                text-transform: uppercase;
                color: #666666;
                letter-spacing: 0.5px;
            }
        """)
        layout.addWidget(title_label)
        
        # 항목들
        buttons = {}
        for icon, text, key, is_active in items:
            item = QPushButton(f"{icon} {text}")
            item.setCheckable(True)
            item.setChecked(is_active)
            item.setStyleSheet("""
                QPushButton {
                    text-align: left;
                    padding: 12px 16px;
                    border-radius: 8px;
                    font-size: 14px;
                    font-weight: 500;
                    color: #a0a0a0;
                    background-color: transparent;
                    border: none;
                }
                QPushButton:hover {
                    background-color: #2a2a2a;
                    color: #e0e0e0;
                }
                QPushButton:checked {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #6366f1, stop:1 #8b5cf6);
                    color: white;
                }
            """)
            layout.addWidget(item)
            buttons[key] = item
        
        return widget, buttons
    
    def _create_pages(self) -> None:
        """각 탭 페이지 생성."""
        # 파일 스캔 페이지
        scan_page = self._create_scan_page()
        self.stacked_widget.addWidget(scan_page)
        
        # 중복 파일 정리 페이지
        duplicate_page = self._create_duplicate_page()
        self.stacked_widget.addWidget(duplicate_page)
        
        # 작은 파일 정리 페이지
        small_page = self._create_small_files_page()
        self.stacked_widget.addWidget(small_page)
        
        # 무결성 확인 페이지
        integrity_page = self._create_integrity_page()
        self.stacked_widget.addWidget(integrity_page)
        
        # 인코딩 통일 페이지
        encoding_page = self._create_encoding_page()
        self.stacked_widget.addWidget(encoding_page)
        
        # 통계 및 리포트 페이지
        stats_page = self._create_stats_page()
        self.stacked_widget.addWidget(stats_page)
        
        # 작업 로그 페이지
        log_page = self._create_log_page()
        self.stacked_widget.addWidget(log_page)
        
        # Undo/Rollback 페이지
        undo_page = self._create_undo_page()
        self.stacked_widget.addWidget(undo_page)
        
        # 설정 페이지
        settings_page = self._create_settings_page()
        self.stacked_widget.addWidget(settings_page)
    
    def _create_scrollable_page(self, widgets: list[QWidget]) -> QWidget:
        """스크롤 가능한 페이지 생성.
        
        Args:
            widgets: 페이지에 포함할 위젯 리스트
            
        Returns:
            스크롤 가능한 페이지 위젯
        """
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: #1a1a1a;
            }
        """)
        
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(24)
        
        for widget in widgets:
            layout.addWidget(widget)
        
        layout.addStretch()
        
        scroll.setWidget(content)
        return scroll
    
    def _create_scan_page(self) -> QWidget:
        """파일 스캔 페이지 생성.
        
        Returns:
            파일 스캔 페이지 위젯
        """
        widgets = [
            self._create_action_bar(),
            self._create_progress_section(),
            self._create_scan_settings(),
        ]
        return self._create_scrollable_page(widgets)
    
    def _create_duplicate_page(self) -> QWidget:
        """중복 파일 정리 페이지 생성.
        
        Returns:
            중복 파일 정리 페이지 위젯
        """
        widgets = [
            self._create_filter_bar(),
            self._create_stats_grid(),
            self._create_results_section(),
        ]
        return self._create_scrollable_page(widgets)
    
    def _create_small_files_page(self) -> QWidget:
        """작은 파일 정리 페이지 생성.
        
        Returns:
            작은 파일 정리 페이지 위젯
        """
        widgets = [
            self._create_filter_bar(),
            self._create_stats_grid(),
            self._create_results_section(),
        ]
        return self._create_scrollable_page(widgets)
    
    def _create_integrity_page(self) -> QWidget:
        """무결성 확인 페이지 생성.
        
        Returns:
            무결성 확인 페이지 위젯
        """
        widgets = [
            self._create_filter_bar(),
            self._create_stats_grid(),
            self._create_results_section(),
        ]
        return self._create_scrollable_page(widgets)
    
    def _create_encoding_page(self) -> QWidget:
        """인코딩 통일 페이지 생성.
        
        Returns:
            인코딩 통일 페이지 위젯
        """
        widgets = [
            self._create_filter_bar(),
            self._create_stats_grid(),
            self._create_results_section(),
        ]
        return self._create_scrollable_page(widgets)
    
    def _create_stats_page(self) -> QWidget:
        """통계 및 리포트 페이지 생성.
        
        Returns:
            통계 및 리포트 페이지 위젯
        """
        widgets = [
            self._create_stats_grid(),
            self._create_results_section(),
        ]
        return self._create_scrollable_page(widgets)
    
    def _create_log_page(self) -> QWidget:
        """작업 로그 페이지 생성.
        
        Returns:
            작업 로그 페이지 위젯
        """
        widgets = [
            self._create_log_section(),
        ]
        return self._create_scrollable_page(widgets)
    
    def _create_undo_page(self) -> QWidget:
        """Undo/Rollback 페이지 생성.
        
        Returns:
            Undo/Rollback 페이지 위젯
        """
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(24)
        
        title = QLabel("Undo/Rollback")
        title_font = QFont()
        title_font.setPointSize(24)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setStyleSheet("color: #e0e0e0;")
        layout.addWidget(title)
        
        info = QLabel("최근 작업 내역을 확인하고 되돌릴 수 있습니다.")
        info.setStyleSheet("color: #b0b0b0; font-size: 14px;")
        layout.addWidget(info)
        
        layout.addStretch()
        
        return widget
    
    def _create_settings_page(self) -> QWidget:
        """설정 페이지 생성.
        
        Returns:
            설정 페이지 위젯
        """
        widgets = [
            self._create_duplicate_settings(),
        ]
        return self._create_scrollable_page(widgets)
    
    def _connect_navigation(self, nav_buttons: dict[str, QPushButton]) -> None:
        """네비게이션 버튼과 페이지 연결.
        
        Args:
            nav_buttons: 네비게이션 버튼 딕셔너리
        """
        # 페이지 인덱스 매핑
        page_indices = {
            "scan": 0,
            "duplicate": 1,
            "small": 2,
            "integrity": 3,
            "encoding": 4,
            "stats": 5,
            "log": 6,
            "undo": 7,
            "settings": 8,
        }
        
        # QButtonGroup으로 단일 선택 보장
        self.nav_button_group = QButtonGroup(self)
        self.nav_button_group.setExclusive(True)
        
        for key, button in nav_buttons.items():
            # 버튼 그룹에 추가
            self.nav_button_group.addButton(button)
            
            if key in page_indices:
                page_index = page_indices[key]
                # buttonClicked 시그널로 페이지 전환
                button.clicked.connect(
                    lambda checked, idx=page_index: self._switch_page(idx)
                )
    
    def _switch_page(self, index: int) -> None:
        """페이지 전환.
        
        Args:
            index: 페이지 인덱스
        """
        # QButtonGroup이 자동으로 단일 선택 처리하므로 수동 체크 해제 불필요
        # 페이지 전환만 수행
        self.stacked_widget.setCurrentIndex(index)
    
    def _create_action_bar(self) -> QWidget:
        """액션 바 위젯 생성.
        
        Returns:
            액션 바 위젯
        """
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        
        # 폴더 선택 버튼
        folder_btn = QPushButton("📁 폴더 선택")
        folder_btn.setStyleSheet(self._get_primary_button_style())
        folder_btn.clicked.connect(self._on_select_folder)
        layout.addWidget(folder_btn)
        
        # 스캔 시작 버튼
        self.scan_btn = QPushButton("▶ 스캔 시작")
        self.scan_btn.setStyleSheet(self._get_primary_button_style())
        self.scan_btn.clicked.connect(self._on_start_scan)
        layout.addWidget(self.scan_btn)
        
        # 중지 버튼
        self.stop_btn = QPushButton("⏹ 중지")
        self.stop_btn.setStyleSheet(self._get_secondary_button_style())
        self.stop_btn.setEnabled(False)  # 초기에는 비활성화
        self.stop_btn.clicked.connect(self._on_stop_scan)
        layout.addWidget(self.stop_btn)
        
        # Dry Run 버튼
        dry_run_btn = QPushButton("👁 Dry Run")
        dry_run_btn.setStyleSheet(self._get_secondary_button_style())
        dry_run_btn.setToolTip("실제 작업 전 미리보기")
        layout.addWidget(dry_run_btn)
        
        layout.addStretch()
        
        return widget
    
    def _create_progress_section(self) -> QGroupBox:
        """진행률 섹션 생성.
        
        Returns:
            진행률 섹션 위젯
        """
        group = QGroupBox()
        group.setStyleSheet("""
            QGroupBox {
                background-color: #212121;
                border-radius: 12px;
                padding: 20px;
                border: 1px solid #2a2a2a;
            }
        """)
        
        layout = QVBoxLayout(group)
        layout.setSpacing(12)
        
        # 헤더
        header_layout = QHBoxLayout()
        title = QLabel("작업 진행 중")
        title.setStyleSheet("font-size: 14px; font-weight: 600; color: #b0b0b0;")
        header_layout.addWidget(title)
        header_layout.addStretch()
        self.progress_percent_label = QLabel("0%")
        self.progress_percent_label.setStyleSheet("font-size: 14px; font-weight: 700; color: #6366f1;")
        header_layout.addWidget(self.progress_percent_label)
        layout.addLayout(header_layout)
        
        # Stage 표시
        self.progress_stage_label = QLabel("대기 중")
        self.progress_stage_label.setStyleSheet("font-size: 13px; font-weight: 500; color: #e0e0e0;")
        layout.addWidget(self.progress_stage_label)
        
        # 전체 진행률 바
        self.progress_overall_bar = QProgressBar()
        self.progress_overall_bar.setValue(0)
        self.progress_overall_bar.setStyleSheet("""
            QProgressBar {
                height: 8px;
                border-radius: 4px;
                background-color: #2a2a2a;
                border: none;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #6366f1, stop:1 #8b5cf6);
                border-radius: 4px;
            }
        """)
        layout.addWidget(self.progress_overall_bar)
        
        # Stage 진행률 바
        stage_label = QLabel("현재 단계:")
        stage_label.setStyleSheet("font-size: 12px; color: #808080; margin-top: 8px;")
        layout.addWidget(stage_label)
        
        self.progress_stage_bar = QProgressBar()
        self.progress_stage_bar.setValue(0)
        self.progress_stage_bar.setStyleSheet("""
            QProgressBar {
                height: 6px;
                border-radius: 3px;
                background-color: #2a2a2a;
                border: none;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #4facfe, stop:1 #00f2fe);
                border-radius: 3px;
            }
        """)
        layout.addWidget(self.progress_stage_bar)
        
        # 현재 처리 중 파일
        self.progress_file_label = QLabel("")
        self.progress_file_label.setStyleSheet("font-size: 11px; color: #666666; font-style: italic;")
        self.progress_file_label.setWordWrap(True)
        layout.addWidget(self.progress_file_label)
        
        # 정보
        self.progress_info_label = QLabel("대기 중...")
        self.progress_info_label.setStyleSheet("font-size: 12px; color: #808080;")
        layout.addWidget(self.progress_info_label)
        
        return group
    
    def _create_scan_settings(self) -> QGroupBox:
        """스캔 설정 그룹 생성.
        
        Returns:
            스캔 설정 그룹 위젯
        """
        group = QGroupBox("스캔 설정")
        group.setStyleSheet(self._get_group_box_style())
        
        layout = QVBoxLayout(group)
        layout.setSpacing(20)
        
        # 대상 폴더
        folder_layout = QVBoxLayout()
        folder_label = QLabel("대상 폴더")
        folder_label.setStyleSheet("font-size: 14px; font-weight: 600; color: #b0b0b0;")
        folder_layout.addWidget(folder_label)
        self.folder_input = QLineEdit()
        self.folder_input.setReadOnly(True)
        self.folder_input.setStyleSheet(self._get_input_style())
        # QSettings에서 마지막 폴더 복원
        last_folder = self.settings.value(self.SETTING_LAST_FOLDER, "")
        if last_folder:
            self.folder_input.setText(last_folder)
        folder_layout.addWidget(self.folder_input)
        layout.addLayout(folder_layout)
        
        # 파일 확장자 필터
        ext_layout = QVBoxLayout()
        ext_label = QLabel("파일 확장자 필터")
        ext_label.setStyleSheet("font-size: 14px; font-weight: 600; color: #b0b0b0;")
        ext_layout.addWidget(ext_label)
        self.ext_input = QLineEdit()
        self.ext_input.setPlaceholderText(".txt, .md, .log (비어있으면 모든 텍스트 파일)")
        self.ext_input.setStyleSheet(self._get_input_style())
        # QSettings에서 확장자 필터 복원
        saved_extensions = self.settings.value(self.SETTING_EXTENSIONS, "")
        if saved_extensions:
            self.ext_input.setText(saved_extensions)
        # 변경 시 저장
        self.ext_input.textChanged.connect(
            lambda text: self.settings.setValue(self.SETTING_EXTENSIONS, text)
        )
        ext_layout.addWidget(self.ext_input)
        layout.addLayout(ext_layout)
        
        # 스캔 옵션
        options_label = QLabel("스캔 옵션")
        options_label.setStyleSheet("font-size: 14px; font-weight: 600; color: #b0b0b0;")
        layout.addWidget(options_label)
        
        options_grid = QGridLayout()
        options = [
            ("하위 폴더 포함", "recursive", True),
            ("증분 스캔 (변경된 파일만)", "incremental", True),
            ("숨김 파일 포함", "include_hidden", False),
            ("심볼릭 링크 따라가기", "follow_symlinks", True),
        ]
        row = 0
        for text, key, default_checked in options:
            checkbox = QCheckBox(text)
            # QSettings에서 옵션 복원
            saved_value = self.settings.value(f"{self.SETTING_SCAN_OPTIONS}/{key}", default_checked, type=bool)
            checkbox.setChecked(saved_value)
            # 변경 시 저장
            checkbox.toggled.connect(
                lambda checked, k=key: self.settings.setValue(f"{self.SETTING_SCAN_OPTIONS}/{k}", checked)
            )
            options_grid.addWidget(checkbox, row // 2, row % 2)
            self.scan_checkboxes[key] = checkbox
            row += 1
        layout.addLayout(options_grid)
        
        return group
    
    def _create_duplicate_settings(self) -> QGroupBox:
        """중복 탐지 설정 그룹 생성.
        
        Returns:
            중복 탐지 설정 그룹 위젯
        """
        group = QGroupBox("중복 탐지 설정")
        group.setStyleSheet(self._get_group_box_style())
        
        layout = QVBoxLayout(group)
        layout.setSpacing(20)
        
        # 중복 유형
        type_label = QLabel("중복 유형")
        type_label.setStyleSheet("font-size: 14px; font-weight: 600; color: #b0b0b0;")
        layout.addWidget(type_label)
        
        type_grid = QGridLayout()
        types = [
            ("완전 중복 (Exact)", True),
            ("유사 중복 (Near)", True),
            ("포함 관계 (Containment)", True),
        ]
        row = 0
        for text, checked in types:
            checkbox = QCheckBox(text)
            checkbox.setChecked(checked)
            type_grid.addWidget(checkbox, row // 2, row % 2)
            row += 1
        layout.addLayout(type_grid)
        
        # 유사도 임계값
        threshold_layout = QVBoxLayout()
        threshold_label = QLabel("유사도 임계값 (%)")
        threshold_label.setStyleSheet("font-size: 14px; font-weight: 600; color: #b0b0b0;")
        threshold_layout.addWidget(threshold_label)
        
        slider_layout = QHBoxLayout()
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setMinimum(50)
        slider.setMaximum(100)
        slider.setValue(85)
        slider_layout.addWidget(slider)
        value_label = QLabel("85%")
        slider.valueChanged.connect(lambda v: value_label.setText(f"{v}%"))
        slider_layout.addWidget(value_label)
        threshold_layout.addLayout(slider_layout)
        
        info_label = QLabel("85% 이상 유사 시 중복으로 판정")
        info_label.setStyleSheet("font-size: 12px; color: #808080;")
        threshold_layout.addWidget(info_label)
        layout.addLayout(threshold_layout)
        
        # 충돌 시 정책
        policy_layout = QVBoxLayout()
        policy_label = QLabel("충돌 시 정책")
        policy_label.setStyleSheet("font-size: 14px; font-weight: 600; color: #b0b0b0;")
        policy_layout.addWidget(policy_label)
        policy_combo = QComboBox()
        policy_combo.addItems([
            "건너뛰기 (Skip)",
            "접미사 추가 (Rename)",
            "덮어쓰기 (Overwrite)",
            "병합 (Merge)",
        ])
        policy_combo.setCurrentIndex(1)
        policy_combo.setStyleSheet(self._get_input_style())
        policy_layout.addWidget(policy_combo)
        layout.addLayout(policy_layout)
        
        return group
    
    def _create_filter_bar(self) -> QWidget:
        """필터 바 위젯 생성.
        
        Returns:
            필터 바 위젯
        """
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        
        # 확장자 필터
        ext_filter = self._create_filter_item("확장자:", ["전체", ".txt", ".md", ".log"])
        layout.addWidget(ext_filter)
        
        # 크기 필터
        size_filter = self._create_filter_item("크기:", ["전체", "< 1KB", "< 10KB", "> 1MB"])
        layout.addWidget(size_filter)
        
        # 중복군 크기 필터
        dup_filter = self._create_filter_item("중복군 크기:", ["전체", "≥ 2개", "≥ 5개", "≥ 10개"])
        layout.addWidget(dup_filter)
        
        layout.addStretch()
        
        return widget
    
    def _create_filter_item(self, label: str, options: list[str]) -> QWidget:
        """필터 항목 위젯 생성.
        
        Args:
            label: 라벨 텍스트
            options: 옵션 리스트
            
        Returns:
            필터 항목 위젯
        """
        widget = QWidget()
        widget.setStyleSheet("""
            QWidget {
                background-color: #212121;
                border-radius: 20px;
                padding: 8px 16px;
                border: 1px solid #2a2a2a;
            }
        """)
        
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        label_widget = QLabel(label)
        label_widget.setStyleSheet("font-size: 13px; color: #b0b0b0;")
        layout.addWidget(label_widget)
        
        combo = QComboBox()
        combo.addItems(options)
        combo.setStyleSheet("""
            QComboBox {
                border: none;
                background-color: transparent;
                font-size: 13px;
                color: #e0e0e0;
            }
        """)
        layout.addWidget(combo)
        
        return widget
    
    def _create_stats_grid(self) -> QWidget:
        """통계 그리드 위젯 생성.
        
        Returns:
            통계 그리드 위젯
        """
        widget = QWidget()
        layout = QGridLayout(widget)
        layout.setSpacing(16)
        
        stats = [
            ("중복 파일 그룹", "247", "총 1,523개 파일", "#6366f1", "#8b5cf6"),
            ("작은 파일 (<1KB)", "892", "정리 가능", "#f093fb", "#f5576c"),
            ("인코딩 오류", "34", "수정 필요", "#4facfe", "#00f2fe"),
            ("절감 가능 용량", "2.3", "GB", "#43e97b", "#38f9d7"),
        ]
        
        for i, (label, value, unit, color1, color2) in enumerate(stats):
            stat_card = self._create_stat_card(label, value, unit, color1, color2)
            layout.addWidget(stat_card, 0, i)
        
        return widget
    
    def _create_stat_card(self, label: str, value: str, unit: str, color1: str, color2: str) -> QWidget:
        """통계 카드 위젯 생성.
        
        Args:
            label: 라벨 텍스트
            value: 값 텍스트
            unit: 단위 텍스트
            color1: 그라데이션 시작 색상
            color2: 그라데이션 끝 색상
            
        Returns:
            통계 카드 위젯
        """
        widget = QWidget()
        widget.setStyleSheet(f"""
            QWidget {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {color1}, stop:1 {color2});
                border-radius: 12px;
                padding: 20px;
            }}
        """)
        
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        label_widget = QLabel(label)
        label_widget.setStyleSheet("""
            QLabel {
                color: rgba(255, 255, 255, 230);
                font-size: 13px;
            }
        """)
        layout.addWidget(label_widget)
        
        value_widget = QLabel(value)
        value_font = QFont()
        value_font.setPointSize(32)
        value_font.setBold(True)
        value_widget.setFont(value_font)
        value_widget.setStyleSheet("color: white;")
        layout.addWidget(value_widget)
        
        unit_widget = QLabel(unit)
        unit_widget.setStyleSheet("""
            QLabel {
                color: rgba(255, 255, 255, 230);
                font-size: 14px;
            }
        """)
        layout.addWidget(unit_widget)
        
        return widget
    
    def _create_results_section(self) -> QGroupBox:
        """결과 섹션 위젯 생성.
        
        Returns:
            결과 섹션 위젯
        """
        group = QGroupBox("결과 (247개 그룹)")
        group.setStyleSheet(self._get_group_box_style())
        
        layout = QVBoxLayout(group)
        layout.setSpacing(16)
        
        # Splitter로 테이블과 Inspector 분할
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet("""
            QSplitter {
                background-color: transparent;
            }
        """)
        
        # 테이블 뷰
        table_view = QTableView()
        table_view.setStyleSheet("""
            QTableView {
                background-color: #1a1a1a;
                border: 1px solid #2a2a2a;
                border-radius: 8px;
                gridline-color: #2a2a2a;
                color: #e0e0e0;
                selection-background-color: #6366f1;
                selection-color: white;
            }
            QTableView::item {
                padding: 4px;
            }
            QHeaderView::section {
                background-color: #212121;
                color: #b0b0b0;
                padding: 8px;
                border: 1px solid #2a2a2a;
                font-weight: 600;
            }
        """)
        
        # 모델 생성 및 연결
        model = ResultTableModel(self.result_store)
        table_view.setModel(model)
        
        # 샘플 데이터 추가 (FileRow로 변환)
        sample_rows = [
            FileRow(
                file_id=1,
                group_id=1,
                group_type="EXACT",
                canonical=False,
                similarity=100.0,
                issues_count=0,
                planned_action="DELETE",
                action_status="—",
                short_path="document_final.txt",
                size=125 * 1024,
                mtime=0.0,
                encoding="UTF-8"
            ),
            FileRow(
                file_id=2,
                group_id=2,
                group_type="NEAR",
                canonical=True,
                similarity=92.0,
                issues_count=0,
                planned_action=None,
                action_status="—",
                short_path="notes_v1.txt",
                size=89 * 1024,
                mtime=0.0,
                encoding="UTF-8"
            ),
            FileRow(
                file_id=3,
                group_id=3,
                group_type="CONTAINMENT",
                canonical=False,
                similarity=None,
                issues_count=0,
                planned_action=None,
                action_status="—",
                short_path="summary.txt",
                size=12 * 1024,
                mtime=0.0,
                encoding="UTF-8"
            ),
            FileRow(
                file_id=4,
                group_id=None,
                group_type=None,
                canonical=False,
                similarity=None,
                issues_count=1,
                planned_action="DELETE",
                action_status="—",
                short_path="empty.txt",
                size=0,
                mtime=0.0,
                encoding="UTF-8"
            ),
            FileRow(
                file_id=5,
                group_id=None,
                group_type=None,
                canonical=False,
                similarity=None,
                issues_count=1,
                planned_action="CONVERT_ENCODING",
                action_status="—",
                short_path="old_data.txt",
                size=45 * 1024,
                mtime=0.0,
                encoding="EUC-KR"
            ),
        ]
        model.appendRows(sample_rows)
        
        # 컬럼 너비 조정
        header = table_view.horizontalHeader()
        header.setSectionResizeMode(ResultTableModel.COLUMN_PATH, QHeaderView.ResizeMode.Stretch)
        table_view.setColumnWidth(ResultTableModel.COLUMN_STATUS, 60)
        table_view.setColumnWidth(ResultTableModel.COLUMN_GROUP_ID, 80)
        table_view.setColumnWidth(ResultTableModel.COLUMN_GROUP_TYPE, 120)
        table_view.setColumnWidth(ResultTableModel.COLUMN_CANONICAL, 60)
        table_view.setColumnWidth(ResultTableModel.COLUMN_SIMILARITY, 100)
        table_view.setColumnWidth(ResultTableModel.COLUMN_SIZE, 100)
        table_view.setColumnWidth(ResultTableModel.COLUMN_ENCODING, 100)
        table_view.setColumnWidth(ResultTableModel.COLUMN_ISSUES, 60)
        table_view.setColumnWidth(ResultTableModel.COLUMN_ACTION, 120)
        
        # 선택 모드 설정
        table_view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table_view.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        
        # 정렬 활성화
        table_view.setSortingEnabled(True)
        
        # 컨텍스트 메뉴 설정
        table_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        table_view.customContextMenuRequested.connect(
            lambda pos: self._show_table_context_menu(table_view, model, pos)
        )
        
        # Inspector 패널 (우측)
        inspector = self._create_inspector_panel(table_view, model)
        
        # Splitter에 추가
        splitter.addWidget(table_view)
        splitter.addWidget(inspector)
        splitter.setStretchFactor(0, 2)  # 테이블이 더 넓게
        splitter.setStretchFactor(1, 1)  # Inspector는 좁게
        
        layout.addWidget(splitter)
        
        return group
    
    def _create_inspector_panel(self, table_view: QTableView, model: ResultTableModel) -> QWidget:
        """Inspector 패널 생성 (선택 항목 상세 표시).
        
        Args:
            table_view: 테이블 뷰
            model: 테이블 모델
            
        Returns:
            Inspector 패널 위젯
        """
        panel = QWidget()
        panel.setStyleSheet("""
            QWidget {
                background-color: #212121;
                border: 1px solid #2a2a2a;
                border-radius: 8px;
            }
        """)
        
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # 제목
        title = QLabel("상세 정보")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setStyleSheet("color: #e0e0e0;")
        layout.addWidget(title)
        
        # 상세 정보 표시 영역
        detail_text = QTextEdit()
        detail_text.setReadOnly(True)
        detail_text.setMaximumHeight(400)
        detail_text.setStyleSheet("""
            QTextEdit {
                background-color: #1a1a1a;
                border: 1px solid #2a2a2a;
                border-radius: 4px;
                padding: 12px;
                color: #e0e0e0;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 12px;
            }
        """)
        layout.addWidget(detail_text)
        
        # 선택 변경 시 상세 정보 업데이트
        def update_inspector() -> None:
            """선택된 항목의 상세 정보를 Inspector에 표시."""
            indexes = table_view.selectedIndexes()
            if not indexes:
                detail_text.clear()
                return
            
            # 첫 번째 선택된 행의 데이터 가져오기
            first_index = indexes[0]
            row = model.getRowByFileId(
                model._rows[first_index.row()].file_id
            ) if first_index.row() < len(model._rows) else None
            
            if row:
                # 상세 정보 포맷팅
                info_lines = [
                    f"File ID: {row.file_id}",
                    f"Group ID: {row.group_id or 'N/A'}",
                    f"Type: {row.group_type or 'N/A'}",
                    f"Similarity: {row.similarity:.1f}%" if row.similarity is not None else "Similarity: N/A",
                    f"Size: {model._format_size(row.size)}",
                    f"Path: {row.short_path}",
                    f"Encoding: {row.encoding or 'N/A'}",
                    f"Issues: {row.issues_count}",
                    f"Action: {row.planned_action or 'N/A'}",
                    f"Status: {row.action_status}",
                ]
                detail_text.setText("\n".join(info_lines))
            else:
                detail_text.clear()
        
        # 선택 변경 시그널 연결
        table_view.selectionModel().selectionChanged.connect(lambda: update_inspector())
        
        layout.addStretch()
        
        return panel
    
    def _show_table_context_menu(self, table_view: QTableView, model: ResultTableModel, position) -> None:
        """테이블 컨텍스트 메뉴 표시.
        
        Args:
            table_view: 테이블 뷰
            model: 테이블 모델
            position: 메뉴 표시 위치
        """
        from PySide6.QtWidgets import QMenu
        
        index = table_view.indexAt(position)
        if not index.isValid() or index.row() >= len(model._rows):
            return
        
        row = model._rows[index.row()]
        
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #212121;
                border: 1px solid #2a2a2a;
                color: #e0e0e0;
            }
            QMenu::item {
                padding: 8px 24px;
            }
            QMenu::item:selected {
                background-color: #6366f1;
            }
        """)
        
        # 파일 열기
        open_file_action = menu.addAction("파일 열기")
        open_file_action.triggered.connect(
            lambda: self._open_file(row.short_path)
        )
        
        # 폴더 열기
        open_folder_action = menu.addAction("폴더 열기")
        open_folder_action.triggered.connect(
            lambda: self._open_folder(row.short_path)
        )
        
        menu.addSeparator()
        
        # 경로 복사
        copy_path_action = menu.addAction("경로 복사")
        copy_path_action.triggered.connect(
            lambda: self._copy_path(row.short_path)
        )
        
        menu.addSeparator()
        
        # 제외 규칙 추가
        exclude_action = menu.addAction("제외 규칙 추가")
        exclude_action.triggered.connect(
            lambda: self._add_exclude_rule(row.short_path)
        )
        
        # 메뉴 표시
        menu.exec(table_view.viewport().mapToGlobal(position))
    
    def _open_file(self, path) -> None:
        """파일 열기.
        
        Args:
            path: 파일 경로
        """
        if not path:
            return
        
        from PySide6.QtGui import QDesktopServices
        from PySide6.QtCore import QUrl
        
        file_path = Path(path) if isinstance(path, str) else path
        if file_path.exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(file_path.resolve())))
    
    def _open_folder(self, path) -> None:
        """폴더 열기.
        
        Args:
            path: 파일 경로
        """
        if not path:
            return
        
        from PySide6.QtGui import QDesktopServices
        from PySide6.QtCore import QUrl
        
        file_path = Path(path) if isinstance(path, str) else path
        folder_path = file_path.parent if file_path.is_file() else file_path
        if folder_path.exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder_path.resolve())))
    
    def _copy_path(self, path) -> None:
        """경로 복사.
        
        Args:
            path: 파일 경로
        """
        if not path:
            return
        
        from PySide6.QtGui import QClipboard
        
        file_path = Path(path) if isinstance(path, str) else path
        clipboard = QClipboard()
        clipboard.setText(str(file_path.resolve()))
        QMessageBox.information(self, "복사 완료", f"경로가 클립보드에 복사되었습니다:\n{file_path}")
    
    def _add_exclude_rule(self, path) -> None:
        """제외 규칙 추가.
        
        Args:
            path: 파일 경로
        """
        if not path:
            return
        
        file_path = Path(path) if isinstance(path, str) else path
        # TODO: 제외 규칙 UI 구현 시 연결
        QMessageBox.information(self, "제외 규칙", f"제외 규칙 추가 기능은 추후 구현 예정입니다.\n{file_path}")
    
    def _update_progress(self, state: ProgressState) -> None:
        """진행률 업데이트.
        
        Args:
            state: 진행률 상태
        """
        # Stage 표시
        if self.progress_stage_label:
            self.progress_stage_label.setText(f"단계: {state.current_stage}")
        
        # 전체 진행률
        if self.progress_overall_bar:
            self.progress_overall_bar.setValue(state.overall_progress)
        
        # Stage 진행률
        if self.progress_stage_bar:
            self.progress_stage_bar.setValue(state.stage_progress)
        
        # 퍼센트 라벨
        if self.progress_percent_label:
            self.progress_percent_label.setText(f"{state.overall_progress}%")
        
        # 현재 처리 중 파일
        if self.progress_file_label:
            if state.current_file:
                file_path = Path(state.current_file)
                # 경로가 너무 길면 파일명만 표시
                if len(str(file_path)) > 60:
                    self.progress_file_label.setText(f"처리 중: ...{file_path.name}")
                else:
                    self.progress_file_label.setText(f"처리 중: {file_path}")
            else:
                self.progress_file_label.setText("")
        
        # 정보 텍스트
        if self.progress_info_label:
            # ETA 계산
            if state.eta_seconds > 0:
                if state.eta_seconds < 60:
                    eta_text = f"{state.eta_seconds}초"
                elif state.eta_seconds < 3600:
                    eta_text = f"{state.eta_seconds // 60}분"
                else:
                    hours = state.eta_seconds // 3600
                    minutes = (state.eta_seconds % 3600) // 60
                    eta_text = f"{hours}시간 {minutes}분"
            else:
                eta_text = "계산 중..."
            
            info_parts = [
                f"{state.files_processed:,} / {state.files_total:,} 파일 처리 완료",
                f"속도: {state.speed:.0f} files/sec" if state.speed > 0 else "속도: 계산 중...",
                f"남은 시간: {eta_text}",
            ]
            self.progress_info_label.setText(" • ".join(info_parts))
    
    def _create_result_card(self, type_text: str, count: str, filename: str, 
                           size: str, meta: str, bg_color: str, text_color: str) -> QWidget:
        """결과 카드 위젯 생성.
        
        Args:
            type_text: 타입 텍스트
            count: 개수 텍스트
            filename: 파일명
            size: 크기 텍스트
            meta: 메타 정보
            bg_color: 배경 색상
            text_color: 텍스트 색상
            
        Returns:
            결과 카드 위젯
        """
        widget = QWidget()
        widget.setStyleSheet("""
            QWidget {
                background-color: #212121;
                border: 2px solid #2a2a2a;
                border-radius: 12px;
                padding: 16px;
            }
            QWidget:hover {
                border-color: #6366f1;
            }
        """)
        
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        # 헤더
        header_layout = QHBoxLayout()
        type_label = QLabel(type_text)
        type_label.setStyleSheet(f"""
            QLabel {{
                background-color: {bg_color};
                color: {text_color};
                font-size: 12px;
                font-weight: 600;
                padding: 4px 8px;
                border-radius: 4px;
            }}
        """)
        header_layout.addWidget(type_label)
        header_layout.addStretch()
        count_label = QLabel(count)
        count_label.setStyleSheet("font-size: 12px; color: #808080;")
        header_layout.addWidget(count_label)
        layout.addLayout(header_layout)
        
        # 파일명
        filename_label = QLabel(filename)
        filename_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                font-weight: 500;
                color: #e0e0e0;
            }
        """)
        filename_label.setWordWrap(True)
        layout.addWidget(filename_label)
        
        # 메타 정보
        meta_label = QLabel(f"{size} • {meta}")
        meta_label.setStyleSheet("font-size: 12px; color: #808080;")
        layout.addWidget(meta_label)
        
        return widget
    
    def _create_log_section(self) -> QGroupBox:
        """작업 로그 섹션 생성.
        
        Returns:
            작업 로그 섹션 위젯
        """
        group = QGroupBox("작업 로그")
        group.setStyleSheet(self._get_group_box_style())
        
        layout = QVBoxLayout(group)
        
        log_console = QTextEdit()
        log_console.setReadOnly(True)
        log_console.setMaximumHeight(400)
        log_console.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border-radius: 8px;
                padding: 16px;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 12px;
            }
        """)
        
        # 샘플 로그
        sample_logs = [
            "[14:23:45] [INFO] 스캔 시작: C:\\Users\\Documents\\TextFiles",
            "[14:23:46] [INFO] 워커 스레드 8개 초기화 완료",
            "[14:23:47] [INFO] Stage 1: 메타데이터 스캔 (12,458 파일)",
            "[14:24:12] [INFO] Stage 2: 앵커 해시 생성 중...",
            "[14:24:45] [WARN] 인코딩 감지 실패: old_file.txt (confidence: 0.45)",
            "[14:25:01] [INFO] 중복 그룹 247개 발견",
        ]
        
        for log in sample_logs:
            log_console.append(log)
        
        layout.addWidget(log_console)
        
        return group
    
    def _apply_styles(self) -> None:
        """전역 스타일 적용."""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #0a0a0a;
            }
            QCheckBox {
                color: #b0b0b0;
                font-size: 14px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 2px solid #2a2a2a;
                border-radius: 4px;
                background-color: #1a1a1a;
            }
            QCheckBox::indicator:checked {
                background-color: #6366f1;
                border-color: #6366f1;
            }
            QCheckBox::indicator:hover {
                border-color: #6366f1;
            }
            QSlider::groove:horizontal {
                height: 8px;
                background: #2a2a2a;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #6366f1;
                width: 18px;
                height: 18px;
                border-radius: 9px;
                margin: -5px 0;
            }
            QSlider::handle:horizontal:hover {
                background: #8b5cf6;
            }
            QComboBox {
                color: #e0e0e0;
            }
            QComboBox::drop-down {
                border: none;
                background-color: transparent;
            }
            QComboBox::down-arrow {
                width: 0;
                height: 0;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 6px solid #e0e0e0;
                margin-right: 8px;
            }
            QComboBox QAbstractItemView {
                background-color: #212121;
                border: 1px solid #2a2a2a;
                color: #e0e0e0;
                selection-background-color: #6366f1;
                selection-color: white;
            }
        """)
    
    def _get_primary_button_style(self) -> str:
        """주요 버튼 스타일 반환.
        
        Returns:
            CSS 스타일 문자열
        """
        return """
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #6366f1, stop:1 #8b5cf6);
                color: white;
                padding: 12px 24px;
                border-radius: 8px;
                font-size: 14px;
                font-weight: 600;
                border: none;
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #5568d3, stop:1 #7c4ad6);
            }
        """
    
    def _get_secondary_button_style(self) -> str:
        """보조 버튼 스타일 반환.
        
        Returns:
            CSS 스타일 문자열
        """
        return """
            QPushButton {
                background-color: #2a2a2a;
                color: #e0e0e0;
                padding: 12px 24px;
                border-radius: 8px;
                font-size: 14px;
                font-weight: 600;
                border: 2px solid #3a3a3a;
            }
            QPushButton:hover {
                border-color: #6366f1;
                color: #6366f1;
                background-color: #252525;
            }
            QPushButton:pressed {
                background-color: #1f1f1f;
            }
        """
    
    def _get_group_box_style(self) -> str:
        """그룹 박스 스타일 반환.
        
        Returns:
            CSS 스타일 문자열
        """
        return """
            QGroupBox {
                background-color: #212121;
                border: 1px solid #2a2a2a;
                border-radius: 12px;
                padding: 24px;
                font-size: 18px;
                font-weight: 700;
                color: #e0e0e0;
                margin-top: 12px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 16px;
                padding: 0 8px;
            }
        """
    
    def _get_input_style(self) -> str:
        """입력 필드 스타일 반환.
        
        Returns:
            CSS 스타일 문자열
        """
        return """
            QLineEdit, QComboBox {
                width: 100%;
                padding: 10px 14px;
                border: 2px solid #2a2a2a;
                border-radius: 8px;
                font-size: 14px;
                background-color: #1a1a1a;
                color: #e0e0e0;
            }
            QLineEdit:focus, QComboBox:focus {
                border-color: #6366f1;
                outline: none;
            }
        """
    
    def _on_select_folder(self) -> None:
        """폴더 선택 버튼 클릭 핸들러."""
        # 마지막 선택 폴더를 기본 경로로 사용
        last_folder = self.settings.value(self.SETTING_LAST_FOLDER, "")
        folder = QFileDialog.getExistingDirectory(
            self,
            "폴더 선택",
            last_folder if last_folder else "",
            QFileDialog.Option.ShowDirsOnly | QFileDialog.Option.DontResolveSymlinks
        )
        if folder:
            # UI에 반영
            if self.folder_input:
                self.folder_input.setText(folder)
            # QSettings에 저장
            self.settings.setValue(self.SETTING_LAST_FOLDER, folder)
            # 상태 업데이트
            folder_path = Path(folder)
            self.state_manager.update_app_state(scan_folder=folder_path)
    
    def _on_start_scan(self) -> None:
        """스캔 시작 버튼 클릭 핸들러."""
        if not self.folder_input or not self.folder_input.text():
            QMessageBox.warning(self, "경고", "스캔할 폴더를 선택해주세요.")
            return
        
        # 상태 업데이트 (스캔 시작)
        self.state_manager.update_app_state(
            is_scanning=True,
            current_job="파일 스캔"
        )
        
        # TODO: 실제 Worker thread 시작
        # 예: self.scan_worker.start()
    
    def _on_stop_scan(self) -> None:
        """스캔 중지 버튼 클릭 핸들러."""
        # 상태 업데이트 (스캔 중지)
        self.state_manager.update_app_state(
            is_scanning=False,
            current_job=None
        )
        
        # TODO: 실제 Worker thread 중지
        # 예: self.scan_worker.stop()
    
    def _update_ui_state(self, state: AppState) -> None:
        """UI 상태 업데이트.
        
        Args:
            state: 애플리케이션 상태
        """
        if state.is_scanning:
            # 스캔 중: Start 비활성화, Stop 활성화
            if self.scan_btn:
                self.scan_btn.setEnabled(False)
            if self.stop_btn:
                self.stop_btn.setEnabled(True)
            
            # 입력 필드 잠금
            if self.folder_input:
                self.folder_input.setEnabled(False)
            if self.ext_input:
                self.ext_input.setEnabled(False)
            for checkbox in self.scan_checkboxes.values():
                checkbox.setEnabled(False)
        else:
            # 스캔 완료: Start 활성화, Stop 비활성화
            if self.scan_btn:
                self.scan_btn.setEnabled(True)
            if self.stop_btn:
                self.stop_btn.setEnabled(False)
            
            # 입력 필드 잠금 해제
            if self.folder_input:
                self.folder_input.setEnabled(True)
            if self.ext_input:
                self.ext_input.setEnabled(True)
            for checkbox in self.scan_checkboxes.values():
                checkbox.setEnabled(True)

