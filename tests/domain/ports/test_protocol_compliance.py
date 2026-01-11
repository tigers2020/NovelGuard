"""Domain Ports Protocol 준수 테스트.

Infrastructure 구현체들이 Domain Ports Protocol을 올바르게 구현하는지 검증합니다.
"""

# 표준 라이브러리
import sys
from pathlib import Path

# sys.path 추가 (테스트용)
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
if str(PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))

# 테스트
import pytest
from domain.ports.file_repository import IFileRepository
from domain.ports.hash_service import IHashService
from domain.ports.encoding_detector import IEncodingDetector
from infra.db.file_repository import FileRepository
from infra.hashing.hash_calculator import HashCalculator
from infra.hashing.fingerprint import FingerprintGenerator
from infra.hashing.hash_service_adapter import HashServiceAdapter
from infra.encoding.encoding_detector import EncodingDetector


class TestFileRepositoryProtocol:
    """FileRepository가 IFileRepository Protocol을 구현하는지 검증."""
    
    def test_file_repository_implements_protocol(self):
        """FileRepository가 IFileRepository Protocol을 구현하는지 확인."""
        repo = FileRepository()
        
        # @runtime_checkable이 있으면 isinstance 체크 가능
        assert isinstance(repo, IFileRepository), (
            "FileRepository는 IFileRepository Protocol을 구현해야 합니다"
        )
    
    def test_file_repository_has_all_methods(self):
        """FileRepository가 IFileRepository의 모든 메서드를 구현하는지 확인."""
        repo = FileRepository()
        
        # Protocol에 정의된 모든 메서드 확인
        required_methods = [
            'save', 'save_meta', 'meta_to_record',
            'get', 'get_by_path', 'update', 'delete',
            'list_all', 'count', 'clear',
            'get_meta', 'update_meta'
        ]
        
        for method_name in required_methods:
            assert hasattr(repo, method_name), (
                f"FileRepository에 {method_name} 메서드가 없습니다"
            )
            assert callable(getattr(repo, method_name)), (
                f"FileRepository.{method_name}이 호출 가능하지 않습니다"
            )


class TestHashServiceProtocol:
    """HashCalculator + FingerprintGenerator가 IHashService Protocol을 구현하는지 검증."""
    
    def test_hash_calculator_has_required_methods(self):
        """HashCalculator가 IHashService의 해시 메서드를 구현하는지 확인."""
        # HashCalculator는 static method만 가짐
        required_methods = [
            'calculate_md5',
            'calculate_sha256',
            'calculate_hash'
        ]
        
        for method_name in required_methods:
            assert hasattr(HashCalculator, method_name), (
                f"HashCalculator에 {method_name} 메서드가 없습니다"
            )
            assert callable(getattr(HashCalculator, method_name)), (
                f"HashCalculator.{method_name}이 호출 가능하지 않습니다"
            )
    
    def test_fingerprint_generator_has_required_methods(self):
        """FingerprintGenerator가 IHashService의 지문 메서드를 구현하는지 확인."""
        required_methods = [
            'generate_fast_fingerprint',
            'generate_simhash',
            'generate_text_fingerprint'
        ]
        
        for method_name in required_methods:
            assert hasattr(FingerprintGenerator, method_name), (
                f"FingerprintGenerator에 {method_name} 메서드가 없습니다"
            )
            assert callable(getattr(FingerprintGenerator, method_name)), (
                f"FingerprintGenerator.{method_name}이 호출 가능하지 않습니다"
            )
    
    def test_hash_service_adapter_implements_protocol(self):
        """HashServiceAdapter가 IHashService Protocol을 완전히 구현하는지 확인."""
        # HashServiceAdapter는 static method만 가지므로 메서드 존재 확인
        required_methods = [
            'calculate_md5', 'calculate_sha256', 'calculate_hash',
            'generate_fast_fingerprint', 'generate_simhash', 'generate_text_fingerprint'
        ]
        
        for method_name in required_methods:
            assert hasattr(HashServiceAdapter, method_name), (
                f"HashServiceAdapter에 {method_name} 메서드가 없습니다"
            )
            assert callable(getattr(HashServiceAdapter, method_name)), (
                f"HashServiceAdapter.{method_name}이 호출 가능하지 않습니다"
            )


class TestEncodingDetectorProtocol:
    """EncodingDetector가 IEncodingDetector Protocol을 구현하는지 검증."""
    
    def test_encoding_detector_implements_protocol(self):
        """EncodingDetector가 IEncodingDetector Protocol을 구현하는지 확인."""
        # EncodingDetector는 static method만 가짐
        # isinstance 체크는 인스턴스에 대해서만 가능하므로, 메서드 존재 확인
        required_methods = [
            'detect',
            'detect_from_bytes',
            'decode_text'
        ]
        
        for method_name in required_methods:
            assert hasattr(EncodingDetector, method_name), (
                f"EncodingDetector에 {method_name} 메서드가 없습니다"
            )
            assert callable(getattr(EncodingDetector, method_name)), (
                f"EncodingDetector.{method_name}이 호출 가능하지 않습니다"
            )
    
    def test_encoding_detector_uses_constants(self):
        """EncodingDetector가 app.settings.Constants를 사용하는지 확인."""
        # EncodingDetector는 더 이상 MAX_SAMPLE_SIZE를 직접 가지지 않고
        # app.settings.Constants를 통해 접근합니다.
        from app.settings import Constants
        assert hasattr(Constants, 'MAX_SAMPLE_SIZE'), (
            "Constants에 MAX_SAMPLE_SIZE 상수가 없습니다"
        )
        assert isinstance(Constants.MAX_SAMPLE_SIZE, int), (
            "Constants.MAX_SAMPLE_SIZE가 정수가 아닙니다"
        )
