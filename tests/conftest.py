"""Shared pytest fixtures."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _allow_ephemeral_library_paths_for_tests(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NOVELGUARD_ALLOW_EPHEMERAL_LIBRARY", "1")
