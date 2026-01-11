"""IntegrityIssue Entity 테스트."""

import pytest

from domain.entities.integrity_issue import IntegrityIssue


class TestIntegrityIssueCreation:
    """IntegrityIssue 생성 테스트."""
    
    def test_create_minimal(self):
        """최소 정보로 생성."""
        issue = IntegrityIssue(
            issue_id=1,
            file_id=10,
            severity="WARN",
            category="ENCODING",
            message="인코딩 문제 발견"
        )
        
        assert issue.issue_id == 1
        assert issue.file_id == 10
        assert issue.severity == "WARN"
        assert issue.category == "ENCODING"
        assert issue.message == "인코딩 문제 발견"
        assert issue.metrics == {}
        assert issue.fixable is False
        assert issue.suggested_fix is None
    
    def test_create_with_metrics(self):
        """메트릭과 함께 생성."""
        metrics = {"invalid_char_rate": 0.05, "null_count": 3}
        issue = IntegrityIssue(
            issue_id=1,
            file_id=10,
            severity="ERROR",
            category="NUL_BYTE",
            message="NULL 바이트 발견",
            metrics=metrics
        )
        
        assert issue.metrics == metrics
    
    def test_create_fixable(self):
        """수정 가능한 이슈 생성."""
        issue = IntegrityIssue(
            issue_id=1,
            file_id=10,
            severity="WARN",
            category="ENCODING",
            message="인코딩 변환 필요",
            fixable=True,
            suggested_fix="CONVERT_UTF8"
        )
        
        assert issue.fixable is True
        assert issue.suggested_fix == "CONVERT_UTF8"


class TestIntegrityIssueValidation:
    """IntegrityIssue 검증 테스트."""
    
    def test_invalid_severity(self):
        """잘못된 severity이면 실패."""
        with pytest.raises(ValueError, match="severity must be one of"):
            IntegrityIssue(
                issue_id=1,
                file_id=10,
                severity="CRITICAL",  # 잘못된 값
                category="ENCODING",
                message="..."
            )
    
    def test_invalid_category(self):
        """잘못된 category이면 실패."""
        with pytest.raises(ValueError, match="category must be one of"):
            IntegrityIssue(
                issue_id=1,
                file_id=10,
                severity="WARN",
                category="INVALID",  # 잘못된 값
                message="..."
            )


class TestIntegrityIssueEquality:
    """IntegrityIssue 동등성 테스트."""
    
    def test_equality_by_id(self):
        """ID가 같으면 같은 엔티티."""
        issue1 = IntegrityIssue(
            issue_id=1,
            file_id=10,
            severity="WARN",
            category="ENCODING",
            message="Issue 1"
        )
        issue2 = IntegrityIssue(
            issue_id=1,
            file_id=99,  # 다른 file_id
            severity="ERROR",  # 다른 severity
            category="NEWLINE",  # 다른 category
            message="Issue 2"  # 다른 message
        )
        
        # ID가 같으면 같은 엔티티
        assert issue1 == issue2
    
    def test_inequality_by_id(self):
        """ID가 다르면 다른 엔티티."""
        issue1 = IntegrityIssue(
            issue_id=1,
            file_id=10,
            severity="WARN",
            category="ENCODING",
            message="Issue 1"
        )
        issue2 = IntegrityIssue(
            issue_id=2,
            file_id=10,
            severity="WARN",
            category="ENCODING",
            message="Issue 1"
        )
        
        assert issue1 != issue2
    
    def test_hash_by_id(self):
        """ID 기반 해시."""
        issue1 = IntegrityIssue(
            issue_id=1,
            file_id=10,
            severity="WARN",
            category="ENCODING",
            message="Issue"
        )
        issue2 = IntegrityIssue(
            issue_id=1,
            file_id=99,
            severity="ERROR",
            category="NEWLINE",
            message="Other"
        )
        
        # ID가 같으면 해시도 같음
        assert hash(issue1) == hash(issue2)
    
    def test_set_membership(self):
        """Set에서 ID 기반 중복 제거."""
        issue1 = IntegrityIssue(
            issue_id=1,
            file_id=10,
            severity="WARN",
            category="ENCODING",
            message="Issue 1"
        )
        issue2 = IntegrityIssue(
            issue_id=1,
            file_id=10,
            severity="WARN",
            category="ENCODING",
            message="Issue 1"
        )
        issue3 = IntegrityIssue(
            issue_id=2,
            file_id=10,
            severity="WARN",
            category="ENCODING",
            message="Issue 2"
        )
        
        issues = {issue1, issue2, issue3}
        assert len(issues) == 2  # issue1과 issue2는 중복


