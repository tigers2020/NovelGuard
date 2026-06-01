"""Composition root helpers for LibrarySession."""

from __future__ import annotations

from application.library_session import LibrarySession
from application.ports.library_index import LibraryIndexPort
from infrastructure.filesystem_scanner import scan_folder
from infrastructure.memory_library_index import MemoryLibraryIndex


def create_library_session(index: LibraryIndexPort | None = None) -> LibrarySession:
    return LibrarySession(index or MemoryLibraryIndex(), scan_folder=scan_folder)
