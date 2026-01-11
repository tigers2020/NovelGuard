"""File Adapter 테스트."""

import warnings
from pathlib import Path

from domain.models.file_meta import FileMeta
from domain.models.file_record import FileRecord
from domain.entities.file import File
from domain.adapters.file_adapter import (
    file_meta_to_file_entity,
    file_record_to_file_entity,
    file_entity_to_file_record
)


def test_file_meta_to_file_entity():
    """FileMeta → File 엔티티 변환 테스트."""
    # Given: FileMeta
    meta = FileMeta(
        file_id=1,
        path_str="C:/test/file.txt",
        name="file.txt",
        ext=".txt",
        size=1024,
        mtime=1609459200.0,
        is_text_guess=True,
        encoding_detected="utf-8",
        encoding_confidence=0.95,
        fingerprint_fast="fast123"
    )
    
    # When: File 엔티티로 변환
    file_entity = file_meta_to_file_entity(meta)
    
    # Then: 변환 확인
    assert int(file_entity.file_id) == 1
    assert file_entity.path.path == Path("C:/test/file.txt")
    assert file_entity.path.name == "file.txt"
    assert file_entity.path.ext == ".txt"
    assert file_entity.path.size == 1024
    assert file_entity.path.mtime == 1609459200.0
    assert file_entity.metadata.is_text is True
    assert file_entity.metadata.encoding_detected == "utf-8"
    assert file_entity.metadata.encoding_confidence == 0.95
    assert file_entity.hash_info.fingerprint_fast == "fast123"
    assert file_entity.hash_info.hash_strong is None
    assert len(file_entity.flags) == 0
    assert len(file_entity.errors) == 0


def test_file_record_to_file_entity_and_back():
    """FileRecord ↔ File 엔티티 양방향 변환 테스트."""
    # Given: FileRecord
    record = FileRecord(
        file_id=1,
        path=Path("C:/test/file.txt"),
        name="file.txt",
        ext=".txt",
        size=1024,
        mtime=1609459200.0,
        is_text=True,
        encoding_detected="utf-8",
        encoding_confidence=0.95,
        newline="LF",
        hash_strong="abc123",
        fingerprint_fast="fast123",
        fingerprint_norm="norm123",
        simhash64=12345,
        flags={"FLAG1", "FLAG2"},
        errors=[1, 2, 3]
    )
    
    # When: File 엔티티로 변환
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        file_entity = file_record_to_file_entity(record)
    
    # Then: 변환 확인
    assert int(file_entity.file_id) == 1
    assert file_entity.path.path == Path("C:/test/file.txt")
    assert file_entity.path.name == "file.txt"
    assert file_entity.metadata.is_text is True
    assert file_entity.metadata.encoding_detected == "utf-8"
    assert file_entity.hash_info.hash_strong == "abc123"
    assert file_entity.hash_info.fingerprint_fast == "fast123"
    assert file_entity.flags == {"FLAG1", "FLAG2"}
    assert file_entity.errors == [1, 2, 3]
    
    # When: 다시 FileRecord로 변환
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        record_back = file_entity_to_file_record(file_entity)
    
    # Then: 원본과 동일
    assert record_back.file_id == record.file_id
    assert record_back.path == record.path
    assert record_back.name == record.name
    assert record_back.is_text == record.is_text
    assert record_back.encoding_detected == record.encoding_detected
    assert record_back.hash_strong == record.hash_strong
    assert record_back.flags == record.flags
    assert record_back.errors == record.errors


def test_file_record_to_file_entity_method():
    """FileRecord.to_file_entity() 메서드 테스트."""
    # Given: FileRecord
    record = FileRecord(
        file_id=1,
        path=Path("C:/test/file.txt"),
        name="file.txt",
        ext=".txt",
        size=1024,
        mtime=1609459200.0,
        is_text=True,
        encoding_detected="utf-8",
        hash_strong="abc123"
    )
    
    # When: to_file_entity() 호출 (DeprecationWarning 발생 예상)
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        file_entity = record.to_file_entity()
        
        # Then: DeprecationWarning 발생 확인
        assert len(w) == 1
        assert issubclass(w[0].category, DeprecationWarning)
        assert "deprecated" in str(w[0].message).lower()
    
    # Then: 변환 확인
    assert int(file_entity.file_id) == 1
    assert file_entity.path.path == Path("C:/test/file.txt")


def test_file_from_file_record_classmethod():
    """File.from_file_record() 클래스 메서드 테스트."""
    # Given: FileRecord
    record = FileRecord(
        file_id=1,
        path=Path("C:/test/file.txt"),
        name="file.txt",
        ext=".txt",
        size=1024,
        mtime=1609459200.0,
        is_text=True,
        hash_strong="abc123"
    )
    
    # When: File.from_file_record() 호출
    file_entity = File.from_file_record(record)
    
    # Then: 변환 확인
    assert int(file_entity.file_id) == 1
    assert file_entity.path.path == Path("C:/test/file.txt")
    assert file_entity.hash_info.hash_strong == "abc123"


def test_file_to_file_record_method():
    """File.to_file_record() 메서드 테스트."""
    # Given: File 엔티티
    from domain.value_objects import FileId, FilePath, FileMetadata, FileHashInfo
    
    file_entity = File(
        file_id=FileId(1),
        path=FilePath(
            path=Path("C:/test/file.txt"),
            name="file.txt",
            ext=".txt",
            size=1024,
            mtime=1609459200.0
        ),
        metadata=FileMetadata.text_file(encoding="utf-8"),
        hash_info=FileHashInfo(hash_strong="abc123")
    )
    
    # When: to_file_record() 호출
    record = file_entity.to_file_record()
    
    # Then: 변환 확인
    assert record.file_id == 1
    assert record.path == Path("C:/test/file.txt")
    assert record.name == "file.txt"
    assert record.is_text is True
    assert record.encoding_detected == "utf-8"
    assert record.hash_strong == "abc123"


def test_deprecation_warnings():
    """Deprecation 경고 발생 확인."""
    record = FileRecord(
        file_id=1,
        path=Path("C:/test/file.txt"),
        name="file.txt",
        ext=".txt",
        size=1024,
        mtime=1609459200.0
    )
    
    # file_record_to_file_entity() deprecation
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        file_record_to_file_entity(record)
        assert len(w) == 1
        assert issubclass(w[0].category, DeprecationWarning)
    
    # file_entity_to_file_record() deprecation
    file_entity = File.from_file_record(record)
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        file_entity_to_file_record(file_entity)
        assert len(w) == 1
        assert issubclass(w[0].category, DeprecationWarning)
