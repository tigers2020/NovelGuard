"""PreviewStats ValueObject 테스트."""

import pytest

from domain.value_objects.preview_stats import PreviewStats


class TestPreviewStatsCreation:
    """PreviewStats 생성 테스트."""
    
    def test_create_minimal(self):
        """최소 정보로 생성."""
        stats = PreviewStats(
            estimated_total_files=100,
            top_extensions={".txt": 70, ".md": 30}
        )
        
        assert stats.estimated_total_files == 100
        assert stats.top_extensions == {".txt": 70, ".md": 30}
        assert stats.estimated_bytes is None
    
    def test_create_with_bytes(self):
        """크기 추정과 함께 생성."""
        stats = PreviewStats(
            estimated_total_files=100,
            top_extensions={".txt": 70},
            estimated_bytes=1024000
        )
        
        assert stats.estimated_bytes == 1024000
    
    def test_create_empty(self):
        """빈 통계 생성."""
        stats = PreviewStats(
            estimated_total_files=0,
            top_extensions={}
        )
        
        assert stats.estimated_total_files == 0
        assert stats.top_extensions == {}


class TestPreviewStatsValidation:
    """PreviewStats 검증 테스트."""
    
    def test_invalid_negative_files(self):
        """파일 수가 음수이면 실패."""
        with pytest.raises(ValueError, match="estimated_total_files must be >= 0"):
            PreviewStats(
                estimated_total_files=-1,
                top_extensions={}
            )
    
    def test_invalid_negative_bytes(self):
        """크기가 음수이면 실패."""
        with pytest.raises(ValueError, match="estimated_bytes must be >= 0"):
            PreviewStats(
                estimated_total_files=100,
                top_extensions={".txt": 70},
                estimated_bytes=-1
            )
    
    def test_invalid_negative_extension_count(self):
        """확장자 파일 수가 음수이면 실패."""
        with pytest.raises(ValueError, match="Extension count .* must be >= 0"):
            PreviewStats(
                estimated_total_files=100,
                top_extensions={".txt": -10}
            )


class TestPreviewStatsImmutability:
    """PreviewStats 불변성 테스트."""
    
    def test_frozen(self):
        """frozen=True로 속성 변경 불가."""
        stats = PreviewStats(
            estimated_total_files=100,
            top_extensions={".txt": 70}
        )
        
        with pytest.raises(Exception):  # FrozenInstanceError
            stats.estimated_total_files = 200  # type: ignore


class TestPreviewStatsProperties:
    """PreviewStats 속성 테스트."""
    
    def test_has_size_estimate_true(self):
        """크기 추정 정보 있음."""
        stats = PreviewStats(
            estimated_total_files=100,
            top_extensions={".txt": 70},
            estimated_bytes=1024000
        )
        
        assert stats.has_size_estimate is True
    
    def test_has_size_estimate_false(self):
        """크기 추정 정보 없음."""
        stats = PreviewStats(
            estimated_total_files=100,
            top_extensions={".txt": 70}
        )
        
        assert stats.has_size_estimate is False
    
    def test_is_empty_true(self):
        """파일 없음."""
        stats = PreviewStats(
            estimated_total_files=0,
            top_extensions={}
        )
        
        assert stats.is_empty is True
    
    def test_is_empty_false(self):
        """파일 있음."""
        stats = PreviewStats(
            estimated_total_files=100,
            top_extensions={".txt": 70}
        )
        
        assert stats.is_empty is False
    
    def test_extension_count(self):
        """확장자 종류 수."""
        stats = PreviewStats(
            estimated_total_files=100,
            top_extensions={".txt": 70, ".md": 20, ".pdf": 10}
        )
        
        assert stats.extension_count == 3


