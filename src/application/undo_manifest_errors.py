"""Errors for undo manifest validation and dry-run planning."""

from __future__ import annotations


class UndoManifestValidationError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
