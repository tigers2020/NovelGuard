"""Evidence ValueObject 테스트."""

import pytest
from datetime import datetime

from domain.value_objects.evidence import Evidence


class TestEvidenceCreation:
    """Evidence 생성 테스트."""
    
    def test_create_minimal(self):
        """최소 정보로 생성."""
        evidence = Evidence(
            evidence_id=1,
            kind="HASH_STRONG"
        )
        
        assert evidence.evidence_id == 1
        assert evidence.kind == "HASH_STRONG"
        assert evidence.detail == {}
        assert isinstance(evidence.created_at, datetime)
    
    def test_create_with_detail(self):
        """상세 정보와 함께 생성."""
        detail = {
            "algorithm": "md5",
            "value": "abc123def456"
        }
        evidence = Evidence(
            evidence_id=1,
            kind="HASH_STRONG",
            detail=detail
        )
        
        assert evidence.detail == detail
    
    def test_create_with_similarity(self):
        """유사도 정보와 함께 생성."""
        evidence = Evidence(
            evidence_id=1,
            kind="SIMHASH",
            detail={"similarity": 0.93}
        )
        
        assert evidence.detail["similarity"] == 0.93


class TestEvidenceValidation:
    """Evidence 검증 테스트."""
    
    def test_invalid_kind(self):
        """잘못된 kind이면 실패."""
        with pytest.raises(ValueError, match="kind must be one of"):
            Evidence(
                evidence_id=1,
                kind="INVALID"
            )
    
    def test_detail_with_complex_object(self):
        """detail에 복잡한 객체가 있으면 실패."""
        class MockFile:
            pass
        
        with pytest.raises(ValueError, match="contains non-primitive object"):
            Evidence(
                evidence_id=1,
                kind="HASH_STRONG",
                detail={"file": MockFile()}
            )


class TestEvidenceImmutability:
    """Evidence 불변성 테스트."""
    
    def test_frozen(self):
        """frozen=True로 속성 변경 불가."""
        evidence = Evidence(
            evidence_id=1,
            kind="HASH_STRONG"
        )
        
        with pytest.raises(Exception):  # FrozenInstanceError
            evidence.kind = "SIMHASH"  # type: ignore


class TestEvidenceProperties:
    """Evidence 속성 테스트."""
    
    def test_is_hash_based(self):
        """해시 기반 증거 확인."""
        evidence_strong = Evidence(evidence_id=1, kind="HASH_STRONG")
        evidence_fast = Evidence(evidence_id=2, kind="FP_FAST")
        evidence_norm = Evidence(evidence_id=3, kind="NORM_HASH")
        evidence_sim = Evidence(evidence_id=4, kind="SIMHASH")
        
        assert evidence_strong.is_hash_based is True
        assert evidence_fast.is_hash_based is True
        assert evidence_norm.is_hash_based is True
        assert evidence_sim.is_hash_based is False
    
    def test_is_similarity_based(self):
        """유사도 기반 증거 확인."""
        evidence = Evidence(evidence_id=1, kind="SIMHASH")
        
        assert evidence.is_similarity_based is True
        assert evidence.is_hash_based is False
    
    def test_is_containment_based(self):
        """포함 관계 기반 증거 확인."""
        evidence = Evidence(evidence_id=1, kind="CONTAINMENT_RK")
        
        assert evidence.is_containment_based is True
        assert evidence.is_hash_based is False
    
    def test_is_text_diff_based(self):
        """텍스트 차이 분석 기반 증거 확인."""
        evidence = Evidence(evidence_id=1, kind="TEXT_DIFF")
        
        assert evidence.is_text_diff_based is True
        assert evidence.is_hash_based is False


class TestEvidenceMethods:
    """Evidence 메서드 테스트."""
    
    def test_get_similarity_present(self):
        """유사도 값 반환 (있음)."""
        evidence = Evidence(
            evidence_id=1,
            kind="SIMHASH",
            detail={"similarity": 0.93}
        )
        
        assert evidence.get_similarity() == 0.93
    
    def test_get_similarity_absent(self):
        """유사도 값 반환 (없음)."""
        evidence = Evidence(
            evidence_id=1,
            kind="HASH_STRONG"
        )
        
        assert evidence.get_similarity() is None
    
    def test_get_match_spans_present(self):
        """매칭 구간 반환 (있음)."""
        spans = [(1200, 5600), (7000, 9000)]
        evidence = Evidence(
            evidence_id=1,
            kind="CONTAINMENT_RK",
            detail={"match_spans": spans}
        )
        
        assert evidence.get_match_spans() == spans
    
    def test_get_match_spans_absent(self):
        """매칭 구간 반환 (없음)."""
        evidence = Evidence(
            evidence_id=1,
            kind="HASH_STRONG"
        )
        
        assert evidence.get_match_spans() is None
    
    def test_has_detail_true(self):
        """상세 정보 존재 확인 (있음)."""
        evidence = Evidence(
            evidence_id=1,
            kind="HASH_STRONG",
            detail={"algorithm": "md5"}
        )
        
        assert evidence.has_detail("algorithm") is True
    
    def test_has_detail_false(self):
        """상세 정보 존재 확인 (없음)."""
        evidence = Evidence(
            evidence_id=1,
            kind="HASH_STRONG",
            detail={"algorithm": "md5"}
        )
        
        assert evidence.has_detail("value") is False


class TestEvidenceKinds:
    """Evidence 종류별 테스트."""
    
    def test_hash_strong(self):
        """HASH_STRONG 증거."""
        evidence = Evidence(
            evidence_id=1,
            kind="HASH_STRONG",
            detail={"algorithm": "md5", "value": "abc123"}
        )
        
        assert evidence.is_hash_based is True
    
    def test_fp_fast(self):
        """FP_FAST 증거."""
        evidence = Evidence(
            evidence_id=1,
            kind="FP_FAST",
            detail={"head": "abc", "mid": "def", "tail": "ghi"}
        )
        
        assert evidence.is_hash_based is True
    
    def test_norm_hash(self):
        """NORM_HASH 증거."""
        evidence = Evidence(
            evidence_id=1,
            kind="NORM_HASH",
            detail={"normalized_text": "..."}
        )
        
        assert evidence.is_hash_based is True
    
    def test_simhash(self):
        """SIMHASH 증거."""
        evidence = Evidence(
            evidence_id=1,
            kind="SIMHASH",
            detail={"similarity": 0.93, "hamming_distance": 3}
        )
        
        assert evidence.is_similarity_based is True
        assert evidence.get_similarity() == 0.93
    
    def test_containment_rk(self):
        """CONTAINMENT_RK 증거."""
        evidence = Evidence(
            evidence_id=1,
            kind="CONTAINMENT_RK",
            detail={
                "match_spans": [(1200, 5600)],
                "coverage": 0.85
            }
        )
        
        assert evidence.is_containment_based is True
        assert evidence.get_match_spans() == [(1200, 5600)]
    
    def test_text_diff(self):
        """TEXT_DIFF 증거."""
        evidence = Evidence(
            evidence_id=1,
            kind="TEXT_DIFF",
            detail={
                "added_lines": 5,
                "removed_lines": 3,
                "diff_ratio": 0.92
            }
        )
        
        assert evidence.is_text_diff_based is True
