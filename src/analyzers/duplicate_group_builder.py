"""
중복 그룹 빌더 모듈

중복 검증 결과를 기반으로 DuplicateGroup 객체를 생성하는 기능을 제공합니다.
"""

from typing import Optional, Any

from models.file_record import FileRecord
from analyzers.duplicate_group import DuplicateGroup
from utils.logger import get_logger
from utils.constants import CONFIDENCE_STRONG, CONFIDENCE_WEAK


class DuplicateGroupBuilder:
    """중복 그룹 빌더 클래스.
    
    중복 검증 결과를 기반으로 DuplicateGroup 객체를 생성합니다.
    중복 강도 결정, 근거 생성 등의 로직을 캡슐화합니다.
    
    Attributes:
        _logger: 로거 인스턴스
    """
    
    def __init__(self) -> None:
        """DuplicateGroupBuilder 초기화."""
        self._logger = get_logger("DuplicateGroupBuilder")
    
    def build(
        self,
        keep_file: FileRecord,
        verified_duplicates: list[FileRecord],
        verification_evidence: list[dict[str, Any]]
    ) -> Optional[DuplicateGroup]:
        """중복 그룹을 생성합니다.
        
        Args:
            keep_file: 유지할 최신본 FileRecord
            verified_duplicates: 검증된 중복 파일 리스트
            verification_evidence: 검증 근거 리스트
        
        Returns:
            DuplicateGroup 객체. 중복이 없으면 None.
        """
        # 중복이 없으면 None 반환
        if not verified_duplicates:
            return None
        
        # 중복 강도 결정
        duplicate_strength = self._determine_strength(verification_evidence)
        
        # 판정 근거
        reason = "LATEST_INCLUDES_OLDER"
        evidence = {
            "keep_file": str(keep_file.path),
            "duplicate_count": len(verified_duplicates),
            "base_title": keep_file.base_title,
            "episode_end": keep_file.episode_end,
            "selection_rule": "episode_end_max" if keep_file.episode_end else "size_max",
            "verification_details": verification_evidence
        }
        
        # confidence 계산
        confidence = CONFIDENCE_STRONG if duplicate_strength == "STRONG" else CONFIDENCE_WEAK
        
        # 그룹 생성 (keep_file + verified_duplicates)
        group = DuplicateGroup(
            members=[keep_file] + verified_duplicates,
            reason=reason,
            evidence=evidence,
            confidence=confidence,
            keep_file=keep_file,
            duplicate_strength=duplicate_strength
        )
        
        self._logger.debug(
            f"중복 그룹 생성: keep={keep_file.name}, "
            f"duplicates={len(verified_duplicates)}개, strength={duplicate_strength}"
        )
        
        return group
    
    def _determine_strength(self, verification_evidence: list[dict[str, Any]]) -> str:
        """중복 강도를 결정합니다.
        
        Args:
            verification_evidence: 검증 근거 리스트
        
        Returns:
            "STRONG" 또는 "WEAK"
        """
        # anchor_hashes 기반 검증이 하나라도 있으면 STRONG
        if any(ev.get("method") == "anchor_hashes" for ev in verification_evidence):
            return "STRONG"
        return "WEAK"

