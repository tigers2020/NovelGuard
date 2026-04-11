"""애플리케이션 메인 진입점."""

import sys
from pathlib import Path

src_path = Path(__file__).parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from app.main import main  # noqa: E402 — sys.path 설정 후 import

if __name__ == "__main__":
    sys.exit(main())
