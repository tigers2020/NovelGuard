"""NovelGuard 메인 진입점.

GUI 애플리케이션을 시작합니다.
"""

# 표준 라이브러리
import sys
from pathlib import Path

# 서드파티
from PySide6.QtWidgets import QApplication

# src 폴더를 sys.path에 추가 (프로토콜의 import 예시와 일치)
src_path = Path(__file__).parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

# 로컬
from gui.views.main_window import MainWindow


def main() -> None:
    """메인 함수."""
    app = QApplication(sys.argv)
    app.setApplicationName("NovelGuard")
    app.setOrganizationName("NovelGuard")
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

