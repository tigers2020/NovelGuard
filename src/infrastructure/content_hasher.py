"""Streaming file content hashing."""

from __future__ import annotations

import hashlib
from pathlib import Path

_CHUNK_SIZE = 64 * 1024


def hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(_CHUNK_SIZE):
            digest.update(chunk)
    return digest.hexdigest()
