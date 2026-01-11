"""FileHashInfo Value Object 테스트."""

import pytest
from domain.value_objects.file_hash import FileHashInfo


def test_file_hash_info_creation():
    """FileHashInfo 생성 테스트."""
    hash_info = FileHashInfo(
        hash_strong="abc123",
        fingerprint_fast="def456",
        fingerprint_norm="ghi789",
        simhash64=12345
    )
    
    assert hash_info.hash_strong == "abc123"
    assert hash_info.fingerprint_fast == "def456"
    assert hash_info.fingerprint_norm == "ghi789"
    assert hash_info.simhash64 == 12345


def test_file_hash_info_immutable():
    """FileHashInfo 불변성 테스트."""
    hash_info = FileHashInfo(hash_strong="abc123")
    
    with pytest.raises(Exception):  # FrozenInstanceError
        hash_info.hash_strong = "xyz789"  # type: ignore


def test_file_hash_info_defaults():
    """FileHashInfo 기본값 테스트."""
    hash_info = FileHashInfo()
    
    assert hash_info.hash_strong is None
    assert hash_info.fingerprint_fast is None
    assert hash_info.fingerprint_norm is None
    assert hash_info.simhash64 is None


def test_has_any_hash():
    """has_any_hash 메서드 테스트."""
    # 빈 해시
    empty_hash = FileHashInfo()
    assert not empty_hash.has_any_hash()
    
    # hash_strong만 있음
    hash_with_strong = FileHashInfo(hash_strong="abc123")
    assert hash_with_strong.has_any_hash()
    
    # fingerprint_fast만 있음
    hash_with_fast = FileHashInfo(fingerprint_fast="def456")
    assert hash_with_fast.has_any_hash()
    
    # simhash64만 있음
    hash_with_simhash = FileHashInfo(simhash64=12345)
    assert hash_with_simhash.has_any_hash()


def test_has_strong_hash():
    """has_strong_hash 메서드 테스트."""
    # hash_strong 없음
    hash_without_strong = FileHashInfo(fingerprint_fast="def456")
    assert not hash_without_strong.has_strong_hash()
    
    # hash_strong 있음
    hash_with_strong = FileHashInfo(hash_strong="abc123")
    assert hash_with_strong.has_strong_hash()


def test_has_fingerprint():
    """has_fingerprint 메서드 테스트."""
    # fingerprint_fast 없음
    hash_without_fingerprint = FileHashInfo(hash_strong="abc123")
    assert not hash_without_fingerprint.has_fingerprint()
    
    # fingerprint_fast 있음
    hash_with_fingerprint = FileHashInfo(fingerprint_fast="def456")
    assert hash_with_fingerprint.has_fingerprint()
