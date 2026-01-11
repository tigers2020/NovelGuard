"""Pytest 설정 파일."""

import sys
from pathlib import Path

# src 디렉토리를 sys.path에 추가
src_path = Path(__file__).parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))
