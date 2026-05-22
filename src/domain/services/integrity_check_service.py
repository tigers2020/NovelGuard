"""Pure integrity check rules (no I/O)."""

from domain.value_objects.integrity_issue import IntegrityIssue, IntegrityRuleId

_UTF8_ALIASES = frozenset({"utf-8", "utf8", "utf_8"})


def normalize_encoding(name: str | None) -> str | None:
    """Normalize encoding name for comparisons."""
    if not name:
        return None
    lowered = name.lower().replace("_", "-")
    if lowered in _UTF8_ALIASES or lowered.replace("-", "") == "utf8":
        return "utf-8"
    return lowered


class IntegrityCheckService:
    """Evaluate integrity rules from file metadata and encoding probe results."""

    @staticmethod
    def evaluate(
        *,
        size: int,
        encoding: str | None,
        confidence: float | None,
        decode_ok: bool,
        min_text_size: int,
        min_confidence: float,
    ) -> list[IntegrityIssue]:
        """Return issues ordered ERROR, then WARN, then INFO."""
        issues: list[IntegrityIssue] = []

        if size == 0:
            issues.append(
                IntegrityIssue(
                    rule_id=IntegrityRuleId.EMPTY_FILE,
                    message="빈 파일 (0바이트)",
                    severity="ERROR",
                )
            )
            return issues

        if size < min_text_size:
            issues.append(
                IntegrityIssue(
                    rule_id=IntegrityRuleId.SMALL_FILE,
                    message=f"작은 텍스트 파일 ({size}B)",
                    severity="WARN",
                )
            )

        normalized = normalize_encoding(encoding)
        conf = confidence if confidence is not None else 0.0

        if not normalized or conf < min_confidence:
            issues.append(
                IntegrityIssue(
                    rule_id=IntegrityRuleId.ENCODING_UNKNOWN,
                    message="인코딩 감지 불확실",
                    severity="WARN",
                )
            )
        elif normalized != "utf-8":
            issues.append(
                IntegrityIssue(
                    rule_id=IntegrityRuleId.ENCODING_NON_UTF8,
                    message=f"비 UTF-8 ({normalized})",
                    severity="INFO",
                )
            )

        if not decode_ok:
            issues.append(
                IntegrityIssue(
                    rule_id=IntegrityRuleId.DECODE_ERROR,
                    message="텍스트 디코드 실패",
                    severity="ERROR",
                )
            )

        severity_order = {"ERROR": 0, "WARN": 1, "INFO": 2}
        issues.sort(key=lambda i: severity_order.get(i.severity, 99))
        return issues
