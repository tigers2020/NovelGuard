"""Exact 중복 탐지 서비스."""
from pathlib import Path
from typing import Optional, Protocol

from domain.entities.file_entry import FileEntry
from domain.value_objects.blocking_group import BlockingGroup
from domain.value_objects.duplicate_relation import ExactDuplicateRelation


class IHashService(Protocol):
    """해시 서비스 인터페이스 (Port).
    
    실제 구현은 Infrastructure 계층에서 제공.
    """
    
    def calculate_hash(self, file_path: Path) -> str:
        """전체 파일 해시 계산 (SHA256).
        
        Args:
            file_path: 파일 경로.
        
        Returns:
            해시 값 (hex 문자열).
        """
        ...
    
    def calculate_prefix_hash(self, file_path: Path, size: int = 65536) -> str:
        """파일 앞부분 해시 계산.
        
        Args:
            file_path: 파일 경로.
            size: 읽을 바이트 수 (기본값: 64KB).
        
        Returns:
            해시 값 (hex 문자열).
        """
        ...
    
    def calculate_suffix_hash(self, file_path: Path, size: int = 65536) -> str:
        """파일 뒷부분 해시 계산.
        
        Args:
            file_path: 파일 경로.
            size: 읽을 바이트 수 (기본값: 64KB).
        
        Returns:
            해시 값 (hex 문자열).
        """
        ...


class ExactDuplicateDetector:
    """Exact 중복 탐지 서비스.
    
    내용이 100% 동일한 파일을 탐지하는 서비스.
    해시 기반으로 동일성을 판정.
    """
    
    def __init__(
        self,
        hash_service: IHashService,
        log_sink: Optional["ILogSink"] = None
    ) -> None:
        """ExactDuplicateDetector 초기화.
        
        Args:
            hash_service: 해시 서비스 (Port).
            log_sink: 로그 싱크 (선택적, 디버깅 목적).
        """
        self._hash_service = hash_service
        self._log_sink = log_sink
    
    def detect_exact(
        self,
        blocking_group: BlockingGroup,
        file_entries: dict[int, FileEntry]
    ) -> list[ExactDuplicateRelation]:
        """Exact 중복 탐지.
        
        Args:
            blocking_group: Blocking Group.
            file_entries: 파일 ID -> FileEntry 매핑.
        
        Returns:
            ExactDuplicateRelation 리스트.
        """
        # 같은 크기의 파일들끼리만 비교
        size_groups: dict[int, list[int]] = {}
        for file_id in blocking_group.file_ids:
            if file_id in file_entries:
                file_entry = file_entries[file_id]
                if file_entry.size not in size_groups:
                    size_groups[file_entry.size] = []
                size_groups[file_entry.size].append(file_id)
        
        exact_relations = []
        
        # 각 크기 그룹 내에서 해시 비교
        for size, file_ids in size_groups.items():
            if len(file_ids) < 2:
                continue  # 중복 가능성이 없음
            
            # 단계적 필터링: prefix hash → suffix hash → full hash
            prefix_hash_groups = self._group_by_prefix_hash(file_ids, file_entries)
            
            for prefix_hash, prefix_file_ids in prefix_hash_groups.items():
                if len(prefix_file_ids) < 2:
                    continue
                
                suffix_hash_groups = self._group_by_suffix_hash(prefix_file_ids, file_entries)
                
                for suffix_hash, suffix_file_ids in suffix_hash_groups.items():
                    if len(suffix_file_ids) < 2:
                        continue
                    
                    # Full hash로 최종 확인
                    full_hash_groups = self._group_by_full_hash(suffix_file_ids, file_entries)
                    
                    for full_hash, hash_file_ids in full_hash_groups.items():
                        if len(hash_file_ids) >= 2:
                            evidence = {
                                "hash": full_hash,
                                "size": size,
                                "prefix_hash": prefix_hash,
                                "suffix_hash": suffix_hash
                            }
                            
                            relation = ExactDuplicateRelation(
                                file_ids=hash_file_ids,
                                evidence=evidence,
                                confidence=1.0  # Exact는 항상 1.0
                            )
                            exact_relations.append(relation)
        
        return exact_relations
    
    def _group_by_prefix_hash(
        self,
        file_ids: list[int],
        file_entries: dict[int, FileEntry]
    ) -> dict[str, list[int]]:
        """Prefix hash로 그룹화."""
        groups: dict[str, list[int]] = {}
        
        for file_id in file_ids:
            file_entry = file_entries[file_id]
            prefix_hash = self._hash_service.calculate_prefix_hash(file_entry.path)
            
            if prefix_hash not in groups:
                groups[prefix_hash] = []
            groups[prefix_hash].append(file_id)
        
        return groups
    
    def _group_by_suffix_hash(
        self,
        file_ids: list[int],
        file_entries: dict[int, FileEntry]
    ) -> dict[str, list[int]]:
        """Suffix hash로 그룹화."""
        groups: dict[str, list[int]] = {}
        
        for file_id in file_ids:
            file_entry = file_entries[file_id]
            suffix_hash = self._hash_service.calculate_suffix_hash(file_entry.path)
            
            if suffix_hash not in groups:
                groups[suffix_hash] = []
            groups[suffix_hash].append(file_id)
        
        return groups
    
    def _group_by_full_hash(
        self,
        file_ids: list[int],
        file_entries: dict[int, FileEntry]
    ) -> dict[str, list[int]]:
        """Full hash로 그룹화."""
        groups: dict[str, list[int]] = {}
        
        for file_id in file_ids:
            file_entry = file_entries[file_id]
            full_hash = self._hash_service.calculate_hash(file_entry.path)
            
            if full_hash not in groups:
                groups[full_hash] = []
            groups[full_hash].append(file_id)
        
        return groups

