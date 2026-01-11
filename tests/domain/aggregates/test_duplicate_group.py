"""DuplicateGroup Aggregate 테스트."""

import pytest

from domain.aggregates.duplicate_group import DuplicateGroup


class TestDuplicateGroupCreation:
    """DuplicateGroup 생성 테스트."""
    
    def test_create_minimal(self):
        """최소 정보로 생성."""
        group = DuplicateGroup(
            group_id=1,
            group_type="EXACT"
        )
        
        assert group.group_id == 1
        assert group.group_type == "EXACT"
        assert group.member_ids == ()
        assert group.canonical_id is None
        assert group.confidence == 0.0
        assert group.bytes_savable == 0
        assert group.status == "CANDIDATE"
        assert group.reason_ids == ()
    
    def test_create_with_members(self):
        """멤버와 함께 생성."""
        group = DuplicateGroup(
            group_id=1,
            group_type="EXACT",
            member_ids=(10, 11, 12),
            canonical_id=10,
            confidence=1.0,
            bytes_savable=1024000
        )
        
        assert group.member_ids == (10, 11, 12)
        assert group.canonical_id == 10
        assert group.confidence == 1.0
        assert group.bytes_savable == 1024000
    
    def test_create_with_reasons(self):
        """증거와 함께 생성."""
        group = DuplicateGroup(
            group_id=1,
            group_type="EXACT",
            reason_ids=(1, 2, 3)
        )
        
        assert group.reason_ids == (1, 2, 3)


class TestDuplicateGroupValidation:
    """DuplicateGroup 검증 테스트."""
    
    def test_invalid_confidence_too_low(self):
        """confidence가 0.0 미만이면 실패."""
        with pytest.raises(ValueError, match="confidence must be between"):
            DuplicateGroup(
                group_id=1,
                group_type="EXACT",
                confidence=-0.1
            )
    
    def test_invalid_confidence_too_high(self):
        """confidence가 1.0 초과이면 실패."""
        with pytest.raises(ValueError, match="confidence must be between"):
            DuplicateGroup(
                group_id=1,
                group_type="EXACT",
                confidence=1.1
            )
    
    def test_invalid_group_type(self):
        """잘못된 group_type이면 실패."""
        with pytest.raises(ValueError, match="group_type must be one of"):
            DuplicateGroup(
                group_id=1,
                group_type="INVALID"
            )
    
    def test_invalid_status(self):
        """잘못된 status이면 실패."""
        with pytest.raises(ValueError, match="status must be one of"):
            DuplicateGroup(
                group_id=1,
                group_type="EXACT",
                status="INVALID"
            )
    
    def test_canonical_not_in_members(self):
        """canonical_id가 member_ids에 없으면 실패."""
        with pytest.raises(ValueError, match="canonical_id .* must be in member_ids"):
            DuplicateGroup(
                group_id=1,
                group_type="EXACT",
                member_ids=(10, 11, 12),
                canonical_id=99  # member_ids에 없음
            )


class TestDuplicateGroupImmutability:
    """DuplicateGroup 불변성 테스트."""
    
    def test_frozen(self):
        """frozen=True로 속성 변경 불가."""
        group = DuplicateGroup(
            group_id=1,
            group_type="EXACT",
            member_ids=(10, 11)
        )
        
        with pytest.raises(Exception):  # FrozenInstanceError
            group.status = "VERIFIED"  # type: ignore
    
    def test_member_ids_immutable(self):
        """member_ids는 불변 튜플."""
        group = DuplicateGroup(
            group_id=1,
            group_type="EXACT",
            member_ids=(10, 11)
        )
        
        assert isinstance(group.member_ids, tuple)
        # 튜플은 변경 불가
        with pytest.raises(AttributeError):
            group.member_ids.append(12)  # type: ignore


