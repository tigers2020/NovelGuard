"""FilePath Value Object 테스트."""

import pytest
from pathlib import Path
from datetime import datetime
from domain.value_objects.file_path import FilePath


def test_file_path_creation():
    """FilePath 생성 테스트."""
    file_path = FilePath(
        path=Path("C:/test/file.txt"),
        name="file.txt",
        ext=".txt",
        size=1024,
        mtime=1609459200.0
    )
    
    assert file_path.path == Path("C:/test/file.txt")
    assert file_path.name == "file.txt"
    assert file_path.ext == ".txt"
    assert file_path.size == 1024
    assert file_path.mtime == 1609459200.0


def test_file_path_immutable():
    """FilePath 불변성 테스트."""
    file_path = FilePath(
        path=Path("C:/test/file.txt"),
        name="file.txt",
        ext=".txt",
        size=1024,
        mtime=1609459200.0
    )
    
    with pytest.raises(Exception):  # FrozenInstanceError
        file_path.size = 2048  # type: ignore


def test_file_path_validation_negative_size():
    """FilePath 검증: 음수 크기 테스트."""
    with pytest.raises(ValueError, match="File size must be non-negative"):
        FilePath(
            path=Path("C:/test/file.txt"),
            name="file.txt",
            ext=".txt",
            size=-1,
            mtime=1609459200.0
        )


def test_file_path_validation_negative_mtime():
    """FilePath 검증: 음수 수정 시간 테스트."""
    with pytest.raises(ValueError, match="Modification time must be non-negative"):
        FilePath(
            path=Path("C:/test/file.txt"),
            name="file.txt",
            ext=".txt",
            size=1024,
            mtime=-1.0
        )


def test_mtime_datetime():
    """mtime_datetime 속성 테스트."""
    file_path = FilePath(
        path=Path("C:/test/file.txt"),
        name="file.txt",
        ext=".txt",
        size=1024,
        mtime=1609459200.0
    )
    
    dt = file_path.mtime_datetime
    assert dt is not None
    assert isinstance(dt, datetime)
    
    # mtime이 0인 경우
    file_path_zero = FilePath(
        path=Path("C:/test/file.txt"),
        name="file.txt",
        ext=".txt",
        size=1024,
        mtime=0.0
    )
    assert file_path_zero.mtime_datetime is None


def test_from_path_str():
    """from_path_str 클래스 메서드 테스트."""
    file_path = FilePath.from_path_str(
        path_str="C:/test/file.TXT",
        size=1024,
        mtime=1609459200.0
    )
    
    assert file_path.path == Path("C:/test/file.TXT")
    assert file_path.name == "file.TXT"
    assert file_path.ext == ".txt"  # 소문자로 변환됨
    assert file_path.size == 1024
    assert file_path.mtime == 1609459200.0


def test_is_empty():
    """is_empty 메서드 테스트."""
    # 빈 파일
    empty_file = FilePath(
        path=Path("C:/test/empty.txt"),
        name="empty.txt",
        ext=".txt",
        size=0,
        mtime=1609459200.0
    )
    assert empty_file.is_empty()
    
    # 비어있지 않은 파일
    non_empty_file = FilePath(
        path=Path("C:/test/file.txt"),
        name="file.txt",
        ext=".txt",
        size=1024,
        mtime=1609459200.0
    )
    assert not non_empty_file.is_empty()


def test_is_large():
    """is_large 메서드 테스트."""
    # 10MB보다 작은 파일
    small_file = FilePath(
        path=Path("C:/test/small.txt"),
        name="small.txt",
        ext=".txt",
        size=5 * 1024 * 1024,  # 5MB
        mtime=1609459200.0
    )
    assert not small_file.is_large()
    
    # 10MB보다 큰 파일
    large_file = FilePath(
        path=Path("C:/test/large.txt"),
        name="large.txt",
        ext=".txt",
        size=15 * 1024 * 1024,  # 15MB
        mtime=1609459200.0
    )
    assert large_file.is_large()
    
    # 사용자 정의 임계값 (5MB)
    assert small_file.is_large(threshold_mb=3)  # 5MB > 3MB
    assert not small_file.is_large(threshold_mb=7)  # 5MB < 7MB
