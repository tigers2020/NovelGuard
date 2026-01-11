"""애플리케이션 진입점."""
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from gui.views.main_window import MainWindow
from gui.styles.dark_theme import get_dark_theme_stylesheet


def main() -> int:
    """애플리케이션 메인 함수."""
    # QApplication 생성
    app = QApplication(sys.argv)
    app.setApplicationName("텍스트 정리 프로그램")
    app.setOrganizationName("NovelGuard")
    
    # 다크 테마 적용
    app.setStyleSheet(get_dark_theme_stylesheet())
    
    # 메인 윈도우 생성 및 표시
    window = MainWindow()
    window.show()
    
    # 이벤트 루프 실행
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
