"""FileComparisonService 테스트."""

from pathlib import Path
from domain.entities.file import File
from domain.value_objects import FileId, FilePath, FileMetadata, FileHashInfo
from domain.services.file_compare import (
    FileComparisonService,
    ComparisonResult,
    ComparisonDetail
)


def test_are_identical_with_strong_hash():
    """강한 해시로 동일성 확인 테스트."""
    service = FileComparisonService()
    
    # 동일한 강한 해시
    file1 = _create_file_with_hash(hash_strong="abc123")
    file2 = _create_file_with_hash(hash_strong="abc123")
    assert service.are_identical(file1, file2)
    
    # 다른 강한 해시
    file3 = _create_file_with_hash(hash_strong="xyz789")
    assert not service.are_identical(file1, file3)


def test_are_identical_with_fingerprint():
    """빠른 지문으로 동일성 확인 테스트."""
    service = FileComparisonService()
    
    # 동일한 지문
    file1 = _create_file_with_hash(fingerprint_fast="fast123")
    file2 = _create_file_with_hash(fingerprint_fast="fast123")
    assert service.are_identical(file1, file2)
    
    # 다른 지문
    file3 = _create_file_with_hash(fingerprint_fast="fast456")
    assert not service.are_identical(file1, file3)


def test_are_identical_no_hash():
    """해시 없을 때 동일성 확인 테스트."""
    service = FileComparisonService()
    
    # 해시 없음
    file1 = _create_file_with_hash()
    file2 = _create_file_with_hash()
    assert not service.are_identical(file1, file2)


def test_calculate_similarity_with_simhash():
    """SimHash로 유사도 계산 테스트."""
    service = FileComparisonService()
    
    # 동일한 SimHash (유사도 1.0)
    file1 = _create_file_with_hash(simhash64=0b1010101010101010101010101010101010101010101010101010101010101010)
    file2 = _create_file_with_hash(simhash64=0b1010101010101010101010101010101010101010101010101010101010101010)
    similarity = service.calculate_similarity(file1, file2)
    assert similarity == 1.0
    
    # 1비트만 다름 (유사도 63/64)
    file3 = _create_file_with_hash(simhash64=0b1010101010101010101010101010101010101010101010101010101010101011)
    similarity = service.calculate_similarity(file1, file3)
    assert abs(similarity - (63.0 / 64.0)) < 0.01
    
    # 완전히 다름 (모든 비트 반전)
    file4 = _create_file_with_hash(simhash64=0b0101010101010101010101010101010101010101010101010101010101010101)
    similarity = service.calculate_similarity(file1, file4)
    assert similarity == 0.0


def test_calculate_similarity_with_fingerprint_norm():
    """정규화 지문으로 유사도 계산 테스트."""
    service = FileComparisonService()
    
    # 동일한 정규화 지문 (유사도 1.0)
    file1 = _create_file_with_hash(fingerprint_norm="norm123")
    file2 = _create_file_with_hash(fingerprint_norm="norm123")
    similarity = service.calculate_similarity(file1, file2)
    assert similarity == 1.0
    
    # 다른 정규화 지문 (유사도 0.0)
    file3 = _create_file_with_hash(fingerprint_norm="norm456")
    similarity = service.calculate_similarity(file1, file3)
    assert similarity == 0.0


def test_calculate_similarity_no_hash():
    """해시 없을 때 유사도 계산 테스트."""
    service = FileComparisonService()
    
    file1 = _create_file_with_hash()
    file2 = _create_file_with_hash()
    similarity = service.calculate_similarity(file1, file2)
    assert similarity == 0.0


def test_are_similar():
    """유사성 확인 테스트."""
    service = FileComparisonService()
    
    # 유사도가 임계값 이상 (기본값 0.8)
    file1 = _create_file_with_hash(simhash64=0b1010101010101010101010101010101010101010101010101010101010101010)
    file2 = _create_file_with_hash(simhash64=0b1010101010101010101010101010101010101010101010101010101010101010)
    assert service.are_similar(file1, file2)
    
    # 유사도가 임계값 미만
    file3 = _create_file_with_hash(simhash64=0b0000000000000000000000000000000000000000000000000000000000000000)
    assert not service.are_similar(file1, file3)
    
    # 사용자 정의 임계값
    file4 = _create_file_with_hash(simhash64=0b1010101010101010101010101010101010101010101010101010101010101011)  # 1비트 차이
    assert service.are_similar(file1, file4, threshold=0.9)


