"""FileRepository 구현.

file_id -> FileRecord 매핑 저장 및 조회.
"""

from typing import Optional, Iterator
from domain.models.file_record import FileRecord
from common.errors import RepositoryError
from common.logging import setup_logging

logger = setup_logging()


class FileRepository:
    """FileRepository - file_id -> FileRecord 매핑 저장."""
    
    def __init__(self) -> None:
        """FileRepository 초기화."""
        # 메모리 기반 저장소
        self._records: dict[int, FileRecord] = {}
        self._next_id: int = 1
    
    def save(self, record: FileRecord) -> FileRecord:
        """FileRecord 저장.
        
        Args:
            record: 저장할 FileRecord
        
        Returns:
            저장된 FileRecord (file_id 할당됨)
        """
        # file_id가 없으면 할당
        if record.file_id == 0:
            record = record.copy(update={"file_id": self._next_id})
            self._next_id += 1
        
        self._records[record.file_id] = record
        logger.debug(f"FileRecord 저장: file_id={record.file_id}, path={record.path}")
        return record
    
    def get(self, file_id: int) -> Optional[FileRecord]:
        """FileRecord 조회.
        
        Args:
            file_id: 파일 ID
        
        Returns:
            FileRecord 또는 None
        """
        return self._records.get(file_id)
    
    def get_by_path(self, path: str) -> Optional[FileRecord]:
        """경로로 FileRecord 조회.
        
        Args:
            path: 파일 경로
        
        Returns:
            FileRecord 또는 None
        """
        for record in self._records.values():
            if str(record.path) == path:
                return record
        return None
    
    def update(self, file_id: int, **updates) -> Optional[FileRecord]:
        """FileRecord 업데이트.
        
        Args:
            file_id: 파일 ID
            **updates: 업데이트할 필드
        
        Returns:
            업데이트된 FileRecord 또는 None
        """
        record = self.get(file_id)
        if not record:
            return None
        
        updated = record.copy(update=updates)
        self._records[file_id] = updated
        logger.debug(f"FileRecord 업데이트: file_id={file_id}")
        return updated
    
    def delete(self, file_id: int) -> bool:
        """FileRecord 삭제.
        
        Args:
            file_id: 파일 ID
        
        Returns:
            삭제 성공 여부
        """
        if file_id in self._records:
            del self._records[file_id]
            logger.debug(f"FileRecord 삭제: file_id={file_id}")
            return True
        return False
    
    def list_all(self) -> Iterator[FileRecord]:
        """모든 FileRecord 조회.
        
        Yields:
            FileRecord
        """
        for record in self._records.values():
            yield record
    
    def count(self) -> int:
        """저장된 레코드 수 반환.
        
        Returns:
            레코드 수
        """
        return len(self._records)
    
    def clear(self) -> None:
        """모든 레코드 삭제."""
        self._records.clear()
        logger.debug("FileRepository 초기화")

