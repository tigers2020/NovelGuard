"""메인 윈도우."""
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QSettings, Qt, QTimer
from PySide6.QtWidgets import (
    QHBoxLayout,
    QMainWindow,
    QMessageBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.settings.constants import Constants, SETTINGS_KEY_SCAN_FOLDER
from application.utils.extensions import parse_extensions
from application.utils.debug_logger import debug_step
from gui.models.app_state import AppState
from gui.styles.dark_theme import get_dark_theme_stylesheet
from gui.views.components.file_list_table import FileListTableWidget
from gui.views.components.header import HeaderWidget
from gui.views.components.sidebar import SidebarWidget
from gui.workers.preview_worker import PreviewWorker


class MainWindow(QMainWindow):
    """메인 윈도우."""
    
    def __init__(
        self,
        index_repo=None,
        log_sink=None,
        job_manager=None,
        parent: Optional[QWidget] = None
    ) -> None:
        """메인 윈도우 초기화.
        
        Args:
            index_repo: 인덱스 저장소 (선택적).
            log_sink: 로그 싱크 (선택적).
            job_manager: Job 관리자 (선택적, 추후 구현).
            parent: 부모 위젯.
        """
        super().__init__(parent)
        
        # 의존성 저장 (debug_step 호출 전에 먼저 할당)
        self._index_repo = index_repo
        self._log_sink = log_sink
        self._job_manager = job_manager
        
        debug_step(self._log_sink, "main_window_init_start")
        
        self.setWindowTitle("텍스트 정리 프로그램")
        self.setMinimumSize(1400, 800)
        
        # 애플리케이션 상태
        self._app_state = AppState()
        self._app_state.set_log_sink(self._log_sink)
        
        # QSettings
        self._settings = QSettings()
        
        # Preview 워커
        self._preview_worker: Optional[PreviewWorker] = None
        
        # 다크 테마 적용
        self.setStyleSheet(get_dark_theme_stylesheet())
        debug_step(self._log_sink, "main_window_theme_applied")
        
        # UI 설정
        self._setup_ui()
        debug_step(self._log_sink, "main_window_ui_setup_complete")
        
        # JobManager에 FileDataStore 설정
        if self._job_manager and hasattr(self._job_manager, 'set_file_data_store'):
            self._job_manager.set_file_data_store(self._app_state.file_data_store)
        
        # 이벤트 연결
        self._connect_signals()
        debug_step(self._log_sink, "main_window_signals_connected")
        
        # 이전 설정 복원 및 자동 Preview 스캔
        self._restore_settings()
        debug_step(self._log_sink, "main_window_settings_restored")
        self._auto_start_preview_scan()
        debug_step(self._log_sink, "main_window_init_complete")
    
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
        
        # ScanTab과 LogsTab에 deps 전달 (다른 탭은 추후 추가)
        tabs = {
            "scan": ScanTab(self, job_manager=self._job_manager, log_sink=self._log_sink),
            "duplicate": DuplicateTab(self, job_manager=self._job_manager, index_repository=self._index_repo, log_sink=self._log_sink),
            "small": SmallFileTab(self),
            "integrity": IntegrityTab(self),
            "encoding": EncodingTab(self),
            "stats": StatsTab(self, index_repo=self._index_repo, log_sink=self._log_sink),
            "logs": LogsTab(self, log_sink=self._log_sink),
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
        
        # FileDataStore 시그널 연결 (통계 자동 업데이트)
        file_data_store = self._app_state.file_data_store
        file_data_store.files_added_batch.connect(self._on_file_data_changed)
        file_data_store.files_cleared.connect(self._on_file_data_changed)
        file_data_store.files_removed.connect(self._on_file_data_changed)
        file_data_store.files_updated_batch.connect(self._on_file_data_changed)
        
        # 초기 통계 업데이트
        self._update_header_stats_from_store()
    
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
        debug_step(self._log_sink, "on_folder_selected", {"folder": str(folder)})
        
        # 폴더 저장
        self.save_scan_folder(folder)
        
        # Preview 스캔 시작
        self._start_preview_scan(folder)
    
    def _start_preview_scan(self, folder: Path) -> None:
        """Preview 스캔 시작.
        
        Args:
            folder: 스캔할 폴더.
        """
        debug_step(self._log_sink, "start_preview_scan", {"folder": str(folder)})
        
        # 기존 워커가 있으면 취소
        if self._preview_worker and self._preview_worker.isRunning():
            debug_step(self._log_sink, "preview_worker_cancelling_existing")
            self._preview_worker.cancel()
            self._preview_worker.wait()
        
        # SettingsTab에서 설정 가져오기
        settings_tab = self._get_settings_tab()
        if settings_tab:
            extensions_str = settings_tab.get_extension_filter()
            # 확장자 문자열 파싱 (빈 문자열이면 기본 텍스트 확장자 사용)
            parsed_extensions = parse_extensions(extensions_str)
            if parsed_extensions:
                extensions = parsed_extensions
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
            log_sink=self._log_sink,
            parent=self
        )
        self._preview_worker.preview_completed.connect(self._on_preview_completed)
        self._preview_worker.preview_error.connect(self._on_preview_error)
        self._preview_worker.start()
    
    
    def _on_preview_completed(self, stats) -> None:
        """Preview 스캔 완료 핸들러.
        
        Args:
            stats: PreviewStats 객체.
        """
        debug_step(
            self._log_sink,
            "on_preview_completed",
            {"estimated_total_files": stats.estimated_total_files}
        )
        
        # 헤더 통계 업데이트
        self.update_header_stats(
            total_files=stats.estimated_total_files,
            processed_files=0,
            saved_gb=0.0,
            duplicate_groups=0,
            total_size_gb=0.0,
            integrity_issues=0,
            duplicate_files=0,
            small_files=0
        )
    
    def _on_preview_error(self, error_message: str) -> None:
        """Preview 스캔 오류 핸들러.
        
        Args:
            error_message: 오류 메시지.
        """
        # 에러 메시지 다이얼로그 표시
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Icon.Warning)
        msg_box.setWindowTitle("Preview 스캔 오류")
        msg_box.setText("Preview 스캔 중 오류가 발생했습니다.\n\n로그 탭에서 자세한 내용을 확인할 수 있습니다.")
        msg_box.setDetailedText(error_message)
        
        # Yes/No 버튼 사용 (Yes = 로그 탭 열기, No = 닫기)
        msg_box.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        msg_box.button(QMessageBox.StandardButton.Yes).setText("로그 탭 열기")
        msg_box.button(QMessageBox.StandardButton.No).setText("닫기")
        
        result = msg_box.exec()
        
        # "로그 탭 열기" 버튼이 클릭된 경우
        if result == QMessageBox.StandardButton.Yes:
            self._switch_tab("logs")
    
    def _switch_tab(self, tab_name: str) -> None:
        """탭 전환."""
        debug_step(self._log_sink, "switch_tab", {"tab_name": tab_name})
        
        # 스택에서 해당 탭 찾기
        for i in range(self._content_stack.count()):
            widget = self._content_stack.widget(i)
            if widget and widget.property("tab_name") == tab_name:
                self._content_stack.setCurrentIndex(i)
                self._app_state.current_tab = tab_name
                break
    
    def _calculate_stats(self) -> tuple[int, int, float, int, float, int, int, int]:
        """통계 계산.
        
        Returns:
            (total_files, processed_files, saved_gb, duplicate_groups, 
             total_size_gb, integrity_issues, duplicate_files, small_files) 튜플.
        """
        file_data_store = self._app_state.file_data_store
        all_files = file_data_store.get_all_files()
        
        # 총 파일 수
        total_files = len(all_files)
        
        # 처리 완료 (중복 탐지 완료된 파일 = duplicate_group_id가 None이 아닌 파일)
        processed_files = sum(1 for f in all_files if f.duplicate_group_id is not None)
        
        # 절감 용량 (중복 파일 중 제거 가능한 파일들의 크기 = is_canonical=False인 중복 파일들의 크기 합)
        saved_bytes = sum(
            f.size for f in all_files 
            if f.duplicate_group_id is not None and not f.is_canonical
        )
        saved_gb = saved_bytes / Constants.BYTES_PER_GB  # GB 변환
        
        # 중복 그룹 수 (고유한 duplicate_group_id의 개수)
        duplicate_group_ids = {f.duplicate_group_id for f in all_files if f.duplicate_group_id is not None}
        duplicate_groups = len(duplicate_group_ids)
        
        # 총 용량 (모든 파일의 총 크기)
        total_bytes = sum(f.size for f in all_files)
        total_size_gb = total_bytes / Constants.BYTES_PER_GB  # GB 변환
        
        # 무결성 이슈 파일 수 (ERROR 또는 WARN 심각도)
        integrity_issues = sum(
            1 for f in all_files 
            if f.integrity_severity in ("ERROR", "WARN")
        )
        
        # 중복 파일 수 (제거 가능한 파일 수)
        duplicate_files = sum(
            1 for f in all_files 
            if f.duplicate_group_id is not None and not f.is_canonical
        )
        
        # 작은 파일 수 (1KB 미만, 기본 임계값)
        small_files = sum(1 for f in all_files if f.size < Constants.SMALL_FILE_THRESHOLD)
        
        return (total_files, processed_files, saved_gb, duplicate_groups, 
                total_size_gb, integrity_issues, duplicate_files, small_files)
    
    def _on_file_data_changed(self, *args) -> None:
        """FileDataStore 데이터 변경 핸들러."""
        self._update_header_stats_from_store()
    
    def _update_header_stats_from_store(self) -> None:
        """FileDataStore에서 통계를 계산하여 HeaderWidget 업데이트."""
        stats = self._calculate_stats()
        self.update_header_stats(*stats)
    
    def update_header_stats(
        self,
        total_files: int,
        processed_files: int,
        saved_gb: float,
        duplicate_groups: int,
        total_size_gb: float,
        integrity_issues: int,
        duplicate_files: int,
        small_files: int
    ) -> None:
        """헤더 통계 업데이트."""
        debug_step(
            self._log_sink,
            "update_header_stats",
            {
                "total_files": total_files,
                "processed_files": processed_files,
                "saved_gb": saved_gb,
                "duplicate_groups": duplicate_groups,
                "total_size_gb": total_size_gb,
                "integrity_issues": integrity_issues,
                "duplicate_files": duplicate_files,
                "small_files": small_files,
            }
        )
        
        self._header.update_stats(
            total_files, processed_files, saved_gb,
            duplicate_groups, total_size_gb, integrity_issues,
            duplicate_files, small_files
        )
        # AppState는 기존 3개만 저장 (호환성 유지)
        self._app_state.update_stats(total_files, processed_files, saved_gb)
    
    def save_scan_folder(self, folder: Path) -> None:
        """스캔 폴더를 QSettings에 저장.
        
        Args:
            folder: 저장할 폴더 경로.
        """
        debug_step(self._log_sink, "save_scan_folder", {"folder": str(folder)})
        self._settings.setValue(SETTINGS_KEY_SCAN_FOLDER, str(folder))
        self._app_state.scan_folder = str(folder)
