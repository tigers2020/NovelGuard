"""공통 타입 정의."""

from typing import TypeAlias, Optional
from pathlib import Path

# 파일 경로 타입
FilePath: TypeAlias = Path | str

# 파일 ID 타입
FileID: TypeAlias = int

# 그룹 ID 타입
GroupID: TypeAlias = int

# 이슈 ID 타입
IssueID: TypeAlias = int

# 액션 ID 타입
ActionID: TypeAlias = int

# 증거 ID 타입
EvidenceID: TypeAlias = int

# 해시 값 타입
HashValue: TypeAlias = str

# 지문 값 타입
FingerprintValue: TypeAlias = str | int | bytes

