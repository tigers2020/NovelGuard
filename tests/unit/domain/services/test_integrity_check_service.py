"""Tests for IntegrityCheckService."""

from application.constants import Constants
from domain.services.integrity_check_service import IntegrityCheckService
from domain.value_objects.integrity_issue import IntegrityRuleId


def test_empty_file_error() -> None:
    issues = IntegrityCheckService.evaluate(
        size=0,
        encoding=None,
        confidence=None,
        decode_ok=True,
        min_text_size=Constants.MIN_TEXT_FILE_SIZE,
        min_confidence=Constants.INTEGRITY_ENCODING_MIN_CONFIDENCE,
    )
    assert len(issues) == 1
    assert issues[0].rule_id == IntegrityRuleId.EMPTY_FILE
    assert issues[0].severity == "ERROR"


def test_small_file_warn() -> None:
    issues = IntegrityCheckService.evaluate(
        size=50,
        encoding="utf-8",
        confidence=0.99,
        decode_ok=True,
        min_text_size=Constants.MIN_TEXT_FILE_SIZE,
        min_confidence=Constants.INTEGRITY_ENCODING_MIN_CONFIDENCE,
    )
    assert any(i.rule_id == IntegrityRuleId.SMALL_FILE for i in issues)


def test_non_utf8_info() -> None:
    issues = IntegrityCheckService.evaluate(
        size=500,
        encoding="cp949",
        confidence=0.95,
        decode_ok=True,
        min_text_size=Constants.MIN_TEXT_FILE_SIZE,
        min_confidence=Constants.INTEGRITY_ENCODING_MIN_CONFIDENCE,
    )
    assert any(
        i.rule_id == IntegrityRuleId.ENCODING_NON_UTF8 and i.severity == "INFO" for i in issues
    )


def test_decode_error() -> None:
    issues = IntegrityCheckService.evaluate(
        size=500,
        encoding="utf-8",
        confidence=0.99,
        decode_ok=False,
        min_text_size=Constants.MIN_TEXT_FILE_SIZE,
        min_confidence=Constants.INTEGRITY_ENCODING_MIN_CONFIDENCE,
    )
    assert any(i.rule_id == IntegrityRuleId.DECODE_ERROR for i in issues)
