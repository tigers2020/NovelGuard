"""애플리케이션 진입점."""
import sys
from datetime import datetime
from pathlib import Path

from PySide6.QtWidgets import QApplication

from application.dto.log_entry import LogEntry
from gui.views.main_window import MainWindow
from gui.styles.dark_theme import get_dark_theme_stylesheet
from infrastructure.db.sqlite_index_repository import SQLiteIndexRepository
from infrastructure.fs.scanner import FileSystemScanner
from infrastructure.logging.in_memory_log_sink import InMemoryLogSink
from gui.services.qt_job_manager import QtJobManager


def main() -> int:
    """애플리케이션 메인 함수."""
    # QApplication 생성
    app = QApplication(sys.argv)
    app.setApplicationName("텍스트 정리 프로그램")
    app.setOrganizationName("NovelGuard")
    
    # 다크 테마 적용
    app.setStyleSheet(get_dark_theme_stylesheet())
    
    # 프로젝트 루트 찾기 (src/main.py 기준)
    # src/main.py -> src -> 프로젝트 루트
    project_root = Path(__file__).parent.parent.parent
    
    # Composition Root: 의존성 생성
    log_sink = InMemoryLogSink(log_dir=project_root / "logs")
    
    # 애플리케이션 시작 로그
    log_sink.write(LogEntry(
        timestamp=datetime.now(),
        level="INFO",
        message="애플리케이션 시작",
        context={"argv": sys.argv}
    ))
    
    index_repo = SQLiteIndexRepository(log_sink=log_sink)
    scanner = FileSystemScanner(log_sink=log_sink)
    job_manager = QtJobManager(scanner, index_repository=index_repo, log_sink=log_sink)
    
    # 메인 윈도우 생성 및 표시 (의존성 주입)
    window = MainWindow(index_repo=index_repo, log_sink=log_sink, job_manager=job_manager)
    window.show()
    
    log_sink.write(LogEntry(
        timestamp=datetime.now(),
        level="INFO",
        message="메인 윈도우 표시 완료",
        context={}
    ))
    
    # 이벤트 루프 실행
    return app.exec()
