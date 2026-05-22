"""IndexPersistenceError mapping tests."""

import sqlite3
from pathlib import Path
from unittest.mock import patch

import pytest

from application.dto.scan_request import ScanRequest
from application.exceptions import IndexPersistenceError
from infrastructure.db.sqlite_index_repository import SQLiteIndexRepository


def test_start_run_wraps_sqlite_error(tmp_path: Path) -> None:
    repo = SQLiteIndexRepository(db_path=tmp_path / "index.db")
    request = ScanRequest(root_folder=tmp_path)

    with patch.object(repo, "_connect", side_effect=sqlite3.OperationalError("disk I/O error")):
        with pytest.raises(IndexPersistenceError) as exc_info:
            repo.start_run(request)

    assert exc_info.value.__cause__ is not None
