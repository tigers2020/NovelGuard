"""Scaffold and app-level unit tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from app import runtime_paths
from app.session_factory import bind_library_runtime, create_library_session
from infrastructure.memory_library_index import MemoryLibraryIndex
from infrastructure.sqlite_library_index import SqliteLibraryIndex


def test_scaffold_passes() -> None:
    assert True


def test_runtime_paths_dev_frontend_build_path() -> None:
    assert runtime_paths.frontend_asset_root().as_posix().endswith("/web/build")


def test_runtime_paths_env_overrides(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    local = tmp_path / "local"
    roaming = tmp_path / "roaming"

    monkeypatch.setenv("NOVELGUARD_LOCALAPPDATA", str(local))
    monkeypatch.setenv("NOVELGUARD_APPDATA", str(roaming))

    assert runtime_paths.logs_dir() == local / "NovelGuard" / "logs"
    assert runtime_paths.state_root() == local / "NovelGuard" / "state"
    assert runtime_paths.config_dir() == roaming / "NovelGuard"


def test_runtime_paths_library_id_is_stable(tmp_path: Path) -> None:
    root = tmp_path / "Library"
    root.mkdir()

    first = runtime_paths.library_id_for_root(root)
    second = runtime_paths.library_id_for_root(root)

    assert first == second
    assert len(first) == 64


def test_runtime_paths_per_library_state_paths(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("NOVELGUARD_LOCALAPPDATA", str(tmp_path / "local"))

    library_id = "a" * 64

    assert runtime_paths.library_db_path(library_id).name == "library.db"
    assert runtime_paths.apply_audit_path(library_id).name == "apply-audit.jsonl"
    assert "/state/libraries/" in runtime_paths.library_db_path(library_id).as_posix()


def test_runtime_paths_save_is_library_scoped(tmp_path: Path) -> None:
    library = tmp_path / "novels"
    library.mkdir()

    assert runtime_paths.save_dir_for_library(library) == library / "SAVE"
    assert runtime_paths.reports_dir_for_library(library) == library / "SAVE" / "reports"


def test_runtime_paths_invalid_library_id() -> None:
    with pytest.raises(ValueError, match="invalid library_id"):
        runtime_paths.library_state_dir("../escape")


def test_session_factory_binds_per_library_db_and_audit(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    local = tmp_path / "local"
    monkeypatch.setenv("NOVELGUARD_LOCALAPPDATA", str(local))

    library = tmp_path / "novels"
    library.mkdir()
    session = create_library_session(MemoryLibraryIndex())
    paths = bind_library_runtime(session, str(library))

    assert paths.db_path == runtime_paths.library_db_path(paths.library_id)
    assert paths.audit_log_path == runtime_paths.apply_audit_path(paths.library_id)
    assert "/state/libraries/" in paths.db_path.as_posix()
    assert session.audit_log_path() == paths.audit_log_path


def test_session_factory_finalize_and_repair_under_library_save(tmp_path: Path) -> None:
    library = tmp_path / "lib"
    library.mkdir()
    session = create_library_session(MemoryLibraryIndex())
    paths = bind_library_runtime(session, str(library))

    assert session.finalize_save_root() == library / "SAVE" / "finalize"
    assert session.repair_backup_root() == library / "SAVE" / "repair_backup"
    assert paths.finalize_save_root == library / "SAVE" / "finalize"


def test_sqlite_session_rebinds_db_on_select_folder(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    local = tmp_path / "local"
    monkeypatch.setenv("NOVELGUARD_LOCALAPPDATA", str(local))

    library = tmp_path / "collection"
    library.mkdir()
    session = create_library_session()
    session.select_folder(str(library))

    assert isinstance(session.index, SqliteLibraryIndex)
    library_id = runtime_paths.library_id_for_root(library)
    expected_db = runtime_paths.library_db_path(library_id)
    assert session.index._db_path == expected_db
