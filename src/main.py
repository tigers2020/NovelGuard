"""
NovelGuard 메인 모듈

GUI 애플리케이션의 진입점입니다.
"""

import sys
import logging
import io
from pathlib import Path

# Windows에서 콘솔 출력 인코딩을 UTF-8로 설정
if sys.platform == "win32":
    # 표준 출력/에러 스트림을 UTF-8로 설정
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    # 콘솔 코드 페이지를 UTF-8로 변경 (Windows)
    try:
        import os
        os.system("chcp 65001 >nul 2>&1")
    except Exception:
        pass

# src 디렉토리를 Python 경로에 추가
# 이 파일이 src/main.py에 있으므로, src 디렉토리의 부모를 경로에 추가
src_dir = Path(__file__).parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

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

