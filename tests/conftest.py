"""Pytest 설정 파일."""

import sys
from pathlib import Path

# `pytest tests`처럼 testpaths를 우회할 때도 레거시 트리를 수집하지 않도록 한다.
# 경로는 이 파일이 있는 `tests/` 기준 상대 경로.
collect_ignore = [
    "_archive",
    "app/test_bootstrap.py",
    "app/test_workflows.py",
    "common",
    "domain",
    "infra",
]

# src 디렉토리를 sys.path에 추가
src_path = Path(__file__).parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))