class TestPreviewStatsMethods:
    """PreviewStats 메서드 테스트."""
    
    def test_get_most_common_extension(self):
        """가장 많은 확장자 반환."""
        stats = PreviewStats(
            estimated_total_files=100,
            top_extensions={".txt": 70, ".md": 20, ".pdf": 10}
        )
        
        assert stats.get_most_common_extension() == ".txt"
    
    def test_get_most_common_extension_empty(self):
        """확장자 없으면 None."""
        stats = PreviewStats(
            estimated_total_files=0,
            top_extensions={}
        )
        
        assert stats.get_most_common_extension() is None
    
    def test_get_extension_percentage(self):
        """확장자 비율 계산."""
        stats = PreviewStats(
            estimated_total_files=100,
            top_extensions={".txt": 70, ".md": 30}
        )
        
        assert stats.get_extension_percentage(".txt") == 70.0
        assert stats.get_extension_percentage(".md") == 30.0
    
    def test_get_extension_percentage_not_exist(self):
        """없는 확장자는 0.0."""
        stats = PreviewStats(
            estimated_total_files=100,
            top_extensions={".txt": 70}
        )
        
        assert stats.get_extension_percentage(".pdf") == 0.0
    
    def test_get_extension_percentage_empty_stats(self):
        """빈 통계에서 비율은 0.0."""
        stats = PreviewStats(
            estimated_total_files=0,
            top_extensions={}
        )
        
        assert stats.get_extension_percentage(".txt") == 0.0
    
    def test_has_extension_true(self):
        """확장자 존재 확인 (있음)."""
        stats = PreviewStats(
            estimated_total_files=100,
            top_extensions={".txt": 70, ".md": 30}
        )
        
        assert stats.has_extension(".txt") is True
        assert stats.has_extension(".md") is True
    
    def test_has_extension_false(self):
        """확장자 존재 확인 (없음)."""
        stats = PreviewStats(
            estimated_total_files=100,
            top_extensions={".txt": 70}
        )
        
        assert stats.has_extension(".pdf") is False
    
    def test_get_top_extensions(self):
        """상위 N개 확장자 반환."""
        stats = PreviewStats(
            estimated_total_files=100,
            top_extensions={
                ".txt": 70,
                ".md": 20,
                ".pdf": 5,
                ".jpg": 3,
                ".png": 2
            }
        )
        
        top_2 = stats.get_top_extensions(2)
        assert top_2 == [(".txt", 70), (".md", 20)]
        
        top_5 = stats.get_top_extensions(5)
        assert len(top_5) == 5
        assert top_5[0] == (".txt", 70)
        assert top_5[-1] == (".png", 2)
    
    def test_get_top_extensions_limit_exceeds(self):
        """limit이 전체 개수보다 크면 전부 반환."""
        stats = PreviewStats(
            estimated_total_files=100,
            top_extensions={".txt": 70, ".md": 30}
        )
        
        top_10 = stats.get_top_extensions(10)
        assert len(top_10) == 2


class TestPreviewStatsUseCases:
    """PreviewStats 실제 사용 시나리오 테스트."""
    
    def test_typical_scan_result(self):
        """일반적인 스캔 결과."""
        stats = PreviewStats(
            estimated_total_files=1523,
            top_extensions={
                ".txt": 1200,
                ".md": 300,
                ".pdf": 20,
                ".docx": 3
            },
            estimated_bytes=1024000000
        )
        
        # 기본 정보 확인
        assert not stats.is_empty
        assert stats.has_size_estimate
        assert stats.extension_count == 4
        
        # 가장 많은 확장자
        assert stats.get_most_common_extension() == ".txt"
        
        # 상위 2개 확장자
        top_2 = stats.get_top_extensions(2)
        assert top_2 == [(".txt", 1200), (".md", 300)]
        
        # 텍스트 파일 비율 (약 78.8%)
        txt_percentage = stats.get_extension_percentage(".txt")
        assert 78.0 < txt_percentage < 79.0
    
    def test_empty_folder(self):
        """빈 폴더 스캔 결과."""
        stats = PreviewStats(
            estimated_total_files=0,
            top_extensions={}
        )
        
        assert stats.is_empty
        assert stats.extension_count == 0
        assert stats.get_most_common_extension() is None
        assert stats.get_top_extensions(5) == []
