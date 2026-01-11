"""Version Selection Service 테스트."""

from pathlib import Path

from domain.entities.file import File
from domain.value_objects.file_path import FilePath
from domain.value_objects.file_metadata import FileMetadata
from domain.value_objects.file_hash import FileHashInfo
from domain.value_objects.file_id import create_file_id
from domain.services.version_selector import VersionSelectionService


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


class TestVersionSelectionService:
    """VersionSelectionService 테스트."""
    
    def setup_method(self):
        """각 테스트 전 실행."""
        self.service = VersionSelectionService()
    
    def test_select_best_version_empty(self):
        """빈 리스트면 None."""
        result = self.service.select_best_version([])
        assert result is None
    
    def test_select_best_version_single(self):
        """파일 하나면 그것 반환."""
        files = [create_test_file(1, "file.txt")]
        result = self.service.select_best_version(files)
        assert result is not None
        assert result.file_id == 1
    
    def test_select_auto_with_filename_pattern(self):
        """auto: 파일명 패턴 우선."""
        files = [
            create_test_file(1, "novel_v1.txt", size=5000, mtime=3000.0),
            create_test_file(2, "novel_v3.txt", size=1000, mtime=1000.0),  # v3
            create_test_file(3, "novel_v2.txt", size=3000, mtime=2000.0),
        ]
        
        result = self.service.select_best_version(files, strategy="auto")
        assert result is not None
        assert result.file_id == 2  # v3이 선택됨 (크기/시간 무시)
    
    def test_select_auto_without_filename_pattern(self):
        """auto: 패턴 없으면 품질 점수."""
        files = [
            create_test_file(
                1, "fileA.txt",
                size=1000, mtime=1000.0, encoding_confidence=0.5
            ),
            create_test_file(
                2, "fileB.txt",
                size=5000, mtime=3000.0, encoding_confidence=0.95  # 최고 품질
            ),
            create_test_file(
                3, "fileC.txt",
                size=3000, mtime=2000.0, encoding_confidence=0.8
            ),
        ]
        
        result = self.service.select_best_version(files, strategy="auto")
        assert result is not None
        assert result.file_id == 2  # 품질 점수 최고
    
    def test_select_filename_strategy(self):
        """filename 전략."""
        files = [
            create_test_file(1, "novel_v1.txt"),
            create_test_file(2, "novel_v5.txt"),
            create_test_file(3, "novel_v3.txt"),
        ]
        
        result = self.service.select_best_version(files, strategy="filename")
        assert result is not None
        assert result.file_id == 2  # v5
    
    def test_select_filename_strategy_no_pattern(self):
        """filename 전략, 패턴 없으면 첫 번째."""
        files = [
            create_test_file(1, "fileA.txt"),
            create_test_file(2, "fileB.txt"),
        ]
        
        result = self.service.select_best_version(files, strategy="filename")
        assert result is not None
        assert result.file_id == 1  # 폴백으로 첫 번째
    
    def test_select_mtime_strategy(self):
        """mtime 전략."""
        files = [
            create_test_file(1, "file1.txt", mtime=1000.0),
            create_test_file(2, "file2.txt", mtime=5000.0),  # 최신
            create_test_file(3, "file3.txt", mtime=3000.0),
        ]
        
        result = self.service.select_best_version(files, strategy="mtime")
        assert result is not None
        assert result.file_id == 2
    
    def test_select_size_strategy(self):
        """size 전략."""
        files = [
            create_test_file(1, "file1.txt", size=1000),
            create_test_file(2, "file2.txt", size=8000),  # 가장 큼
            create_test_file(3, "file3.txt", size=5000),
        ]
        
        result = self.service.select_best_version(files, strategy="size")
        assert result is not None
        assert result.file_id == 2
    
    def test_select_quality_strategy(self):
        """quality 전략."""
        files = [
            create_test_file(
                1, "file1.txt",
                size=1000, mtime=1000.0, encoding_confidence=0.5
            ),
            create_test_file(
                2, "file2.txt",
                size=8000, mtime=5000.0, encoding_confidence=0.98  # 최고
            ),
            create_test_file(
                3, "file3.txt",
                size=5000, mtime=3000.0, encoding_confidence=0.8
            ),
        ]
        
        result = self.service.select_best_version(files, strategy="quality")
        assert result is not None
        assert result.file_id == 2
    
    def test_invalid_strategy(self):
        """잘못된 전략이면 에러."""
        import pytest
        
        # 여러 파일 전달 (단일 파일이면 전략 체크 없이 바로 반환)
        files = [
            create_test_file(1, "file1.txt"),
            create_test_file(2, "file2.txt"),
        ]
        
        with pytest.raises(ValueError, match="Invalid strategy"):
            self.service.select_best_version(files, strategy="invalid")
    
    def test_select_canonical_for_group(self):
        """그룹용 canonical 선택."""
        file1 = create_test_file(10, "novel_v1.txt")
        file2 = create_test_file(11, "novel_v3.txt")  # 선택될 것
        file3 = create_test_file(12, "novel_v2.txt")
        
        file_lookup = {
            10: file1,
            11: file2,
            12: file3,
        }
        
        canonical_id = self.service.select_canonical_for_group(
            file_ids=[10, 11, 12],
            file_lookup=file_lookup,
            strategy="auto"
        )
        
        assert canonical_id == 11  # v3
    
    def test_select_canonical_for_group_empty(self):
        """빈 그룹이면 None."""
        canonical_id = self.service.select_canonical_for_group(
            file_ids=[],
            file_lookup={},
            strategy="auto"
        )
        
        assert canonical_id is None
    
    def test_select_canonical_for_group_missing_files(self):
        """lookup에 없는 파일은 무시."""
        file1 = create_test_file(10, "file1.txt")
        
        file_lookup = {
            10: file1,
            # 11, 12는 없음
        }
        
        canonical_id = self.service.select_canonical_for_group(
            file_ids=[10, 11, 12],
            file_lookup=file_lookup,
            strategy="auto"
        )
        
        assert canonical_id == 10  # 유일하게 존재하는 파일


class TestVersionSelectionServiceIntegration:
    """VersionSelectionService 통합 테스트."""
    
    def setup_method(self):
        """각 테스트 전 실행."""
        self.service = VersionSelectionService()
    
    def test_realistic_scenario(self):
        """실제 시나리오: 여러 버전 파일."""
        files = [
            # 오래된 버전 (v1)
            create_test_file(
                1, "소설_완결_v1.txt",
                size=50000, mtime=1000.0, encoding_confidence=0.7
            ),
            # 중간 버전 (v2)
            create_test_file(
                2, "소설_완결_v2.txt",
                size=52000, mtime=2000.0, encoding_confidence=0.85
            ),
            # 최신 버전 (v3) - 선택될 것
            create_test_file(
                3, "소설_완결_v3.txt",
                size=55000, mtime=3000.0, encoding_confidence=0.95
            ),
            # 버전 표시 없는 파일 (무시됨)
            create_test_file(
                4, "소설_완결.txt",
                size=60000, mtime=4000.0, encoding_confidence=0.99
            ),
        ]
        
        result = self.service.select_best_version(files, strategy="auto")
        assert result is not None
        assert result.file_id == 3  # v3이 선택됨 (파일명 패턴 우선)
