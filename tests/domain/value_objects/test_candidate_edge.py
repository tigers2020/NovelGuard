"""CandidateEdge ValueObject 테스트."""

import pytest

from domain.value_objects.candidate_edge import CandidateEdge


class TestCandidateEdgeCreation:
    """CandidateEdge 생성 테스트."""
    
    def test_create_minimal(self):
        """최소 정보로 생성."""
        edge = CandidateEdge(
            a_id=10,
            b_id=11,
            relation="EXACT"
        )
        
        assert edge.a_id == 10
        assert edge.b_id == 11
        assert edge.relation == "EXACT"
        assert edge.score == 0.0
        assert edge.evidence_id == 0
    
    def test_create_with_score(self):
        """점수와 함께 생성."""
        edge = CandidateEdge(
            a_id=10,
            b_id=11,
            relation="NEAR",
            score=0.95,
            evidence_id=1
        )
        
        assert edge.score == 0.95
        assert edge.evidence_id == 1


class TestCandidateEdgeValidation:
    """CandidateEdge 검증 테스트."""
    
    def test_invalid_score_too_low(self):
        """score가 0.0 미만이면 실패."""
        with pytest.raises(ValueError, match="score must be between"):
            CandidateEdge(
                a_id=10,
                b_id=11,
                relation="EXACT",
                score=-0.1
            )
    
    def test_invalid_score_too_high(self):
        """score가 1.0 초과이면 실패."""
        with pytest.raises(ValueError, match="score must be between"):
            CandidateEdge(
                a_id=10,
                b_id=11,
                relation="EXACT",
                score=1.1
            )
    
    def test_invalid_relation(self):
        """잘못된 relation이면 실패."""
        with pytest.raises(ValueError, match="relation must be one of"):
            CandidateEdge(
                a_id=10,
                b_id=11,
                relation="INVALID"
            )
    
    def test_same_file_ids(self):
        """a_id와 b_id가 같으면 실패."""
        with pytest.raises(ValueError, match="a_id and b_id must be different"):
            CandidateEdge(
                a_id=10,
                b_id=10,
                relation="EXACT"
            )


class TestCandidateEdgeImmutability:
    """CandidateEdge 불변성 테스트."""
    
    def test_frozen(self):
        """frozen=True로 속성 변경 불가."""
        edge = CandidateEdge(
            a_id=10,
            b_id=11,
            relation="EXACT"
        )
        
        with pytest.raises(Exception):  # FrozenInstanceError
            edge.score = 0.95  # type: ignore


class TestCandidateEdgeMethods:
    """CandidateEdge 메서드 테스트."""
    
    def test_get_other_id_from_a(self):
        """a_id를 주면 b_id 반환."""
        edge = CandidateEdge(
            a_id=10,
            b_id=11,
            relation="EXACT"
        )
        
        assert edge.get_other_id(10) == 11
    
    def test_get_other_id_from_b(self):
        """b_id를 주면 a_id 반환."""
        edge = CandidateEdge(
            a_id=10,
            b_id=11,
            relation="EXACT"
        )
        
        assert edge.get_other_id(11) == 10
    
    def test_get_other_id_invalid(self):
        """관련 없는 ID를 주면 실패."""
        edge = CandidateEdge(
            a_id=10,
            b_id=11,
            relation="EXACT"
        )
        
        with pytest.raises(ValueError, match="is not part of this edge"):
            edge.get_other_id(99)
    
    def test_contains_file_true(self):
        """파일 ID 포함 확인 (있음)."""
        edge = CandidateEdge(
            a_id=10,
            b_id=11,
            relation="EXACT"
        )
        
        assert edge.contains_file(10) is True
        assert edge.contains_file(11) is True
    
    def test_contains_file_false(self):
        """파일 ID 포함 확인 (없음)."""
        edge = CandidateEdge(
            a_id=10,
            b_id=11,
            relation="EXACT"
        )
        
        assert edge.contains_file(99) is False


class TestCandidateEdgeProperties:
    """CandidateEdge 속성 테스트."""
    
    def test_is_exact(self):
        """완전 일치 관계 확인."""
        edge = CandidateEdge(
            a_id=10,
            b_id=11,
            relation="EXACT"
        )
        
        assert edge.is_exact is True
        assert edge.is_near is False
        assert edge.is_containment is False
    
    def test_is_near(self):
        """유사 관계 확인."""
        edge = CandidateEdge(
            a_id=10,
            b_id=11,
            relation="NEAR"
        )
        
        assert edge.is_exact is False
        assert edge.is_near is True
        assert edge.is_containment is False
    
    def test_is_containment_a_in_b(self):
        """포함 관계 확인 (A in B)."""
        edge = CandidateEdge(
            a_id=10,
            b_id=11,
            relation="CONTAINS_A_IN_B"
        )
        
        assert edge.is_exact is False
        assert edge.is_near is False
        assert edge.is_containment is True
    
    def test_is_containment_b_in_a(self):
        """포함 관계 확인 (B in A)."""
        edge = CandidateEdge(
            a_id=10,
            b_id=11,
            relation="CONTAINS_B_IN_A"
        )
        
        assert edge.is_containment is True


class TestCandidateEdgeContainment:
    """CandidateEdge 포함 관계 테스트."""
    
    def test_get_container_id_a_in_b(self):
        """A가 B에 포함 → B가 컨테이너."""
        edge = CandidateEdge(
            a_id=10,
            b_id=11,
            relation="CONTAINS_A_IN_B"
        )
        
        assert edge.get_container_id() == 11
        assert edge.get_contained_id() == 10
    
    def test_get_container_id_b_in_a(self):
        """B가 A에 포함 → A가 컨테이너."""
        edge = CandidateEdge(
            a_id=10,
            b_id=11,
            relation="CONTAINS_B_IN_A"
        )
        
        assert edge.get_container_id() == 10
        assert edge.get_contained_id() == 11
    
    def test_get_container_id_no_containment(self):
        """포함 관계 아니면 None."""
        edge = CandidateEdge(
            a_id=10,
            b_id=11,
            relation="EXACT"
        )
        
        assert edge.get_container_id() is None
        assert edge.get_contained_id() is None
