"""Review decision errors (mapped to bridge PreviewApplyError in app layer)."""

from __future__ import annotations


class ReviewDecisionError(Exception):
    def __init__(self, reason: str, message: str | None = None) -> None:
        self.reason = reason
        super().__init__(message or reason)