def test_compare_identical_strong_hash():
    """compare: 강한 해시로 동일성 테스트."""
    service = FileComparisonService()
    
    file1 = _create_file_with_hash(hash_strong="abc123")
    file2 = _create_file_with_hash(hash_strong="abc123")
    
    result = service.compare(file1, file2)
    assert result.result == ComparisonResult.IDENTICAL
    assert result.similarity_score == 1.0
    assert result.matched_by == "strong_hash"


def test_compare_identical_fingerprint():
    """compare: 빠른 지문으로 동일성 테스트."""
    service = FileComparisonService()
    
    file1 = _create_file_with_hash(fingerprint_fast="fast123")
    file2 = _create_file_with_hash(fingerprint_fast="fast123")
    
    result = service.compare(file1, file2)
    assert result.result == ComparisonResult.IDENTICAL
    assert result.similarity_score == 1.0
    assert result.matched_by == "fingerprint"


def test_compare_similar_simhash():
    """compare: SimHash로 유사성 테스트."""
    service = FileComparisonService()
    
    # 유사도 높음 (1비트 차이)
    file1 = _create_file_with_hash(simhash64=0b1010101010101010101010101010101010101010101010101010101010101010)
    file2 = _create_file_with_hash(simhash64=0b1010101010101010101010101010101010101010101010101010101010101011)
    
    result = service.compare(file1, file2)
    assert result.result == ComparisonResult.SIMILAR
    assert result.similarity_score > 0.9
    assert result.matched_by == "simhash"


def test_compare_different():
    """compare: 다른 파일 테스트."""
    service = FileComparisonService()
    
    # 유사도 낮음
    file1 = _create_file_with_hash(simhash64=0b1010101010101010101010101010101010101010101010101010101010101010)
    file2 = _create_file_with_hash(simhash64=0b0000000000000000000000000000000000000000000000000000000000000000)
    
    result = service.compare(file1, file2)
    assert result.result == ComparisonResult.DIFFERENT
    assert result.similarity_score < 0.8


def test_compare_unknown():
    """compare: 비교 불가 테스트."""
    service = FileComparisonService()
    
    # 해시 없음
    file1 = _create_file_with_hash()
    file2 = _create_file_with_hash()
    
    result = service.compare(file1, file2)
    assert result.result == ComparisonResult.UNKNOWN
    assert result.similarity_score == 0.0
    assert result.matched_by is None


def test_compare_hashes():
    """compare_hashes: 해시 정보만으로 비교 테스트."""
    service = FileComparisonService()
    
    # 동일한 강한 해시
    hash1 = FileHashInfo(hash_strong="abc123")
    hash2 = FileHashInfo(hash_strong="abc123")
    result = service.compare_hashes(hash1, hash2)
    assert result.result == ComparisonResult.IDENTICAL
    assert result.matched_by == "strong_hash"
    
    # 동일한 지문
    hash3 = FileHashInfo(fingerprint_fast="fast123")
    hash4 = FileHashInfo(fingerprint_fast="fast123")
    result = service.compare_hashes(hash3, hash4)
    assert result.result == ComparisonResult.IDENTICAL
    assert result.matched_by == "fingerprint"
    
    # SimHash 유사
    hash5 = FileHashInfo(simhash64=0b1010101010101010101010101010101010101010101010101010101010101010)
    hash6 = FileHashInfo(simhash64=0b1010101010101010101010101010101010101010101010101010101010101011)
    result = service.compare_hashes(hash5, hash6)
    assert result.result == ComparisonResult.SIMILAR
    assert result.matched_by == "simhash"


def _create_file_with_hash(
    hash_strong: str = None,
    fingerprint_fast: str = None,
    fingerprint_norm: str = None,
    simhash64: int = None
) -> File:
    """해시 정보를 가진 샘플 File 엔티티 생성.
    
    Args:
        hash_strong: 강한 해시
        fingerprint_fast: 빠른 지문
        fingerprint_norm: 정규화 지문
        simhash64: SimHash 값
    
    Returns:
        File 엔티티
    """
    file_id = FileId(1)
    path = FilePath(
        path=Path("C:/test/file.txt"),
        name="file.txt",
        ext=".txt",
        size=1024,
        mtime=1609459200.0
    )
    metadata = FileMetadata.text_file(encoding="utf-8")
    hash_info = FileHashInfo(
        hash_strong=hash_strong,
        fingerprint_fast=fingerprint_fast,
        fingerprint_norm=fingerprint_norm,
        simhash64=simhash64
    )
    
    return File(
        file_id=file_id,
        path=path,
        metadata=metadata,
        hash_info=hash_info
    )
