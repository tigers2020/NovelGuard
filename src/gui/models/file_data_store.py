"""공유 파일 데이터 저장소."""
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, Signal

from domain.entities.file_entry import FileEntry


@dataclass
class FileData:
    """파일 데이터 (확장된 정보 포함)."""
    
    entry: FileEntry
    """기본 파일 엔트리."""
    
    file_id: int
    """파일 ID (고유 식별자)."""
    
    # 중복 관련
    duplicate_group_id: Optional[int] = None
    """중복 그룹 ID (None이면 중복 아님)."""
    
    is_canonical: bool = False
    """대표 파일 여부 (중복 그룹에서)."""
    
    similarity_score: Optional[float] = None
    """유사도 점수 (0.0 ~ 1.0)."""
    
    # 무결성 관련
    integrity_issues: list[str] = field(default_factory=list)
    """무결성 이슈 메시지 리스트."""
    
    integrity_severity: Optional[str] = None
    """가장 심각한 무결성 이슈 심각도 (INFO, WARN, ERROR)."""
    
    # 인코딩 관련
    encoding: Optional[str] = None
    """감지된 인코딩."""
    
    encoding_confidence: Optional[float] = None
    """인코딩 감지 신뢰도 (0.0 ~ 1.0)."""
    
    @property
    def path(self) -> Path:
        """파일 경로."""
        return self.entry.path
    
    @property
    def size(self) -> int:
        """파일 크기."""
        return self.entry.size
    
    @property
    def mtime(self) -> datetime:
        """수정 시간."""
        return self.entry.mtime
    
    @property
    def extension(self) -> str:
        """확장자."""
        return self.entry.extension


class FileDataStore(QObject):
    """공유 파일 데이터 저장소."""
    
    # 시그널
    file_added = Signal(FileData)
    """파일 추가 시그널 (단일 파일)."""
    
    files_added_batch = Signal(list)  # list[FileData]
    """파일 추가 시그널 (배치)."""
    
    file_updated = Signal(FileData)
    """파일 업데이트 시그널."""
    
    files_cleared = Signal()
    """모든 파일 삭제 시그널."""
    
    data_changed = Signal()
    """데이터 변경 시그널."""
    
    def __init__(self, parent: Optional[QObject] = None) -> None:
        """파일 데이터 저장소 초기화."""
        super().__init__(parent)
        
        # 파일 데이터 저장 (file_id -> FileData)
        self._files: dict[int, FileData] = {}
        
        # 스캔 폴더
        self._scan_folder: Optional[Path] = None
        
        # 다음 파일 ID
        self._next_file_id: int = 1
    
    @property
    def scan_folder(self) -> Optional[Path]:
        """스캔 폴더 반환."""
        return self._scan_folder
    
    @scan_folder.setter
    def scan_folder(self, value: Optional[Path]) -> None:
        """스캔 폴더 설정."""
        self._scan_folder = value
    
    def clear(self) -> None:
        """모든 파일 데이터 삭제."""
        self._files.clear()
        self._next_file_id = 1
        self._scan_folder = None
        self.files_cleared.emit()
        self.data_changed.emit()
    
    def add_file(self, entry: FileEntry) -> FileData:
        """파일 추가.
        
        Args:
            entry: 파일 엔트리.
        
        Returns:
            생성된 FileData 객체.
        """
        file_id = self._next_file_id
        self._next_file_id += 1
        
        file_data = FileData(
            entry=entry,
            file_id=file_id
        )
        
        self._files[file_id] = file_data
        self.file_added.emit(file_data)
        self.data_changed.emit()
        
        return file_data
    
    def add_files(self, entries: list[FileEntry]) -> list[FileData]:
        """여러 파일 추가 (배치 처리).
        
        Args:
            entries: 파일 엔트리 리스트.
        
        Returns:
            생성된 FileData 객체 리스트.
        """
        if not entries:
            return []
        
        file_data_list = []
        for entry in entries:
            file_id = self._next_file_id
            self._next_file_id += 1
            
            file_data = FileData(
                entry=entry,
                file_id=file_id
            )
            
            self._files[file_id] = file_data
            file_data_list.append(file_data)
        
        # 배치 시그널만 emit (개별 시그널은 emit하지 않음)
        self.files_added_batch.emit(file_data_list)
        self.data_changed.emit()
        
        return file_data_list
    
    def get_file(self, file_id: int) -> Optional[FileData]:
        """파일 데이터 반환.
        
        Args:
            file_id: 파일 ID.
        
        Returns:
            FileData 객체. 없으면 None.
        """
        return self._files.get(file_id)
    
    def get_all_files(self) -> list[FileData]:
        """모든 파일 데이터 반환.
        
        Returns:
            FileData 리스트.
        """
        return list(self._files.values())
    
    def update_file(self, file_id: int, **kwargs) -> Optional[FileData]:
        """파일 데이터 업데이트.
        
        Args:
            file_id: 파일 ID.
            **kwargs: 업데이트할 필드들.
        
        Returns:
            업데이트된 FileData 객체. 없으면 None.
        """
        file_data = self._files.get(file_id)
        if not file_data:
            return None
        
        # 필드 업데이트
        for key, value in kwargs.items():
            if hasattr(file_data, key):
                setattr(file_data, key, value)
        
        self.file_updated.emit(file_data)
        self.data_changed.emit()
        
        return file_data
    
    def set_duplicate_group(self, file_id: int, group_id: Optional[int], 
                           is_canonical: bool = False, 
                           similarity_score: Optional[float] = None) -> None:
        """중복 그룹 정보 설정.
        
        Args:
            file_id: 파일 ID.
            group_id: 중복 그룹 ID (None이면 중복 아님).
            is_canonical: 대표 파일 여부.
            similarity_score: 유사도 점수.
        """
        self.update_file(
            file_id,
            duplicate_group_id=group_id,
            is_canonical=is_canonical,
            similarity_score=similarity_score
        )
    
    def add_integrity_issue(self, file_id: int, message: str, severity: str) -> None:
        """무결성 이슈 추가.
        
        Args:
            file_id: 파일 ID.
            message: 이슈 메시지.
            severity: 심각도 (INFO, WARN, ERROR).
        """
        file_data = self._files.get(file_id)
        if not file_data:
            return
        
        file_data.integrity_issues.append(message)
        
        # 가장 심각한 이슈로 업데이트
        severity_order = {"ERROR": 3, "WARN": 2, "INFO": 1}
        current_severity_order = severity_order.get(file_data.integrity_severity, 0)
        new_severity_order = severity_order.get(severity, 0)
        
        if new_severity_order > current_severity_order:
            file_data.integrity_severity = severity
        
        self.file_updated.emit(file_data)
        self.data_changed.emit()
    
    def set_encoding(self, file_id: int, encoding: str, confidence: Optional[float] = None) -> None:
        """인코딩 정보 설정.
        
        Args:
            file_id: 파일 ID.
            encoding: 인코딩 이름.
            confidence: 인코딩 감지 신뢰도.
        """
        self.update_file(
            file_id,
            encoding=encoding,
            encoding_confidence=confidence
        )
    
    def get_file_count(self) -> int:
        """파일 수 반환.
        
        Returns:
            파일 수.
        """
        return len(self._files)
