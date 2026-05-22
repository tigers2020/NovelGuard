"""메인 윈도우."""

from pathlib import Path
from typing import Optional

from PySide6.QtCore import QSettings, QTimer
from PySide6.QtWidgets import (
    QHBoxLayout,
    QMainWindow,
    QMessageBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.settings.constants import SETTINGS_KEY_SCAN_FOLDER
from application.utils.debug_logger import debug_step
from application.utils.extensions import parse_extensions
from gui.models.app_state import AppState
from gui.services.work_stats import compute_work_stats
from gui.view_models.work_view_model import WorkViewModel
from gui.views.components.file_list_table import FileListTableWidget
from gui.views.components.global_action_toolbar import GlobalActionToolbar
from gui.views.components.header import HeaderWidget
from gui.views.components.sidebar import SidebarWidget
from gui.views.work.work_tab import WorkTab
from gui.workers.preview_worker import PreviewWorker


class MainWindow(QMainWindow):
    """메인 윈도우."""

    def __init__(
        self,
        index_repo=None,
        log_sink=None,
        job_manager=None,
        app_state: Optional[AppState] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        """메인 윈도우 초기화.

        Args:
            index_repo: 인덱스 저장소 (선택적).
            log_sink: 로그 싱크 (선택적).
            job_manager: Job 관리자 (선택적, 추후 구현).
            app_state: 앱 전역 상태 (없으면 내부에서 생성).
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

        # 애플리케이션 상태 (composition root에서 주입 가능)
        self._app_state = app_state if app_state is not None else AppState()
        self._app_state.set_log_sink(self._log_sink)

        # QSettings
        self._settings = QSettings()

        # Preview 워커
        self._preview_worker: Optional[PreviewWorker] = None

        # UI 설정
        self._setup_ui()
        debug_step(self._log_sink, "main_window_ui_setup_complete")

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

        self._action_toolbar = GlobalActionToolbar(self)
        main_layout.addWidget(self._action_toolbar)

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

        self._content_stack = QStackedWidget()
        self._content_stack.setObjectName("contentArea")
        center_layout.addWidget(self._content_stack, stretch=1)

        content_layout.addWidget(center_widget, stretch=1)

        main_layout.addWidget(content_widget, stretch=1)

        # 탭 뷰들을 스택에 추가 (나중에 구현될 탭들)
        self._setup_tabs()

    def _setup_tabs(self) -> None:
        """탭 뷰 설정 (work · logs · settings)."""
        from gui.views.tabs.logs_tab import LogsTab
        from gui.views.tabs.settings_tab import SettingsTab

        self._work_tab = WorkTab(
            self,
            job_manager=self._job_manager,
            index_repository=self._index_repo,
            log_sink=self._log_sink,
            app_state=self._app_state,
        )
        self._work_view_model = WorkViewModel(
            self._app_state,
            job_manager=self._job_manager,
            log_sink=self._log_sink,
        )
        self._work_tab.bind_work_view_model(self._work_view_model)
        self._work_tab.bind_main_window(self)
        self._file_list_table = FileListTableWidget(self._app_state.file_data_store, self._work_tab)
        self._work_tab.set_file_list_table(self._file_list_table)

        tabs = {
            "work": self._work_tab,
            "logs": LogsTab(self, log_sink=self._log_sink),
            "settings": SettingsTab(self),
        }

        for tab_name, tab_widget in tabs.items():
            self._content_stack.addWidget(tab_widget)
            tab_widget.setProperty("tab_name", tab_name)

        self._switch_tab("work")

    def _get_work_tab(self) -> Optional[WorkTab]:
        return getattr(self, "_work_tab", None)

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

        work_tab = self._get_work_tab()
        if work_tab:
            work_tab.library_section.folder_selected.connect(self._on_folder_selected)

        # FileDataStore 시그널 연결 (통계 자동 업데이트)
        file_data_store = self._app_state.file_data_store
        file_data_store.files_added_batch.connect(self._on_file_data_changed)
        file_data_store.files_cleared.connect(self._on_file_data_changed)
        file_data_store.files_removed.connect(self._on_file_data_changed)
        file_data_store.files_updated_batch.connect(self._on_file_data_changed)
        file_data_store.files_added_batch.connect(self._on_work_summary_refresh)
        file_data_store.files_cleared.connect(self._on_work_summary_refresh)
        file_data_store.files_removed.connect(self._on_work_summary_refresh)
        file_data_store.files_updated_batch.connect(self._on_work_summary_refresh)

        # 초기 통계 업데이트
        self._update_header_stats_from_store()
        self._on_work_summary_refresh()

    def _restore_settings(self) -> None:
        """이전 설정 복원."""
        # 마지막 선택 폴더 복원
        last_folder = self._settings.value(SETTINGS_KEY_SCAN_FOLDER, None)
        if last_folder:
            folder_path = Path(str(last_folder))
            if folder_path.exists() and folder_path.is_dir():
                self._app_state.scan_folder = str(folder_path)
                work_tab = self._get_work_tab()
                if work_tab:
                    work_tab.library_section.set_scan_folder(folder_path)
                    work_tab.refresh_move_folder()

    def _auto_start_preview_scan(self) -> None:
        """자동 Preview 스캔 시작 (프로그램 시작 시).

        마지막 폴더가 있으면 100ms 후 자동으로 Preview 스캔 시작.
        """
        last_folder = self._settings.value(SETTINGS_KEY_SCAN_FOLDER, None)
        if last_folder:
            folder_path = Path(str(last_folder))
            if folder_path.exists() and folder_path.is_dir():
                # UI가 완전히 로드된 후 실행
                QTimer.singleShot(100, lambda: self._start_preview_scan(folder_path))

    def _on_folder_selected(self, folder: Path) -> None:
        """폴더 선택 핸들러."""
        debug_step(self._log_sink, "on_folder_selected", {"folder": str(folder)})
        self.save_scan_folder(folder)
        work_tab = self._get_work_tab()
        if work_tab:
            work_tab.refresh_move_folder()
        self._start_preview_scan(folder)

    def _on_work_summary_refresh(self, *args) -> None:
        if hasattr(self, "_work_view_model"):
            self._work_view_model.refresh()

    def _start_preview_scan(self, folder: Path) -> None:
        """Preview 스캔 시작.

        Args:
            folder: 스캔할 폴더.
        """
        debug_step(self._log_sink, "start_preview_scan", {"folder": str(folder)})
        if hasattr(self, "_work_view_model"):
            self._work_view_model.set_preview_running(True)
        work_tab = self._get_work_tab()
        if work_tab:
            work_tab.library_section.set_preview_status("진행 중...")

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
            parent=self,
        )
        self._preview_worker.preview_completed.connect(self._on_preview_completed)
        self._preview_worker.preview_error.connect(self._on_preview_error)
        self._preview_worker.start()

    def _on_preview_completed(self, stats) -> None:
        """Preview 스캔 완료 핸들러."""
        debug_step(
            self._log_sink,
            "on_preview_completed",
            {"estimated_total_files": stats.estimated_total_files},
        )
        if hasattr(self, "_work_view_model"):
            self._work_view_model.set_preview_running(False)
        work_tab = self._get_work_tab()
        if work_tab:
            work_tab.library_section.set_preview_status(
                f"약 {stats.estimated_total_files:,}개 파일 (추정)"
            )

        self._update_work_context_stats(
            total_files=stats.estimated_total_files,
            duplicate_groups=0,
            saved_gb=0.0,
            integrity_issues=0,
        )

    def _on_preview_error(self, error_message: str) -> None:
        """Preview 스캔 오류 핸들러."""
        if hasattr(self, "_work_view_model"):
            self._work_view_model.set_preview_running(False)
        work_tab = self._get_work_tab()
        if work_tab:
            work_tab.library_section.set_preview_status("오류")
        # 에러 메시지 다이얼로그 표시
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Icon.Warning)
        msg_box.setWindowTitle("Preview 스캔 오류")
        msg_box.setText(
            "Preview 스캔 중 오류가 발생했습니다.\n\n로그 탭에서 자세한 내용을 확인할 수 있습니다."
        )
        msg_box.setDetailedText(error_message)

        # Yes/No 버튼 사용 (Yes = 로그 탭 열기, No = 닫기)
        msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
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

    def _on_file_data_changed(self, *args) -> None:
        """FileDataStore 데이터 변경 핸들러."""
        self._update_header_stats_from_store()

    def _update_header_stats_from_store(self) -> None:
        """FileDataStore에서 통계를 계산하여 WorkContextBar 갱신."""
        work_stats = compute_work_stats(self._app_state.file_data_store)
        self._update_work_context_stats(
            total_files=work_stats.total_files,
            duplicate_groups=work_stats.duplicate_groups,
            saved_gb=work_stats.saved_gb,
            integrity_issues=work_stats.integrity_issues,
        )
        self._app_state.update_stats(
            work_stats.total_files,
            work_stats.processed_files,
            work_stats.saved_gb,
        )

    def _update_work_context_stats(
        self,
        total_files: int,
        duplicate_groups: int,
        saved_gb: float,
        integrity_issues: int,
    ) -> None:
        debug_step(
            self._log_sink,
            "update_work_context_stats",
            {
                "total_files": total_files,
                "saved_gb": saved_gb,
                "duplicate_groups": duplicate_groups,
                "integrity_issues": integrity_issues,
            },
        )
        if hasattr(self, "_work_view_model"):
            self._work_view_model.refresh()

    def save_scan_folder(self, folder: Path) -> None:
        """스캔 폴더를 QSettings에 저장.

        Args:
            folder: 저장할 폴더 경로.
        """
        debug_step(self._log_sink, "save_scan_folder", {"folder": str(folder)})
        self._settings.setValue(SETTINGS_KEY_SCAN_FOLDER, str(folder))
        self._app_state.scan_folder = str(folder)
