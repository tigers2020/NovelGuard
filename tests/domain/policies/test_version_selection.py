"""Version Selection Policies 테스트."""

from pathlib import Path

from domain.entities.file import File
from domain.value_objects.file_path import FilePath
from domain.value_objects.file_metadata import FileMetadata
from domain.value_objects.file_hash import FileHashInfo
from domain.value_objects.file_id import create_file_id
from domain.policies.version_selection import (
    select_by_filename,
    select_by_mtime,
    select_by_size,
    select_by_quality_score,
    select_first,
)


def create_test_file(
    file_id: int,
    name: str,
    size: int = 1000,
    mtime: float = 1000.0,
    encoding_confidence: float | None = None
) -> File:
    """테스트용 File 생성."""
    path = FilePath(
        path=Path(f"/test/{name}"),
        name=name,
        ext=".txt",
        size=size,
        mtime=mtime
    )
    metadata = FileMetadata.text_file(
        encoding="utf-8",
        confidence=encoding_confidence
    )
    return File(
        file_id=create_file_id(file_id),
        path=path,
        metadata=metadata,
        hash_info=FileHashInfo()
    )


class TestSelectByFilename:
    """select_by_filename 테스트."""
    
    def test_select_v_pattern(self):
        """v숫자 패턴 인식."""
        files = [
            create_test_file(1, "novel_v1.txt"),
            create_test_file(2, "novel_v3.txt"),
            create_test_file(3, "novel_v2.txt"),
        ]
        
        selected = select_by_filename(files)
        assert selected is not None
        assert selected.file_id == 2  # v3이 가장 높음
    
    def test_select_upper_v_pattern(self):
        """V숫자 패턴 인식 (대문자)."""
        files = [
            create_test_file(1, "novel_V1.txt"),
            create_test_file(2, "novel_V5.txt"),
            create_test_file(3, "novel_V3.txt"),
        ]
        
        selected = select_by_filename(files)
        assert selected is not None
        assert selected.file_id == 2  # V5가 가장 높음
    
    def test_select_parentheses_pattern(self):
        """(숫자) 패턴 인식."""
        files = [
            create_test_file(1, "novel(1).txt"),
            create_test_file(2, "novel(10).txt"),
            create_test_file(3, "novel(3).txt"),
        ]
        
        selected = select_by_filename(files)
        assert selected is not None
        assert selected.file_id == 2  # (10)이 가장 높음
    
    def test_select_underscore_pattern(self):
        """_숫자 패턴 인식."""
        files = [
            create_test_file(1, "novel_1.txt"),
            create_test_file(2, "novel_5.txt"),
            create_test_file(3, "novel_2.txt"),
        ]
        
        selected = select_by_filename(files)
        assert selected is not None
        assert selected.file_id == 2  # _5가 가장 높음
    
    def test_select_hyphen_pattern(self):
        """-숫자 패턴 인식."""
        files = [
            create_test_file(1, "novel-1.txt"),
            create_test_file(2, "novel-7.txt"),
            create_test_file(3, "novel-4.txt"),
        ]
        
        selected = select_by_filename(files)
        assert selected is not None
        assert selected.file_id == 2  # -7이 가장 높음
    
    def test_no_pattern(self):
        """패턴 없으면 None."""
        files = [
            create_test_file(1, "novel.txt"),
            create_test_file(2, "story.txt"),
        ]
        
        selected = select_by_filename(files)
        assert selected is None
    
    def test_empty_list(self):
        """빈 리스트면 None."""
        selected = select_by_filename([])
        assert selected is None


class TestSelectByMtime:
    """select_by_mtime 테스트."""
    
    def test_select_newest(self):
        """가장 최신 파일 선택."""
        files = [
            create_test_file(1, "file1.txt", mtime=1000.0),
            create_test_file(2, "file2.txt", mtime=3000.0),
            create_test_file(3, "file3.txt", mtime=2000.0),
        ]
        
        selected = select_by_mtime(files)
        assert selected is not None
        assert selected.file_id == 2  # mtime=3000.0
    
    def test_empty_list(self):
        """빈 리스트면 None."""
        selected = select_by_mtime([])
        assert selected is None


class TestSelectBySize:
    """select_by_size 테스트."""
    
    def test_select_largest(self):
        """가장 큰 파일 선택."""
        files = [
            create_test_file(1, "file1.txt", size=1000),
            create_test_file(2, "file2.txt", size=5000),
            create_test_file(3, "file3.txt", size=3000),
        ]
        
        selected = select_by_size(files)
        assert selected is not None
        assert selected.file_id == 2  # size=5000
    
    def test_empty_list(self):
        """빈 리스트면 None."""
        selected = select_by_size([])
        assert selected is None


class TestSelectByQualityScore:
    """select_by_quality_score 테스트."""
    
    def test_select_best_quality(self):
        """종합 품질 점수로 선택."""
        files = [
            # 작고, 오래됨, 낮은 신뢰도
            create_test_file(
                1, "file1.txt",
                size=1000, mtime=1000.0, encoding_confidence=0.5
            ),
            # 크고, 최신, 높은 신뢰도 → 최고 점수
            create_test_file(
                2, "file2.txt",
                size=5000, mtime=3000.0, encoding_confidence=0.95
            ),
            # 중간
            create_test_file(
                3, "file3.txt",
                size=3000, mtime=2000.0, encoding_confidence=0.8
            ),
        ]
        
        selected = select_by_quality_score(files)
        assert selected is not None
        assert selected.file_id == 2  # 종합 점수 최고
    
    def test_empty_list(self):
        """빈 리스트면 None."""
        selected = select_by_quality_score([])
        assert selected is None


class TestSelectFirst:
    """select_first 테스트."""
    
    def test_select_first(self):
        """첫 번째 파일 선택."""
        files = [
            create_test_file(1, "file1.txt"),
            create_test_file(2, "file2.txt"),
            create_test_file(3, "file3.txt"),
        ]
        
        selected = select_first(files)
        assert selected is not None
        assert selected.file_id == 1  # 첫 번째
    
    def test_empty_list(self):
        """빈 리스트면 None."""
        selected = select_first([])
        assert selected is None
