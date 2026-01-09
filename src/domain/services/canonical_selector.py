"""Canonical 파일 선정 정책."""

from typing import Optional
from domain.models.file_record import FileRecord


class CanonicalSelector:
    """Canonical 파일 선정 정책.
    
    여러 파일 중 어떤 파일을 보존본(canonical)으로 선택할지 결정.
    """
    
    @staticmethod
    def select_canonical(
        records: list[FileRecord],
        policy: str = "newest"
    ) -> Optional[FileRecord]:
        """Canonical 파일 선택.
        
        Args:
            records: 후보 파일 레코드 리스트
            policy: 선정 정책 ("newest" | "largest" | "first")
        
        Returns:
            선택된 FileRecord 또는 None (빈 리스트인 경우)
        """
        if not records:
            return None
        
        if policy == "newest":
            # 수정 시간이 가장 최신인 것
            return max(records, key=lambda r: r.mtime)
        elif policy == "largest":
            # 크기가 가장 큰 것
            return max(records, key=lambda r: r.size)
        elif policy == "first":
            # 첫 번째 것
            return records[0]
        else:
            # 기본값: newest
            return max(records, key=lambda r: r.mtime)

