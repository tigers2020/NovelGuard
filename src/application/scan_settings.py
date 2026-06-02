"""Scan setting parsing (PR-28)."""

from __future__ import annotations


class SettingsValidationError(ValueError):
    """Invalid scan setting value."""


def parse_extension_filter(raw: str) -> set[str]:
    stripped = raw.strip()
    if not stripped:
        raise SettingsValidationError("extension filter must not be empty")

    extensions: set[str] = set()
    for part in stripped.split(","):
        token = part.strip().lower()
        if not token:
            continue
        if token.startswith("*."):
            raise SettingsValidationError("wildcard patterns are not supported")
        if token == ".":
            raise SettingsValidationError("invalid extension segment")
        if not token.startswith("."):
            raise SettingsValidationError("extensions must start with '.'")
        if len(token) < 2:
            raise SettingsValidationError("invalid extension segment")
        extensions.add(token)

    if not extensions:
        raise SettingsValidationError("extension filter must include at least one extension")
    return extensions


def build_scan_options_labels(
    *,
    extension_filter: str,
    include_hidden: bool,
) -> list[str]:
    labels = [extension_filter.replace(",", ", ").strip()]
    labels.append("하위 폴더 포함")
    labels.append("숨김 파일 포함" if include_hidden else "숨김 제외")
    return labels
