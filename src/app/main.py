"""애플리케이션 진입점."""

import sys
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from app.factories import create_duplicate_detection_pipeline
from app.settings.constants import SETTINGS_KEY_UI_THEME
from application.dto.log_entry import LogEntry
from application.use_cases.duplicate_detection.duplicate_detection_pipeline import (
    DuplicateDetectionPipeline,
)
from gui.models.app_state import AppState
from gui.services.qt_job_manager import QtJobManager
from gui.styles.fonts import apply_application_font
from gui.styles.theme_apply import apply_theme_to_app
from gui.styles.theme_mode import ThemeMode
from gui.views.main_window import MainWindow
from infrastructure.db.sqlite_index_repository import SQLiteIndexRepository
from infrastructure.fs.scanner import FileSystemScanner
from infrastructure.logging.in_memory_log_sink import InMemoryLogSink


def main() -> int:
    """애플리케이션 메인 함수."""
    # QApplication 생성
    app = QApplication(sys.argv)
    app.setApplicationName("텍스트 정리 프로그램")
    app.setOrganizationName("NovelGuard")

    settings = QSettings()
    theme_mode = ThemeMode.from_settings_value(settings.value(SETTINGS_KEY_UI_THEME, "dark"))
    apply_application_font(app)
    apply_theme_to_app(theme_mode)

    # 프로젝트 루트 찾기 (src/main.py 기준)
    # src/main.py -> src -> 프로젝트 루트
    project_root = Path(__file__).parent.parent.parent

    # Composition Root: 의존성 생성
    log_sink = InMemoryLogSink(log_dir=project_root / "logs")

    # 애플리케이션 시작 로그
    log_sink.write(
        LogEntry(
            timestamp=datetime.now(),
            level="INFO",
            message="애플리케이션 시작",
            context={"argv": sys.argv},
        )
    )

    index_repo = SQLiteIndexRepository(log_sink=log_sink)
    scanner = FileSystemScanner(log_sink=log_sink)

    app_state = AppState()
    app_state.set_log_sink(log_sink)
    _ = app_state.file_data_store

    def duplicate_pipeline_factory() -> DuplicateDetectionPipeline:
        return create_duplicate_detection_pipeline(
            index_repository=index_repo,
            file_data_store=app_state.file_data_store,
            log_sink=log_sink,
        )

    job_manager = QtJobManager(
        scanner,
        index_repository=index_repo,
        log_sink=log_sink,
        file_data_store=app_state.file_data_store,
        duplicate_pipeline_factory=duplicate_pipeline_factory,
    )

    # 메인 윈도우 생성 및 표시 (의존성 주입)
    window = MainWindow(
        index_repo=index_repo,
        log_sink=log_sink,
        job_manager=job_manager,
        app_state=app_state,
    )
    window.show()

    log_sink.write(
        LogEntry(
            timestamp=datetime.now(), level="INFO", message="메인 윈도우 표시 완료", context={}
        )
    )

    # 이벤트 루프 실행
    return app.exec()
