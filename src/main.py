"""애플리케이션 메인 진입점."""
import sys
from pathlib import Path

# src를 Python path에 추가
src_path = Path(__file__).parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

# app.main 실행
from app.main import main

if __name__ == "__main__":
    sys.exit(main())
