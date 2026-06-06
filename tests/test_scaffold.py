"""Scaffold and app-level unit tests."""

from __future__ import annotations

import json
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
    assert runtime_paths.recovery_checkpoints_path(library_id).name == "recovery-checkpoints.jsonl"
    assert runtime_paths.undo_plans_dir(library_id).name == "undo-plans"
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
    assert paths.recovery_checkpoints_path == runtime_paths.recovery_checkpoints_path(
        paths.library_id
    )
    assert paths.undo_plans_dir == runtime_paths.undo_plans_dir(paths.library_id)
    assert "/state/libraries/" in paths.db_path.as_posix()
    assert session.audit_log_path() == paths.audit_log_path
    assert session.recovery_checkpoints_path() == paths.recovery_checkpoints_path


def test_session_factory_finalize_and_repair_under_library_save(tmp_path: Path) -> None:
    library = tmp_path / "lib"
    library.mkdir()
    session = create_library_session(MemoryLibraryIndex())
    paths = bind_library_runtime(session, str(library))

    assert session.finalize_save_root() == library / "SAVE" / "finalize"
    assert session.repair_backup_root() == library / "SAVE" / "repair_backup"
    assert paths.finalize_save_root == library / "SAVE" / "finalize"


def test_move_apply_recovery_manifest_shape(tmp_path: Path) -> None:
    from datetime import UTC, datetime

    from application.move_apply_recovery_run import MoveApplyRecoveryRun, classify_move_run_status
    from application.recovery_store import JsonlRecoveryStore
    from domain.apply_models import PreviewOperation
    store = JsonlRecoveryStore(
        checkpoints_path=tmp_path / "recovery-checkpoints.jsonl",
        undo_plans_dir=tmp_path / "undo-plans",
    )
    fixed = datetime(2026, 6, 6, 12, 0, 0, tzinfo=UTC)
    run = MoveApplyRecoveryRun(
        store,
        library_id="a" * 64,
        preview_token="preview-token",
        library_revision_at_start=1,
        now_fn=lambda: fixed,
    )
    op = PreviewOperation(
        row_id="file:g1:f1",
        action="move_duplicate",
        source_path="chapter.txt",
        dest_path="../duplicate/chapter.txt",
        source_file_id="f1",
        source_size=10,
        source_content_hash="abc",
        source_mtime_ns=100,
    )
    library = tmp_path / "lib"
    library.mkdir()
    dest = library / "SAVE" / "duplicate" / "chapter.txt"
    dest.parent.mkdir(parents=True)
    dest.write_text("hello", encoding="utf-8")
    run.record_applied(op, dest_path=dest, library_revision_after=2)
    manifest_path = run.seal(
        succeeded=1,
        failed_row_id=None,
        failed_error=None,
        library_revision_at_seal=2,
    )

    assert classify_move_run_status(succeeded=2, failed_row_id="row-3") == "partially_applied"
    assert manifest_path.exists()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["schemaVersion"] == 1
    assert manifest["runStatus"] == "completed"
    assert manifest["summary"]["appliedCount"] == 1
    assert len(manifest["items"]) == 1
    assert manifest["items"][0]["undoAction"] == "move_back"
    assert manifest["items"][0]["fromPath"] == "../duplicate/chapter.txt"
    assert manifest["items"][0]["toPath"] == "chapter.txt"
    assert manifest["createdAt"] == "2026-06-06T12:00:00Z"
    checkpoint_lines = (tmp_path / "recovery-checkpoints.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(checkpoint_lines) == 1
    checkpoint = json.loads(checkpoint_lines[0])
    assert checkpoint["operationType"] == "move_duplicate"
    assert checkpoint["rowId"] == "file:g1:f1"


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
