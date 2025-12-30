"""
테스트 설정 및 픽스처

공통 테스트 설정과 픽스처를 제공합니다.
"""

import tempfile
from pathlib import Path
from typing import Generator

import pytest


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """임시 디렉토리 픽스처.
    
    테스트용 임시 디렉토리를 생성하고 테스트 후 정리합니다.
    
    Yields:
        임시 디렉토리 Path 객체
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_txt_file(temp_dir: Path) -> Path:
    """샘플 .txt 파일 픽스처.
    
    Args:
        temp_dir: 임시 디렉토리
        
    Returns:
        생성된 .txt 파일 경로
    """
    file_path = temp_dir / "sample.txt"
    file_path.write_text("샘플 텍스트 파일 내용", encoding="utf-8")
    return file_path


@pytest.fixture
def sample_files(temp_dir: Path) -> list[Path]:
    """여러 샘플 파일 픽스처.
    
    Args:
        temp_dir: 임시 디렉토리
        
    Returns:
        생성된 파일 경로 리스트
    """
    files = []
    for i in range(3):
        file_path = temp_dir / f"file_{i}.txt"
        file_path.write_text(f"파일 {i} 내용", encoding="utf-8")
        files.append(file_path)
    return files

