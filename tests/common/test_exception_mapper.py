"""Exception Mapper 테스트."""

import pytest

from common.errors import (
    InfraError,
    DomainError,
    FileSystemError,
    DatabaseError,
    EncodingDetectionError,
    IntegrityCheckError,
    ValidationError,
    DuplicateDetectionError,
)
from common.exception_mapper import (
    map_infra_error,
    map_to_integrity_error,
    map_to_validation_error,
    map_to_duplicate_detection_error,
)


class TestMapInfraError:
    """map_infra_error() 함수 테스트."""
    
    def test_file_system_error_to_integrity_error(self):
        """FileSystemError가 IntegrityCheckError로 변환되는지 확인."""
        infra_error = FileSystemError("파일을 읽을 수 없습니다")
        domain_error = map_infra_error(infra_error)
        
        assert isinstance(domain_error, IntegrityCheckError)
        assert str(domain_error) == "파일을 읽을 수 없습니다"
        assert domain_error.__cause__ is infra_error
    
    def test_database_error_to_validation_error(self):
        """DatabaseError가 ValidationError로 변환되는지 확인."""
        infra_error = DatabaseError("데이터베이스 연결 실패")
        domain_error = map_infra_error(infra_error)
        
        assert isinstance(domain_error, ValidationError)
        assert str(domain_error) == "데이터베이스 연결 실패"
        assert domain_error.__cause__ is infra_error
    
    def test_encoding_detection_error_to_integrity_error(self):
        """EncodingDetectionError가 IntegrityCheckError로 변환되는지 확인."""
        infra_error = EncodingDetectionError("인코딩 감지 실패")
        domain_error = map_infra_error(infra_error)
        
        assert isinstance(domain_error, IntegrityCheckError)
        assert str(domain_error) == "인코딩 감지 실패"
        assert domain_error.__cause__ is infra_error
    
    def test_unmapped_infra_error_to_default(self):
        """매핑되지 않은 InfraError가 기본 DomainError로 변환되는지 확인."""
        infra_error = InfraError("알 수 없는 인프라 오류")
        domain_error = map_infra_error(infra_error)
        
        assert isinstance(domain_error, DomainError)
        assert str(domain_error) == "알 수 없는 인프라 오류"
        assert domain_error.__cause__ is infra_error
    
    def test_unmapped_with_custom_default(self):
        """커스텀 기본 에러 타입을 사용하는지 확인."""
        infra_error = InfraError("알 수 없는 오류")
        domain_error = map_infra_error(infra_error, default=ValidationError)
        
        assert isinstance(domain_error, ValidationError)
        assert str(domain_error) == "알 수 없는 오류"


class TestSpecificMappers:
    """특정 에러 변환 함수 테스트."""
    
    def test_map_to_integrity_error_from_infra_error(self):
        """InfraError를 IntegrityCheckError로 변환하는지 확인."""
        infra_error = FileSystemError("파일 읽기 실패")
        domain_error = map_to_integrity_error(infra_error)
        
        assert isinstance(domain_error, IntegrityCheckError)
        assert "파일 읽기 실패" in str(domain_error)
        assert domain_error.__cause__ is infra_error
    
    def test_map_to_integrity_error_from_general_exception(self):
        """일반 예외를 IntegrityCheckError로 변환하는지 확인."""
        general_error = ValueError("잘못된 값")
        domain_error = map_to_integrity_error(general_error)
        
        assert isinstance(domain_error, IntegrityCheckError)
        assert "무결성 검사 실패" in str(domain_error)
        assert domain_error.__cause__ is general_error
    
    def test_map_to_validation_error_from_infra_error(self):
        """InfraError를 ValidationError로 변환하는지 확인."""
        infra_error = DatabaseError("쿼리 실패")
        domain_error = map_to_validation_error(infra_error)
        
        assert isinstance(domain_error, ValidationError)
        assert "쿼리 실패" in str(domain_error)
        assert domain_error.__cause__ is infra_error
    
    def test_map_to_validation_error_from_general_exception(self):
        """일반 예외를 ValidationError로 변환하는지 확인."""
        general_error = TypeError("잘못된 타입")
        domain_error = map_to_validation_error(general_error)
        
        assert isinstance(domain_error, ValidationError)
        assert "검증 실패" in str(domain_error)
        assert domain_error.__cause__ is general_error
    
    def test_map_to_duplicate_detection_error_from_infra_error(self):
        """InfraError를 DuplicateDetectionError로 변환하는지 확인."""
        infra_error = DatabaseError("중복 검색 실패")
        domain_error = map_to_duplicate_detection_error(infra_error)
        
        assert isinstance(domain_error, DuplicateDetectionError)
        assert "중복 검색 실패" in str(domain_error)
        assert domain_error.__cause__ is infra_error
    
    def test_map_to_duplicate_detection_error_from_general_exception(self):
        """일반 예외를 DuplicateDetectionError로 변환하는지 확인."""
        general_error = RuntimeError("런타임 오류")
        domain_error = map_to_duplicate_detection_error(general_error)
        
        assert isinstance(domain_error, DuplicateDetectionError)
        assert "중복 탐지 실패" in str(domain_error)
        assert domain_error.__cause__ is general_error


class TestErrorChaining:
    """에러 체이닝이 정상 작동하는지 확인."""
    
    def test_cause_chain_preserved(self):
        """원본 에러가 __cause__로 연결되는지 확인."""
        original = FileSystemError("원본 오류")
        mapped = map_infra_error(original)
        
        assert mapped.__cause__ is original
        assert isinstance(mapped.__cause__, FileSystemError)
    
    def test_traceback_information_preserved(self):
        """에러 변환 시 트레이스백 정보가 유지되는지 확인."""
        try:
            try:
                raise FileSystemError("파일 시스템 오류")
            except FileSystemError as e:
                raise map_infra_error(e)
        except IntegrityCheckError as e:
            assert e.__cause__ is not None
            assert isinstance(e.__cause__, FileSystemError)
            assert "파일 시스템 오류" in str(e.__cause__)