class TestDuplicateGroupFunctionalUpdate:
    """DuplicateGroup 함수형 업데이트 테스트."""
    
    def test_with_status(self):
        """상태 변경."""
        group = DuplicateGroup(
            group_id=1,
            group_type="EXACT"
        )
        
        verified = group.with_status("VERIFIED")
        
        # 원본 불변
        assert group.status == "CANDIDATE"
        # 새 인스턴스 생성
        assert verified.status == "VERIFIED"
        assert verified.group_id == group.group_id
    
    def test_with_canonical(self):
        """보존본 설정."""
        group = DuplicateGroup(
            group_id=1,
            group_type="EXACT",
            member_ids=(10, 11, 12)
        )
        
        with_canonical = group.with_canonical(10)
        
        # 원본 불변
        assert group.canonical_id is None
        # 새 인스턴스 생성
        assert with_canonical.canonical_id == 10
    
    def test_with_canonical_not_in_members(self):
        """member_ids에 없는 canonical_id 설정 시 실패."""
        group = DuplicateGroup(
            group_id=1,
            group_type="EXACT",
            member_ids=(10, 11, 12)
        )
        
        with pytest.raises(ValueError, match="canonical_id .* must be in member_ids"):
            group.with_canonical(99)
    
    def test_with_added_member(self):
        """멤버 추가."""
        group = DuplicateGroup(
            group_id=1,
            group_type="EXACT",
            member_ids=(10, 11)
        )
        
        expanded = group.with_added_member(12)
        
        # 원본 불변
        assert group.member_ids == (10, 11)
        # 새 인스턴스 생성
        assert expanded.member_ids == (10, 11, 12)
    
    def test_with_added_member_duplicate(self):
        """이미 존재하는 멤버 추가 시 변경 없음."""
        group = DuplicateGroup(
            group_id=1,
            group_type="EXACT",
            member_ids=(10, 11)
        )
        
        same = group.with_added_member(10)
        
        # 동일한 인스턴스 반환
        assert same is group
    
    def test_with_added_reason(self):
        """증거 추가."""
        group = DuplicateGroup(
            group_id=1,
            group_type="EXACT",
            reason_ids=(1, 2)
        )
        
        with_reason = group.with_added_reason(3)
        
        # 원본 불변
        assert group.reason_ids == (1, 2)
        # 새 인스턴스 생성
        assert with_reason.reason_ids == (1, 2, 3)
    
    def test_with_added_reason_duplicate(self):
        """이미 존재하는 증거 추가 시 변경 없음."""
        group = DuplicateGroup(
            group_id=1,
            group_type="EXACT",
            reason_ids=(1, 2)
        )
        
        same = group.with_added_reason(1)
        
        # 동일한 인스턴스 반환
        assert same is group
    
    def test_with_confidence(self):
        """신뢰도 변경."""
        group = DuplicateGroup(
            group_id=1,
            group_type="EXACT"
        )
        
        high_conf = group.with_confidence(0.95)
        
        # 원본 불변
        assert group.confidence == 0.0
        # 새 인스턴스 생성
        assert high_conf.confidence == 0.95
    
    def test_with_bytes_savable(self):
        """절감 용량 변경."""
        group = DuplicateGroup(
            group_id=1,
            group_type="EXACT"
        )
        
        with_savings = group.with_bytes_savable(1024000)
        
        # 원본 불변
        assert group.bytes_savable == 0
        # 새 인스턴스 생성
        assert with_savings.bytes_savable == 1024000


class TestDuplicateGroupProperties:
    """DuplicateGroup 속성 테스트."""
    
    def test_member_count(self):
        """멤버 수 확인."""
        group = DuplicateGroup(
            group_id=1,
            group_type="EXACT",
            member_ids=(10, 11, 12)
        )
        
        assert group.member_count == 3
    
    def test_has_canonical_true(self):
        """보존본 설정 여부 확인 (있음)."""
        group = DuplicateGroup(
            group_id=1,
            group_type="EXACT",
            member_ids=(10, 11),
            canonical_id=10
        )
        
        assert group.has_canonical is True
    
    def test_has_canonical_false(self):
        """보존본 설정 여부 확인 (없음)."""
        group = DuplicateGroup(
            group_id=1,
            group_type="EXACT",
            member_ids=(10, 11)
        )
        
        assert group.has_canonical is False
    
    def test_is_verified(self):
        """검증 완료 상태 확인."""
        group = DuplicateGroup(
            group_id=1,
            group_type="EXACT",
            status="VERIFIED"
        )
        
        assert group.is_verified is True
    
    def test_is_applied(self):
        """적용 완료 상태 확인."""
        group = DuplicateGroup(
            group_id=1,
            group_type="EXACT",
            status="APPLIED"
        )
        
        assert group.is_applied is True
    
    def test_get_delete_candidate_ids(self):
        """삭제 후보 ID 목록."""
        group = DuplicateGroup(
            group_id=1,
            group_type="EXACT",
            member_ids=(10, 11, 12),
            canonical_id=10
        )
        
        delete_ids = group.get_delete_candidate_ids()
        
        assert delete_ids == (11, 12)
        assert 10 not in delete_ids  # 보존본 제외
    
    def test_get_delete_candidate_ids_no_canonical(self):
        """보존본 없으면 빈 튜플."""
        group = DuplicateGroup(
            group_id=1,
            group_type="EXACT",
            member_ids=(10, 11, 12)
        )
        
        delete_ids = group.get_delete_candidate_ids()
        
        assert delete_ids == ()


class TestDuplicateGroupChaining:
    """DuplicateGroup 메서드 체이닝 테스트."""
    
    def test_chaining_multiple_updates(self):
        """여러 업데이트 체이닝."""
        group = DuplicateGroup(
            group_id=1,
            group_type="EXACT",
            member_ids=(10, 11)
        )
        
        result = (
            group
            .with_added_member(12)
            .with_canonical(10)
            .with_confidence(0.95)
            .with_status("VERIFIED")
            .with_bytes_savable(1024000)
        )
        
        # 원본 불변
        assert group.member_ids == (10, 11)
        assert group.canonical_id is None
        assert group.status == "CANDIDATE"
        
        # 최종 결과
        assert result.member_ids == (10, 11, 12)
        assert result.canonical_id == 10
        assert result.confidence == 0.95
        assert result.status == "VERIFIED"
        assert result.bytes_savable == 1024000
