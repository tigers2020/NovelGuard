"""메인 윈도우."""
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QSettings, Qt, QTimer
from PySide6.QtWidgets import (
    QHBoxLayout,
    QMainWindow,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.settings.constants import SETTINGS_KEY_SCAN_FOLDER
from gui.models.app_state import AppState
from gui.styles.dark_theme import get_dark_theme_stylesheet
from gui.views.components.file_list_table import FileListTableWidget
from gui.views.components.header import HeaderWidget
from gui.views.components.sidebar import SidebarWidget
from gui.workers.preview_worker import PreviewWorker


class MainWindow(QMainWindow):
    """메인 윈도우."""
    
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """메인 윈도우 초기화."""
        super().__init__(parent)
        self.setWindowTitle("텍스트 정리 프로그램")
        self.setMinimumSize(1400, 800)
        
        # 애플리케이션 상태
        self._app_state = AppState()
        
        # QSettings
        self._settings = QSettings()
        
        # Preview 워커
        self._preview_worker: Optional[PreviewWorker] = None
        
        # 다크 테마 적용
        self.setStyleSheet(get_dark_theme_stylesheet())
        
        # UI 설정
        self._setup_ui()
        
        # 이벤트 연결
        self._connect_signals()
        
        # 이전 설정 복원 및 자동 Preview 스캔
        self._restore_settings()
        self._auto_start_preview_scan()
    
    def _setup_ui(self) -> None:
        """UI 설정."""
        # 중앙 위젯
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 메인 레이아웃
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 헤더
        self._header = HeaderWidget(self)
        main_layout.addWidget(self._header)
        
        # 메인 컨텐츠 영역 (사이드바 + 컨텐츠 + 파일 리스트)
        content_widget = QWidget()
        content_layout = QHBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        
        # 사이드바
        self._sidebar = SidebarWidget(self)
        content_layout.addWidget(self._sidebar)
        
        # 중앙 영역 (탭 스택 + 파일 리스트)
        center_widget = QWidget()
        center_layout = QVBoxLayout(center_widget)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(0)
        
        # 컨텐츠 영역 (탭 스택)
        self._content_stack = QStackedWidget()
        self._content_stack.setObjectName("contentArea")
        center_layout.addWidget(self._content_stack, stretch=2)
        
        # 파일 리스트 테이블 (항상 보임)
        self._file_list_table = FileListTableWidget(
            self._app_state.file_data_store,
            self
        )
        center_layout.addWidget(self._file_list_table, stretch=1)
        
        content_layout.addWidget(center_widget, stretch=1)
        
        main_layout.addWidget(content_widget, stretch=1)
        
        # 탭 뷰들을 스택에 추가 (나중에 구현될 탭들)
        self._setup_tabs()
    
    def _setup_tabs(self) -> None:
        """탭 뷰 설정."""
        # Placeholder 탭들 (나중에 실제 구현으로 교체)
        from gui.views.tabs.scan_tab import ScanTab
        from gui.views.tabs.duplicate_tab import DuplicateTab
        from gui.views.tabs.small_file_tab import SmallFileTab
        from gui.views.tabs.integrity_tab import IntegrityTab
        from gui.views.tabs.encoding_tab import EncodingTab
        from gui.views.tabs.stats_tab import StatsTab
        from gui.views.tabs.logs_tab import LogsTab
        from gui.views.tabs.undo_tab import UndoTab
        from gui.views.tabs.settings_tab import SettingsTab
        
        tabs = {
            "scan": ScanTab(self),
            "duplicate": DuplicateTab(self),
            "small": SmallFileTab(self),
            "integrity": IntegrityTab(self),
            "encoding": EncodingTab(self),
            "stats": StatsTab(self),
            "logs": LogsTab(self),
            "undo": UndoTab(self),
            "settings": SettingsTab(self),
        }
        
        for tab_name, tab_widget in tabs.items():
            self._content_stack.addWidget(tab_widget)
            # 탭 이름을 위젯에 저장
            tab_widget.setProperty("tab_name", tab_name)
        
        # 기본 탭 표시
        self._switch_tab("scan")
    
    def _get_scan_tab(self):
        """ScanTab 위젯 반환."""
        for i in range(self._content_stack.count()):
            widget = self._content_stack.widget(i)
            if widget and widget.property("tab_name") == "scan":
                return widget
        return None
    
    def _get_settings_tab(self):
        """SettingsTab 위젯 반환."""
        for i in range(self._content_stack.count()):
            widget = self._content_stack.widget(i)
            if widget and widget.property("tab_name") == "settings":
                return widget
        return None
    
    def _connect_signals(self) -> None:
        """시그널 연결."""
        # 사이드바 탭 변경 시그널
        self._sidebar.tab_changed.connect(self._switch_tab)
        
        # ScanTab의 폴더 선택 시그널 연결 (_setup_tabs 후 호출되므로 안전)
        scan_tab = self._get_scan_tab()
        if scan_tab:
            scan_tab.folder_selected.connect(self._on_folder_selected)
    
    def _restore_settings(self) -> None:
        """이전 설정 복원."""
        # 마지막 선택 폴더 복원
        # _setup_tabs() 후에 호출되므로 ScanTab이 이미 생성되어 있음
        last_folder = self._settings.value(SETTINGS_KEY_SCAN_FOLDER, None)
        if last_folder:
            folder_path = Path(last_folder)
            if folder_path.exists() and folder_path.is_dir():
                self._app_state.scan_folder = str(folder_path)
                # ScanTab에도 전달
                scan_tab = self._get_scan_tab()
                if scan_tab:
                    scan_tab.set_scan_folder(folder_path)
    
    def _auto_start_preview_scan(self) -> None:
        """자동 Preview 스캔 시작 (프로그램 시작 시).
        
        마지막 폴더가 있으면 100ms 후 자동으로 Preview 스캔 시작.
        """
        last_folder = self._settings.value(SETTINGS_KEY_SCAN_FOLDER, None)
        if last_folder:
            folder_path = Path(last_folder)
            if folder_path.exists() and folder_path.is_dir():
                # UI가 완전히 로드된 후 실행
                QTimer.singleShot(100, lambda: self._start_preview_scan(folder_path))
    
    def _on_folder_selected(self, folder: Path) -> None:
        """폴더 선택 핸들러.
        
        Args:
            folder: 선택된 폴더 경로.
        """
        # 폴더 저장
        self.save_scan_folder(folder)
        
        # Preview 스캔 시작
        self._start_preview_scan(folder)
    
    def _start_preview_scan(self, folder: Path) -> None:
        """Preview 스캔 시작.
        
        Args:
            folder: 스캔할 폴더.
        """
        # 기존 워커가 있으면 취소
        if self._preview_worker and self._preview_worker.isRunning():
            self._preview_worker.cancel()
            self._preview_worker.wait()
        
        # SettingsTab에서 설정 가져오기
        settings_tab = self._get_settings_tab()
        if settings_tab:
            extensions_str = settings_tab.get_extension_filter()
            # 확장자 문자열이 비어있으면 기본 텍스트 확장자 사용, 아니면 파싱
            if extensions_str:
                extensions = self._parse_extensions(extensions_str)
            else:
                # 비어있으면 기본 텍스트 확장자 사용
                from app.settings.constants import DEFAULT_TEXT_EXTENSIONS
                extensions = DEFAULT_TEXT_EXTENSIONS
            include_subdirs = settings_tab.get_include_subdirs()
            include_hidden = settings_tab.get_include_hidden()
            include_symlinks = settings_tab.get_include_symlinks()
        else:
            # 기본값: 기본 텍스트 확장자 사용
            from app.settings.constants import DEFAULT_TEXT_EXTENSIONS
            extensions = DEFAULT_TEXT_EXTENSIONS
            include_subdirs = True
            include_hidden = False
            include_symlinks = True
        
        # 새 워커 생성 및 시작
        self._preview_worker = PreviewWorker(
            folder=folder,
            extensions=extensions,
            include_subdirs=include_subdirs,
            include_hidden=include_hidden,
            include_symlinks=include_symlinks,
            parent=self
        )
        self._preview_worker.preview_completed.connect(self._on_preview_completed)
        self._preview_worker.preview_error.connect(self._on_preview_error)
        self._preview_worker.start()
    
    def _parse_extensions(self, extensions_str: str) -> list[str]:
        """확장자 문자열 파싱.
        
        Args:
            extensions_str: ".txt, .md, .log" 형식의 문자열.
        
        Returns:
            확장자 리스트 ['.txt', '.md', '.log'].
        """
        if not extensions_str.strip():
            return []
        
        extensions = []
        for ext in extensions_str.split(','):
            ext = ext.strip()
            if ext:
                # 점이 없으면 추가
                if not ext.startswith('.'):
                    ext = '.' + ext
                extensions.append(ext.lower())
        
        return extensions
    
    def _on_preview_completed(self, stats) -> None:
        """Preview 스캔 완료 핸들러.
        
        Args:
            stats: PreviewStats 객체.
        """
        # 헤더 통계 업데이트
        self.update_header_stats(
            total_files=stats.estimated_total_files,
            processed_files=0,
            saved_gb=0.0
        )
    
    def _on_preview_error(self, error_message: str) -> None:
        """Preview 스캔 오류 핸들러.
        
        Args:
            error_message: 오류 메시지.
        """
        # TODO: 오류 메시지를 사용자에게 표시 (로그 탭 등)
        print(f"Preview 스캔 오류: {error_message}")
    
    def _switch_tab(self, tab_name: str) -> None:
        """탭 전환."""
        # 스택에서 해당 탭 찾기
        for i in range(self._content_stack.count()):
            widget = self._content_stack.widget(i)
            if widget and widget.property("tab_name") == tab_name:
                self._content_stack.setCurrentIndex(i)
                self._app_state.current_tab = tab_name
                break
    
    def update_header_stats(self, total_files: int, processed_files: int, saved_gb: float) -> None:
        """헤더 통계 업데이트."""
        self._header.update_stats(total_files, processed_files, saved_gb)
        self._app_state.update_stats(total_files, processed_files, saved_gb)
    
    def save_scan_folder(self, folder: Path) -> None:
        """스캔 폴더를 QSettings에 저장.
        
        Args:
            folder: 저장할 폴더 경로.
        """
        self._settings.setValue(SETTINGS_KEY_SCAN_FOLDER, str(folder))
        self._app_state.scan_folder = str(folder)