class TestIntegrityIssueImmutability:
    """IntegrityIssue 불변성 테스트."""
    
    def test_frozen(self):
        """frozen=True로 속성 변경 불가."""
        issue = IntegrityIssue(
            issue_id=1,
            file_id=10,
            severity="WARN",
            category="ENCODING",
            message="..."
        )
        
        with pytest.raises(Exception):  # FrozenInstanceError
            issue.severity = "ERROR"  # type: ignore


class TestIntegrityIssueProperties:
    """IntegrityIssue 속성 테스트."""
    
    def test_is_info(self):
        """정보성 이슈 확인."""
        issue = IntegrityIssue(
            issue_id=1, file_id=10,
            severity="INFO",
            category="ENCODING",
            message="..."
        )
        
        assert issue.is_info is True
        assert issue.is_warning is False
        assert issue.is_error is False
    
    def test_is_warning(self):
        """경고 이슈 확인."""
        issue = IntegrityIssue(
            issue_id=1, file_id=10,
            severity="WARN",
            category="ENCODING",
            message="..."
        )
        
        assert issue.is_info is False
        assert issue.is_warning is True
        assert issue.is_error is False
    
    def test_is_error(self):
        """오류 이슈 확인."""
        issue = IntegrityIssue(
            issue_id=1, file_id=10,
            severity="ERROR",
            category="ENCODING",
            message="..."
        )
        
        assert issue.is_info is False
        assert issue.is_warning is False
        assert issue.is_error is True
    
    def test_is_encoding_issue(self):
        """인코딩 문제 확인."""
        issue = IntegrityIssue(
            issue_id=1, file_id=10,
            severity="WARN",
            category="ENCODING",
            message="..."
        )
        
        assert issue.is_encoding_issue is True
    
    def test_is_newline_issue(self):
        """줄바꿈 문제 확인."""
        issue = IntegrityIssue(
            issue_id=1, file_id=10,
            severity="WARN",
            category="NEWLINE",
            message="..."
        )
        
        assert issue.is_newline_issue is True
    
    def test_is_empty_issue(self):
        """빈 파일 문제 확인."""
        issue = IntegrityIssue(
            issue_id=1, file_id=10,
            severity="ERROR",
            category="EMPTY",
            message="..."
        )
        
        assert issue.is_empty_issue is True
    
    def test_is_broken_text_issue(self):
        """깨진 텍스트 문제 확인."""
        issue = IntegrityIssue(
            issue_id=1, file_id=10,
            severity="ERROR",
            category="BROKEN_TEXT",
            message="..."
        )
        
        assert issue.is_broken_text_issue is True
    
    def test_has_fix_true(self):
        """수정 제안 있음."""
        issue = IntegrityIssue(
            issue_id=1, file_id=10,
            severity="WARN",
            category="ENCODING",
            message="...",
            fixable=True,
            suggested_fix="CONVERT_UTF8"
        )
        
        assert issue.has_fix is True
    
    def test_has_fix_false(self):
        """수정 제안 없음."""
        issue = IntegrityIssue(
            issue_id=1, file_id=10,
            severity="ERROR",
            category="BROKEN_TEXT",
            message="..."
        )
        
        assert issue.has_fix is False


