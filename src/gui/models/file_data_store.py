"""공유 파일 데이터 저장소."""
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, TYPE_CHECKING

from PySide6.QtCore import QObject, Signal

from domain.entities.file_entry import FileEntry

if TYPE_CHECKING:
    from application.ports.log_sink import ILogSink


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
    
    files_updated_batch = Signal(list)  # list[int] of file_ids
    """파일 업데이트 시그널 (배치)."""
    
    files_cleared = Signal()
    """모든 파일 삭제 시그널."""
    
    files_removed = Signal(list)  # list[int] of file_ids
    """파일 제거 시그널 (file_id 리스트)."""
    
    data_changed = Signal()
    """데이터 변경 시그널."""
    
    def __init__(
        self,
        parent: Optional[QObject] = None,
        log_sink: Optional["ILogSink"] = None
    ) -> None:
        """파일 데이터 저장소 초기화.
        
        Args:
            parent: 부모 객체.
            log_sink: 로그 싱크 (선택적).
        """
        super().__init__(parent)
        
        self._log_sink = log_sink
        
        # 파일 데이터 저장 (file_id -> FileData)
        self._files: dict[int, FileData] = {}
        
        # 경로 → file_id 인덱스 (Windows 대소문자 무시를 위해 lower() 사용)
        self._path_to_id: dict[str, int] = {}
        
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
        if self._log_sink:
            from application.utils.debug_logger import debug_step
            debug_step(
                self._log_sink,
                "file_data_store_clear",
                {"files_count": len(self._files)}
            )
        
        self._files.clear()
        self._path_to_id.clear()
        self._next_file_id = 1
        self._scan_folder = None
        self.files_cleared.emit()
        self.data_changed.emit()
    
    def remove_files(self, file_ids: list[int]) -> None:
        """여러 파일 제거.
        
        Args:
            file_ids: 제거할 파일 ID 리스트.
        """
        if not file_ids:
            return
        
        removed_count = 0
        for file_id in file_ids:
            file_data = self._files.get(file_id)
            if file_data:
                # 경로 인덱스에서 제거
                path_key = self._normalize_path_key(file_data.entry.path)
                self._path_to_id.pop(path_key, None)
                # 파일 데이터 제거
                self._files.pop(file_id, None)
                removed_count += 1
        
        if removed_count > 0:
            # 파일 제거 시그널 emit
            self.files_removed.emit(file_ids)
    
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
        
        # 경로 인덱스 추가 (정규화)
        path_key = self._normalize_path_key(entry.path)
        self._path_to_id[path_key] = file_id
        
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
        if self._log_sink:
            from application.utils.debug_logger import debug_step
            debug_step(
                self._log_sink,
                "file_data_store_add_files_start",
                {
                    "entries_count": len(entries),
                    "existing_files_count": len(self._files),
                }
            )
        
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
            
            # 경로 인덱스 추가 (정규화)
            path_key = self._normalize_path_key(entry.path)
            self._path_to_id[path_key] = file_id
            
            file_data_list.append(file_data)
        
        # 배치 시그널만 emit (개별 시그널은 emit하지 않음)
        self.files_added_batch.emit(file_data_list)
        self.data_changed.emit()
        
        if self._log_sink:
            from application.utils.debug_logger import debug_step
            debug_step(
                self._log_sink,
                "file_data_store_add_files_complete",
                {
                    "added_count": len(file_data_list),
                    "total_files_count": len(self._files),
                }
            )
        
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
        # data_changed 제거 - 단일 파일 업데이트는 file_updated만으로 충분
        # 전체 리프레시가 필요한 경우(clear, batch add 등)는 명시적으로 emit
        
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
    
    def set_duplicate_groups_batch(
        self,
        updates: list[tuple[int, Optional[int], bool, Optional[float]]]
    ) -> None:
        """중복 그룹 정보 배치 설정.
        
        대량의 중복 그룹 정보를 한 번에 설정하여 시그널을 배치로 emit.
        UI 프리징을 방지하기 위해 사용.
        
        Args:
            updates: (file_id, group_id, is_canonical, similarity_score) 튜플 리스트.
        """
        if self._log_sink:
            from application.utils.debug_logger import debug_step
            debug_step(
                self._log_sink,
                "file_data_store_set_duplicate_groups_batch_start",
                {"updates_count": len(updates)}
            )
        
        changed_ids: list[int] = []
        for file_id, group_id, is_canonical, similarity_score in updates:
            file_data = self._files.get(file_id)
            if not file_data:
                continue
            
            # 필드 업데이트
            file_data.duplicate_group_id = group_id
            file_data.is_canonical = is_canonical
            file_data.similarity_score = similarity_score
            
            changed_ids.append(file_id)
        
        # 배치 시그널 1번만 emit (기존: 각 파일마다 file_updated emit)
        if changed_ids:
            if self._log_sink:
                from application.utils.debug_logger import debug_step
                debug_step(
                    self._log_sink,
                    "file_data_store_files_updated_batch_emit",
                    {"changed_ids_count": len(changed_ids), "sample_ids": changed_ids[:10]}
                )
            print(f"[DEBUG] FileDataStore.set_duplicate_groups_batch: emitting files_updated_batch signal with {len(changed_ids)} file_ids")
            self.files_updated_batch.emit(changed_ids)
            print(f"[DEBUG] FileDataStore.set_duplicate_groups_batch: files_updated_batch signal emitted")
            if self._log_sink:
                from application.utils.debug_logger import debug_step
                debug_step(
                    self._log_sink,
                    "file_data_store_set_duplicate_groups_batch_complete",
                    {"changed_ids_count": len(changed_ids)}
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
        # data_changed 제거 - 단일 파일 업데이트는 file_updated만으로 충분
    
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
    
    def _normalize_path_key(self, path: str | Path) -> str:
        """경로를 정규화하여 인덱스 키로 변환.
        
        Args:
            path: 파일 경로 (str 또는 Path).
        
        Returns:
            정규화된 경로 키 (대소문자 무시, 절대경로, posix 형식).
        """
        if isinstance(path, str):
            path = Path(path)
        
        # 1. 사용자 홈 디렉토리 확장 (~ -> 절대경로)
        path = path.expanduser()
        
        # 2. 절대경로로 변환 (resolve는 비용이 크므로 absolute만 사용)
        #    상대경로는 현재 작업 디렉토리 기준으로 변환
        if not path.is_absolute():
            path = path.absolute()
        
        # 3. 정규화 (.. 제거, . 제거 등)
        #    os.path.normpath는 Path.resolve()보다 가볍고 상대경로도 처리
        import os
        normalized = os.path.normpath(str(path))
        path = Path(normalized)
        
        # 4. posix 형식으로 변환 (Windows에서도 / 사용)
        path_key = path.as_posix()
        
        # 5. Windows에서 대소문자 무시 (Linux/Mac에서는 유지)
        import sys
        if sys.platform == "win32":
            path_key = path_key.lower()
        
        return path_key
    
    def get_file_id_by_path(self, path: str | Path) -> Optional[int]:
        """경로로 file_id 조회.
        
        Args:
            path: 파일 경로 (str 또는 Path).
        
        Returns:
            file_id. 없으면 None.
        """
        path_key = self._normalize_path_key(path)
        return self._path_to_id.get(path_key)
    
    def get_file_by_path(self, path: str | Path) -> Optional[FileData]:
        """경로로 FileData 조회.
        
        Args:
            path: 파일 경로 (str 또는 Path).
        
        Returns:
            FileData 객체. 없으면 None.
        """
        file_id = self.get_file_id_by_path(path)
        if file_id is None:
            return None
        return self.get_file(file_id)
