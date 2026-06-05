"""Shared pytest fixtures."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


@pytest.fixture(autouse=True)
def _allow_ephemeral_library_paths_for_tests(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NOVELGUARD_ALLOW_EPHEMERAL_LIBRARY", "1")
