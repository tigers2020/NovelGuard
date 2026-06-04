"""Shared Cursor CLI prompt helpers."""

from __future__ import annotations

DEFAULT_PROMPT_PREFIX = "/caveman"


def apply_prompt_prefix(prompt: str, prefix: str = DEFAULT_PROMPT_PREFIX) -> str:
    clean_prefix = (prefix or "").strip()
    body = prompt.strip()
    if not clean_prefix:
        return body + "\n"
    if body.startswith(clean_prefix):
        return body + "\n"
    return f"{clean_prefix}\n\n{body}\n"
