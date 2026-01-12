"""FileListTable 컴포넌트 상수 정의."""
from typing import Final

from PySide6.QtCore import Qt


class FileListColumns:
    """FileListTable 컬럼 인덱스 상수.
    
    테이블의 컬럼 구조를 정의합니다.
    모든 컬럼 인덱스는 여기서 중앙 관리됩니다.
    """
    
    FILE_NAME: Final[int] = 0
    """파일명 컬럼 (FileData 저장)."""
    
    FILE_PATH: Final[int] = 1
    """경로 컬럼."""
    
    FILE_SIZE: Final[int] = 2
    """크기 컬럼."""
    
    MODIFIED_AT: Final[int] = 3
    """수정일 컬럼."""
    
    EXTENSION: Final[int] = 4
    """확장자 컬럼."""
    
    ENCODING: Final[int] = 5
    """인코딩 컬럼."""
    
    DUPLICATE_GROUP: Final[int] = 6
    """중복 그룹 컬럼 (delegate 사용)."""
    
    CANONICAL: Final[int] = 7
    """대표 파일 컬럼 (delegate 사용)."""
    
    INTEGRITY: Final[int] = 8
    """무결성 컬럼."""
    
    ATTRIBUTES: Final[int] = 9
    """속성 컬럼."""
    
    TOTAL_COLUMNS: Final[int] = 10
    """전체 컬럼 수."""
    
    # Delegate 사용 컬럼
    DELEGATE_COLUMNS: Final[tuple[int, int]] = (DUPLICATE_GROUP, CANONICAL)
    """Delegate를 사용하는 컬럼 인덱스 튜플."""
    
    # 정렬 비활성화 컬럼
    NO_SORT_COLUMNS: Final[tuple[int, int]] = (DUPLICATE_GROUP, CANONICAL)
    """정렬이 비활성화된 컬럼 인덱스 튜플."""


class FileListRoles:
    """FileListTable Qt Role 상수.
    
    QTableWidgetItem의 data()/setData()에서 사용하는 Role 값을 정의합니다.
    Qt.UserRole 이상의 값만 사용합니다.
    """
    
    FILE_DATA: Final[int] = int(Qt.UserRole) + 1
    """FileData 저장 Role (0번 컬럼: 파일명에 FileData 저장)."""
    
    SORT_VALUE: Final[int] = int(Qt.UserRole) + 2
    """정렬용 원본 값 저장 Role (2번 컬럼: 크기, 3번 컬럼: 수정일)."""


class FileListUpdatePolicy:
    """FileListTable 업데이트 정책 상수.
    
    배치 처리 및 성능 튜닝 관련 상수를 정의합니다.
    """
    
    BATCH_TIMER_INTERVAL_MS: Final[int] = 50
    """배치 타이머 간격 (밀리초)."""
    
    # CHUNK_SIZE는 향후 추가 예정 (현재 코드에서 미사용)
