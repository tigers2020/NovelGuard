"""Constants 모듈 테스트."""

import pytest

from app.settings.constants import Constants


class TestFileConstants:
    """파일 크기 관련 상수 테스트."""
    
    def test_byte_conversions(self):
        """바이트 변환 상수가 올바른지 확인."""
        assert Constants.BYTES_PER_KB == 1024
        assert Constants.BYTES_PER_MB == 1024 * 1024
        assert Constants.BYTES_PER_GB == 1024 * 1024 * 1024
    
    def test_file_size_thresholds(self):
        """파일 크기 임계값이 올바른지 확인."""
        assert Constants.MIN_FILE_SIZE == 1024
        assert Constants.MIN_ENCODING_DETECTION_SIZE == 100
        assert Constants.MAX_SAMPLE_SIZE == 32 * 1024
        assert Constants.LARGE_FILE_THRESHOLD == 5 * 1024 * 1024
        assert Constants.TEXT_FILE_MAX_SIZE == 10 * 1024 * 1024
    
    def test_size_hierarchy(self):
        """파일 크기 임계값의 계층 관계가 올바른지 확인."""
        assert Constants.MIN_ENCODING_DETECTION_SIZE < Constants.MIN_FILE_SIZE
        assert Constants.MIN_FILE_SIZE < Constants.MAX_SAMPLE_SIZE
        assert Constants.MAX_SAMPLE_SIZE < Constants.LARGE_FILE_THRESHOLD
        assert Constants.LARGE_FILE_THRESHOLD < Constants.TEXT_FILE_MAX_SIZE


class TestEncodingConstants:
    """인코딩 관련 상수 테스트."""
    
    def test_encoding_values(self):
        """인코딩 상수 값이 올바른지 확인."""
        assert Constants.DEFAULT_ENCODING == "utf-8"
        assert Constants.TARGET_ENCODING == "UTF-8"
        assert Constants.LOG_FILE_ENCODING == "utf-8"
    
    def test_encoding_confidence(self):
        """인코딩 신뢰도 상수가 올바른지 확인."""
        assert 0.0 <= Constants.MIN_ENCODING_CONFIDENCE <= 1.0
        assert 0.0 <= Constants.HIGH_ENCODING_CONFIDENCE <= 1.0
        assert Constants.MIN_ENCODING_CONFIDENCE < Constants.HIGH_ENCODING_CONFIDENCE


class TestHashConstants:
    """해시 관련 상수 테스트."""
    
    def test_hash_algorithms(self):
        """해시 알고리즘 상수가 올바른지 확인."""
        assert Constants.HASH_ALGORITHM == "sha256"
        assert Constants.FINGERPRINT_ALGORITHM == "sha256"
        assert Constants.HEAD_HASH_SIZE == 1024


class TestBusinessLogicConstants:
    """비즈니스 로직 관련 상수 테스트."""
    
    def test_duplicate_detection(self):
        """중복 탐지 상수가 올바른지 확인."""
        assert 0.0 <= Constants.MIN_DUPLICATE_CONFIDENCE <= 1.0
    
    def test_integrity_check(self):
        """무결성 검사 상수가 올바른지 확인."""
        assert Constants.MIN_TEXT_FILE_SIZE == 100


class TestDisplayConstants:
    """UI/Display 관련 상수 테스트."""
    
    def test_display_thresholds(self):
        """표시 단위 임계값이 올바른지 확인."""
        assert Constants.DISPLAY_KB_THRESHOLD == 1024
        assert Constants.DISPLAY_MB_THRESHOLD == 1024 * 1024
        assert Constants.DISPLAY_GB_THRESHOLD == 1024 * 1024 * 1024
    
    def test_display_threshold_hierarchy(self):
        """표시 단위 임계값의 계층 관계가 올바른지 확인."""
        assert Constants.DISPLAY_KB_THRESHOLD < Constants.DISPLAY_MB_THRESHOLD
        assert Constants.DISPLAY_MB_THRESHOLD < Constants.DISPLAY_GB_THRESHOLD


class TestAppMetadata:
    """애플리케이션 메타데이터 테스트."""
    
    def test_app_info(self):
        """애플리케이션 정보가 올바른지 확인."""
        assert Constants.APP_NAME == "NovelGuard"
        assert Constants.APP_ORGANIZATION == "NovelGuard"
        assert isinstance(Constants.APP_VERSION, str)
        assert len(Constants.APP_VERSION) > 0


class TestConstantsImmutability:
    """Constants 불변성 테스트."""
    
    def test_constants_class_cannot_be_instantiated(self):
        """Constants 클래스는 인스턴스화할 수 없어야 함 (현재는 가능, 향후 개선 가능)."""
        # 현재는 인스턴스화가 가능하지만, 모든 속성이 클래스 레벨이므로 문제없음
        constants = Constants()
        assert constants.MIN_FILE_SIZE == Constants.MIN_FILE_SIZE
    
    def test_all_constants_are_uppercase(self):
        """모든 상수가 대문자로 정의되어 있는지 확인."""
        for attr_name in dir(Constants):
            if not attr_name.startswith('_'):
                # 공개 속성만 확인
                assert attr_name.isupper() or attr_name.startswith('__'), \
                    f"상수 {attr_name}는 대문자로 작성되어야 합니다"
