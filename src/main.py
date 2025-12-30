"""
NovelGuard 메인 모듈

GUI 애플리케이션의 진입점입니다.
"""

import sys
import logging
from pathlib import Path

from PySide6.QtWidgets import QApplication

from gui.main_window import MainWindow
from utils.logger import setup_logger


def main() -> None:
    """메인 함수.
    
    PySide6 애플리케이션을 초기화하고 메인 윈도우를 표시합니다.
    """
    # 로거 초기화 (애플리케이션 시작 시)
    log_file = Path.home() / ".novelguard" / "novelguard.log"
    setup_logger("NovelGuard", log_file=log_file, level=logging.INFO)
    logger = setup_logger("NovelGuard.Main")
    logger.info("NovelGuard 애플리케이션 시작")
    
    app = QApplication(sys.argv)
    
    # 애플리케이션 메타데이터 설정
    app.setApplicationName("NovelGuard")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("NovelGuard")
    
    try:
        # 메인 윈도우 생성 및 표시
        window = MainWindow()
        window.show()
        
        logger.info("메인 윈도우 표시 완료")
        
        # 이벤트 루프 실행
        exit_code = app.exec()
        logger.info(f"애플리케이션 종료 (코드: {exit_code})")
        sys.exit(exit_code)
    except Exception as e:
        logger.critical(f"애플리케이션 실행 중 치명적 오류: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

