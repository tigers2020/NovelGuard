"""FileMetadata Value Object 테스트."""

import pytest
from domain.value_objects.file_metadata import FileMetadata


def test_file_metadata_creation():
    """FileMetadata 생성 테스트."""
    metadata = FileMetadata(
        is_text=True,
        encoding_detected="utf-8",
        encoding_confidence=0.95,
        newline="LF"
    )
    
    assert metadata.is_text is True
    assert metadata.encoding_detected == "utf-8"
    assert metadata.encoding_confidence == 0.95
    assert metadata.newline == "LF"


def test_file_metadata_immutable():
    """FileMetadata 불변성 테스트."""
    metadata = FileMetadata(is_text=True)
    
    with pytest.raises(Exception):  # FrozenInstanceError
        metadata.is_text = False  # type: ignore


def test_file_metadata_defaults():
    """FileMetadata 기본값 테스트."""
    metadata = FileMetadata()
    
    assert metadata.is_text is False
    assert metadata.encoding_detected is None
    assert metadata.encoding_confidence is None
    assert metadata.newline is None


def test_file_metadata_validation_confidence_range():
    """FileMetadata 검증: 신뢰도 범위 테스트."""
    # 정상 범위
    FileMetadata(encoding_confidence=0.0)
    FileMetadata(encoding_confidence=0.5)
    FileMetadata(encoding_confidence=1.0)
    
    # 범위 초과
    with pytest.raises(ValueError, match="encoding_confidence must be between"):
        FileMetadata(encoding_confidence=-0.1)
    
    with pytest.raises(ValueError, match="encoding_confidence must be between"):
        FileMetadata(encoding_confidence=1.1)


def test_file_metadata_validation_newline():
    """FileMetadata 검증: 줄바꿈 타입 테스트."""
    # 유효한 값들
    FileMetadata(newline="LF")
    FileMetadata(newline="CRLF")
    FileMetadata(newline="MIXED")
    FileMetadata(newline=None)
    
    # 유효하지 않은 값
    with pytest.raises(ValueError, match="newline must be one of"):
        FileMetadata(newline="INVALID")


def test_has_encoding():
    """has_encoding 메서드 테스트."""
    # 인코딩 없음
    metadata_without_encoding = FileMetadata()
    assert not metadata_without_encoding.has_encoding()
    
    # 인코딩 있음
    metadata_with_encoding = FileMetadata(encoding_detected="utf-8")
    assert metadata_with_encoding.has_encoding()


def test_is_high_confidence():
    """is_high_confidence 메서드 테스트."""
    # 신뢰도 없음
    metadata_without_confidence = FileMetadata()
    assert not metadata_without_confidence.is_high_confidence()
    
    # 낮은 신뢰도
    metadata_low_confidence = FileMetadata(encoding_confidence=0.5)
    assert not metadata_low_confidence.is_high_confidence()
    
    # 높은 신뢰도 (기본 임계값 0.8)
    metadata_high_confidence = FileMetadata(encoding_confidence=0.9)
    assert metadata_high_confidence.is_high_confidence()
    
    # 사용자 정의 임계값
    metadata_medium_confidence = FileMetadata(encoding_confidence=0.7)
    assert metadata_medium_confidence.is_high_confidence(threshold=0.6)
    assert not metadata_medium_confidence.is_high_confidence(threshold=0.8)


def test_text_file_factory():
    """text_file 팩토리 메서드 테스트."""
    metadata = FileMetadata.text_file(
        encoding="utf-8",
        confidence=0.95,
        newline="LF"
    )
    
    assert metadata.is_text is True
    assert metadata.encoding_detected == "utf-8"
    assert metadata.encoding_confidence == 0.95
    assert metadata.newline == "LF"
    
    # 기본값
    metadata_default = FileMetadata.text_file(encoding="utf-8")
    assert metadata_default.is_text is True
    assert metadata_default.encoding_confidence == 1.0
    assert metadata_default.newline is None


def test_binary_file_factory():
    """binary_file 팩토리 메서드 테스트."""
    metadata = FileMetadata.binary_file()
    
    assert metadata.is_text is False
    assert metadata.encoding_detected is None
    assert metadata.encoding_confidence is None
    assert metadata.newline is None
