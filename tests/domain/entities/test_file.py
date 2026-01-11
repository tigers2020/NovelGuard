"""File Entity 테스트."""

from pathlib import Path
from domain.entities.file import File
from domain.value_objects import FileId, FilePath, FileMetadata, FileHashInfo


def test_file_creation():
    """File 엔티티 생성 테스트."""
    file_id = FileId(1)
    path = FilePath(
        path=Path("C:/test/file.txt"),
        name="file.txt",
        ext=".txt",
        size=1024,
        mtime=1609459200.0
    )
    metadata = FileMetadata.text_file(encoding="utf-8")
    hash_info = FileHashInfo(hash_strong="abc123")
    
    file_entity = File(
        file_id=file_id,
        path=path,
        metadata=metadata,
        hash_info=hash_info
    )
    
    assert file_entity.file_id == file_id
    assert file_entity.path == path
    assert file_entity.metadata == metadata
    assert file_entity.hash_info == hash_info
    assert len(file_entity.flags) == 0
    assert len(file_entity.errors) == 0


def test_file_equality():
    """File 엔티티 동등성 테스트 (ID 기반)."""
    file_id = FileId(1)
    path = FilePath(
        path=Path("C:/test/file.txt"),
        name="file.txt",
        ext=".txt",
        size=1024,
        mtime=1609459200.0
    )
    metadata = FileMetadata.text_file(encoding="utf-8")
    hash_info = FileHashInfo(hash_strong="abc123")
    
    file1 = File(file_id=file_id, path=path, metadata=metadata, hash_info=hash_info)
    file2 = File(file_id=file_id, path=path, metadata=metadata, hash_info=hash_info)
    
    # 같은 ID이면 동일한 엔티티
    assert file1 == file2
    
    # 다른 ID이면 다른 엔티티
    file3 = File(file_id=FileId(2), path=path, metadata=metadata, hash_info=hash_info)
    assert file1 != file3


def test_file_hash():
    """File 엔티티 해시 테스트."""
    file_id = FileId(1)
    path = FilePath(
        path=Path("C:/test/file.txt"),
        name="file.txt",
        ext=".txt",
        size=1024,
        mtime=1609459200.0
    )
    metadata = FileMetadata.text_file(encoding="utf-8")
    hash_info = FileHashInfo(hash_strong="abc123")
    
    file1 = File(file_id=file_id, path=path, metadata=metadata, hash_info=hash_info)
    file2 = File(file_id=file_id, path=path, metadata=metadata, hash_info=hash_info)
    
    # 같은 ID이면 같은 해시
    assert hash(file1) == hash(file2)
    
    # 다른 ID이면 다른 해시
    file3 = File(file_id=FileId(2), path=path, metadata=metadata, hash_info=hash_info)
    assert hash(file1) != hash(file3)


def test_add_flag():
    """플래그 추가 테스트."""
    file_entity = _create_sample_file()
    
    file_entity.add_flag("BINARY_SUSPECT")
    assert file_entity.has_flag("BINARY_SUSPECT")
    assert len(file_entity.flags) == 1
    
    file_entity.add_flag("DECODE_FAIL")
    assert file_entity.has_flag("DECODE_FAIL")
    assert len(file_entity.flags) == 2


def test_remove_flag():
    """플래그 제거 테스트."""
    file_entity = _create_sample_file()
    
    file_entity.add_flag("BINARY_SUSPECT")
    file_entity.add_flag("DECODE_FAIL")
    assert len(file_entity.flags) == 2
    
    file_entity.remove_flag("BINARY_SUSPECT")
    assert not file_entity.has_flag("BINARY_SUSPECT")
    assert file_entity.has_flag("DECODE_FAIL")
    assert len(file_entity.flags) == 1


def test_add_error():
    """에러 추가 테스트."""
    file_entity = _create_sample_file()
    
    file_entity.add_error(1)
    assert file_entity.has_errors()
    assert 1 in file_entity.errors
    assert len(file_entity.errors) == 1
    
    # 중복 추가 방지
    file_entity.add_error(1)
    assert len(file_entity.errors) == 1
    
    file_entity.add_error(2)
    assert len(file_entity.errors) == 2


def test_remove_error():
    """에러 제거 테스트."""
    file_entity = _create_sample_file()
    
    file_entity.add_error(1)
    file_entity.add_error(2)
    assert len(file_entity.errors) == 2
    
    file_entity.remove_error(1)
    assert 1 not in file_entity.errors
    assert 2 in file_entity.errors
    assert len(file_entity.errors) == 1


def test_update_metadata():
    """메타데이터 업데이트 테스트."""
    file_entity = _create_sample_file()
    
    original_metadata = file_entity.metadata
    assert original_metadata.encoding_detected == "utf-8"
    
    new_metadata = FileMetadata.text_file(encoding="utf-16", confidence=0.9)
    file_entity.update_metadata(new_metadata)
    
    assert file_entity.metadata.encoding_detected == "utf-16"
    assert file_entity.metadata.encoding_confidence == 0.9


def test_update_hash_info():
    """해시 정보 업데이트 테스트."""
    file_entity = _create_sample_file()
    
    original_hash = file_entity.hash_info
    assert original_hash.hash_strong == "abc123"
    
    new_hash = FileHashInfo(
        hash_strong="xyz789",
        fingerprint_fast="fast123"
    )
    file_entity.update_hash_info(new_hash)
    
    assert file_entity.hash_info.hash_strong == "xyz789"
    assert file_entity.hash_info.fingerprint_fast == "fast123"


def test_is_text_file():
    """텍스트 파일 확인 테스트."""
    # 텍스트 파일
    text_file = _create_sample_file()
    assert text_file.is_text_file()
    
    # 바이너리 파일
    binary_file = _create_sample_file(is_text=False)
    assert not binary_file.is_text_file()


def test_is_empty():
    """빈 파일 확인 테스트."""
    # 빈 파일
    empty_file = _create_sample_file(size=0)
    assert empty_file.is_empty()
    
    # 비어있지 않은 파일
    non_empty_file = _create_sample_file(size=1024)
    assert not non_empty_file.is_empty()


def test_has_hash():
    """해시 정보 확인 테스트."""
    # 해시 있음
    file_with_hash = _create_sample_file()
    assert file_with_hash.has_hash()
    
    # 해시 없음
    file_without_hash = File(
        file_id=FileId(1),
        path=FilePath(
            path=Path("C:/test/file.txt"),
            name="file.txt",
            ext=".txt",
            size=1024,
            mtime=1609459200.0
        ),
        metadata=FileMetadata.text_file(encoding="utf-8"),
        hash_info=FileHashInfo()  # 빈 해시
    )
    assert not file_without_hash.has_hash()


def _create_sample_file(size: int = 1024, is_text: bool = True) -> File:
    """샘플 File 엔티티 생성 헬퍼.
    
    Args:
        size: 파일 크기
        is_text: 텍스트 파일 여부
    
    Returns:
        File 엔티티
    """
    file_id = FileId(1)
    path = FilePath(
        path=Path("C:/test/file.txt"),
        name="file.txt",
        ext=".txt",
        size=size,
        mtime=1609459200.0
    )
    
    if is_text:
        metadata = FileMetadata.text_file(encoding="utf-8")
    else:
        metadata = FileMetadata.binary_file()
    
    hash_info = FileHashInfo(hash_strong="abc123")
    
    return File(
        file_id=file_id,
        path=path,
        metadata=metadata,
        hash_info=hash_info
    )