class TestIntegrityIssueMethods:
    """IntegrityIssue 메서드 테스트."""
    
    def test_get_metric_present(self):
        """메트릭 값 반환 (있음)."""
        issue = IntegrityIssue(
            issue_id=1, file_id=10,
            severity="WARN",
            category="ENCODING",
            message="...",
            metrics={"invalid_char_rate": 0.05, "null_count": 3}
        )
        
        assert issue.get_metric("invalid_char_rate") == 0.05
        assert issue.get_metric("null_count") == 3
    
    def test_get_metric_absent(self):
        """메트릭 값 반환 (없음, 기본값)."""
        issue = IntegrityIssue(
            issue_id=1, file_id=10,
            severity="WARN",
            category="ENCODING",
            message="..."
        )
        
        assert issue.get_metric("invalid_char_rate") is None
        assert issue.get_metric("invalid_char_rate", 0.0) == 0.0
    
    def test_has_metric_true(self):
        """메트릭 존재 확인 (있음)."""
        issue = IntegrityIssue(
            issue_id=1, file_id=10,
            severity="WARN",
            category="ENCODING",
            message="...",
            metrics={"invalid_char_rate": 0.05}
        )
        
        assert issue.has_metric("invalid_char_rate") is True
    
    def test_has_metric_false(self):
        """메트릭 존재 확인 (없음)."""
        issue = IntegrityIssue(
            issue_id=1, file_id=10,
            severity="WARN",
            category="ENCODING",
            message="..."
        )
        
        assert issue.has_metric("invalid_char_rate") is False
    
    def test_is_more_severe_than(self):
        """심각도 비교."""
        error_issue = IntegrityIssue(
            issue_id=1, file_id=10,
            severity="ERROR",
            category="ENCODING",
            message="..."
        )
        warn_issue = IntegrityIssue(
            issue_id=2, file_id=10,
            severity="WARN",
            category="NEWLINE",
            message="..."
        )
        info_issue = IntegrityIssue(
            issue_id=3, file_id=10,
            severity="INFO",
            category="ENCODING",
            message="..."
        )
        
        # ERROR > WARN
        assert error_issue.is_more_severe_than(warn_issue) is True
        assert warn_issue.is_more_severe_than(error_issue) is False
        
        # WARN > INFO
        assert warn_issue.is_more_severe_than(info_issue) is True
        assert info_issue.is_more_severe_than(warn_issue) is False
        
        # ERROR > INFO
        assert error_issue.is_more_severe_than(info_issue) is True
        
        # 같은 심각도
        another_error = IntegrityIssue(
            issue_id=4, file_id=10,
            severity="ERROR",
            category="EMPTY",
            message="..."
        )
        assert error_issue.is_more_severe_than(another_error) is False


class TestIntegrityIssueCategories:
    """IntegrityIssue 카테고리별 테스트."""
    
    def test_encoding_issue(self):
        """인코딩 문제."""
        issue = IntegrityIssue(
            issue_id=1, file_id=10,
            severity="ERROR",
            category="ENCODING",
            message="인코딩을 감지할 수 없습니다.",
            fixable=True,
            suggested_fix="CONVERT_UTF8"
        )
        
        assert issue.is_encoding_issue
        assert issue.is_error
        assert issue.fixable
    
    def test_newline_issue(self):
        """줄바꿈 문제."""
        issue = IntegrityIssue(
            issue_id=1, file_id=10,
            severity="WARN",
            category="NEWLINE",
            message="혼재된 줄바꿈 발견 (CRLF/LF).",
            fixable=True,
            suggested_fix="NORMALIZE_NEWLINE"
        )
        
        assert issue.is_newline_issue
        assert issue.is_warning
        assert issue.fixable
    
    def test_empty_issue(self):
        """빈 파일 문제."""
        issue = IntegrityIssue(
            issue_id=1, file_id=10,
            severity="INFO",
            category="EMPTY",
            message="빈 파일입니다.",
            fixable=False
        )
        
        assert issue.is_empty_issue
        assert issue.is_info
        assert not issue.fixable
    
    def test_nul_byte_issue(self):
        """NULL 바이트 문제."""
        issue = IntegrityIssue(
            issue_id=1, file_id=10,
            severity="ERROR",
            category="NUL_BYTE",
            message="NULL 바이트가 발견되었습니다.",
            metrics={"null_count": 5},
            fixable=False
        )
        
        assert issue.is_error
        assert issue.get_metric("null_count") == 5
