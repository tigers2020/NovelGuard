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
    checkpoint_lines = (
        (tmp_path / "recovery-checkpoints.jsonl").read_text(encoding="utf-8").splitlines()
    )
    assert len(checkpoint_lines) == 1
    checkpoint = json.loads(checkpoint_lines[0])
    assert checkpoint["operationType"] == "move_duplicate"
    assert checkpoint["rowId"] == "file:g1:f1"


def _move_undo_manifest_dict(
    *,
    operation_id: str = "op-1",
    from_path: str = "chapter.txt",
    to_path: str = "chapter.txt",
    after_hash: str | None = "abc",
    drift_policy: str = "strict",
    collision_policy: str = "block",
) -> dict:
    return {
        "schemaVersion": 1,
        "undoPlanId": "plan-1",
        "runId": "run-1",
        "libraryId": "a" * 64,
        "createdAt": "2026-06-06T12:00:00Z",
        "sealedAt": "2026-06-06T12:00:01Z",
        "status": "pending",
        "sourceBatchKind": "move_apply",
        "sourcePreviewToken": "token",
        "libraryRevisionAtSeal": 2,
        "runStatus": "completed",
        "summary": {"appliedCount": 1, "failedCount": 0},
        "idempotencyKey": "key",
        "failedRowId": None,
        "failedError": None,
        "items": [
            {
                "operationId": operation_id,
                "sequence": 1,
                "operationType": "move_duplicate",
                "undoAction": "move_back",
                "fromPath": from_path,
                "toPath": to_path,
                "backupPath": None,
                "recoverability": "recoverable",
                "manualRequired": False,
                "driftPolicy": drift_policy,
                "collisionPolicy": collision_policy,
                "checkpointRef": {"beforeHash": "before", "afterHash": after_hash},
            }
        ],
    }


def test_undo_dry_run_recovers_when_layout_matches(tmp_path: Path) -> None:
    from application.move_source_hash import content_hash_for_move
    from application.undo_dry_run_planner import plan_move_undo_dry_run
    from application.undo_manifest_loader import parse_and_validate_undo_manifest

    library = tmp_path / "lib"
    library.mkdir()
    dup_root = tmp_path / "duplicate" / "lib"
    dup_root.mkdir(parents=True)
    moved = dup_root / "chapter.txt"
    moved.write_text("hello", encoding="utf-8")
    after_hash = content_hash_for_move(moved, size_bytes=moved.stat().st_size)

    manifest = parse_and_validate_undo_manifest(_move_undo_manifest_dict(after_hash=after_hash))
    plan = plan_move_undo_dry_run(library_root=library, manifest=manifest)
    assert plan.recoverable_count == 1
    assert plan.blocked_count == 0
    assert plan.items[0].status == "recoverable"
    assert plan.items[0].reason is None


def test_undo_dry_run_blocks_when_current_file_missing(tmp_path: Path) -> None:
    from application.undo_dry_run_planner import plan_move_undo_dry_run
    from application.undo_manifest_loader import parse_and_validate_undo_manifest

    library = tmp_path / "lib"
    library.mkdir()
    manifest = parse_and_validate_undo_manifest(_move_undo_manifest_dict())
    plan = plan_move_undo_dry_run(library_root=library, manifest=manifest)
    assert plan.blocked_count == 1
    assert plan.items[0].reason == "dest_missing"


def test_undo_dry_run_blocks_when_source_occupied(tmp_path: Path) -> None:
    from application.move_source_hash import content_hash_for_move
    from application.undo_dry_run_planner import plan_move_undo_dry_run
    from application.undo_manifest_loader import parse_and_validate_undo_manifest

    library = tmp_path / "lib"
    library.mkdir()
    (library / "chapter.txt").write_text("occupied", encoding="utf-8")
    dup_root = tmp_path / "duplicate" / "lib"
    dup_root.mkdir(parents=True)
    moved = dup_root / "chapter.txt"
    moved.write_text("hello", encoding="utf-8")
    after_hash = content_hash_for_move(moved, size_bytes=moved.stat().st_size)

    manifest = parse_and_validate_undo_manifest(_move_undo_manifest_dict(after_hash=after_hash))
    plan = plan_move_undo_dry_run(library_root=library, manifest=manifest)
    assert plan.blocked_count == 1
    assert plan.items[0].reason == "source_occupied"


def test_undo_dry_run_blocks_on_metadata_drift_strict(tmp_path: Path) -> None:
    from application.undo_dry_run_planner import plan_move_undo_dry_run
    from application.undo_manifest_loader import parse_and_validate_undo_manifest

    library = tmp_path / "lib"
    library.mkdir()
    dup_root = tmp_path / "duplicate" / "lib"
    dup_root.mkdir(parents=True)
    (dup_root / "chapter.txt").write_text("changed", encoding="utf-8")

    manifest = parse_and_validate_undo_manifest(
        _move_undo_manifest_dict(after_hash="stale-hash", drift_policy="strict")
    )
    plan = plan_move_undo_dry_run(library_root=library, manifest=manifest)
    assert plan.blocked_count == 1
    assert plan.items[0].reason == "dest_changed"


def test_undo_dry_run_manual_required_on_metadata_drift(tmp_path: Path) -> None:
    from application.undo_dry_run_planner import plan_move_undo_dry_run
    from application.undo_manifest_loader import parse_and_validate_undo_manifest

    library = tmp_path / "lib"
    library.mkdir()
    dup_root = tmp_path / "duplicate" / "lib"
    dup_root.mkdir(parents=True)
    (dup_root / "chapter.txt").write_text("changed", encoding="utf-8")

    manifest = parse_and_validate_undo_manifest(
        _move_undo_manifest_dict(after_hash="stale-hash", drift_policy="manual")
    )
    plan = plan_move_undo_dry_run(library_root=library, manifest=manifest)
    assert plan.manual_required_count == 1
    assert plan.items[0].reason == "dest_changed"


def test_undo_manifest_loader_rejects_unsealed() -> None:
    from application.undo_manifest_errors import UndoManifestValidationError
    from application.undo_manifest_loader import parse_and_validate_undo_manifest

    payload = _move_undo_manifest_dict()
    payload["sealedAt"] = ""
    with pytest.raises(UndoManifestValidationError) as exc:
        parse_and_validate_undo_manifest(payload)
    assert exc.value.code == "MANIFEST_UNSEALED"


def test_undo_manifest_loader_rejects_duplicate_operation_ids() -> None:
    from application.undo_manifest_errors import UndoManifestValidationError
    from application.undo_manifest_loader import parse_and_validate_undo_manifest

    payload = _move_undo_manifest_dict()
    payload["items"].append(dict(payload["items"][0]))
    with pytest.raises(UndoManifestValidationError) as exc:
        parse_and_validate_undo_manifest(payload)
    assert exc.value.code == "DUPLICATE_OPERATION_ID"


def _undo_test_store(tmp_path: Path):
    from application.recovery_store import JsonlRecoveryStore

    return JsonlRecoveryStore(
        checkpoints_path=tmp_path / "recovery-checkpoints.jsonl",
        undo_plans_dir=tmp_path / "undo-plans",
    )


def _write_undo_manifest(store, payload: dict) -> None:
    store.write_undo_manifest(payload)


def _recoverable_layout(tmp_path: Path, *, content: str = "hello") -> tuple[Path, str]:
    from application.move_source_hash import content_hash_for_move

    library = tmp_path / "lib"
    library.mkdir()
    dup_root = tmp_path / "duplicate" / "lib"
    dup_root.mkdir(parents=True)
    moved = dup_root / "chapter.txt"
    moved.write_text(content, encoding="utf-8")
    after_hash = content_hash_for_move(moved, size_bytes=moved.stat().st_size)
    return library, after_hash


def test_undo_execute_full_success(tmp_path: Path) -> None:
    from application.undo_dry_run_planner import plan_move_undo_dry_run
    from application.undo_manifest_loader import parse_and_validate_undo_manifest
    from application.undo_move_executor import execute_move_undo_from_store

    library, after_hash = _recoverable_layout(tmp_path)
    payload = _move_undo_manifest_dict(after_hash=after_hash)
    store = _undo_test_store(tmp_path)
    _write_undo_manifest(store, payload)
    manifest = parse_and_validate_undo_manifest(payload)
    plan = plan_move_undo_dry_run(library_root=library, manifest=manifest)

    result = execute_move_undo_from_store(library_root=library, store=store, plan=plan)

    assert result.no_op is False
    assert result.manifest_status == "completed"
    assert result.recovered_count == 1
    assert result.failed_count == 0
    assert (library / "chapter.txt").read_text(encoding="utf-8") == "hello"
    assert not (tmp_path / "duplicate" / "lib" / "chapter.txt").exists()

    updated = json.loads(store.undo_manifest_path("plan-1").read_text(encoding="utf-8"))
    assert updated["status"] == "completed"
    assert updated["execution"]["recoveredCount"] == 1


def test_undo_execute_partial_failure(tmp_path: Path) -> None:
    from application.move_source_hash import content_hash_for_move
    from application.undo_dry_run_planner import plan_move_undo_dry_run
    from application.undo_manifest_loader import parse_and_validate_undo_manifest
    from application.undo_move_executor import execute_move_undo_from_store

    library = tmp_path / "lib"
    library.mkdir()
    dup_root = tmp_path / "duplicate" / "lib"
    dup_root.mkdir(parents=True)
    first = dup_root / "a.txt"
    second = dup_root / "b.txt"
    first.write_text("one", encoding="utf-8")
    second.write_text("two", encoding="utf-8")
    first_hash = content_hash_for_move(first, size_bytes=first.stat().st_size)
    second_hash = content_hash_for_move(second, size_bytes=second.stat().st_size)

    payload = _move_undo_manifest_dict(after_hash=first_hash)
    payload["items"] = [
        {
            "operationId": "op-1",
            "sequence": 1,
            "operationType": "move_duplicate",
            "undoAction": "move_back",
            "fromPath": "a.txt",
            "toPath": "a.txt",
            "backupPath": None,
            "recoverability": "recoverable",
            "manualRequired": False,
            "driftPolicy": "strict",
            "collisionPolicy": "block",
            "checkpointRef": {"beforeHash": "h1", "afterHash": first_hash},
        },
        {
            "operationId": "op-2",
            "sequence": 2,
            "operationType": "move_duplicate",
            "undoAction": "move_back",
            "fromPath": "b.txt",
            "toPath": "b.txt",
            "backupPath": None,
            "recoverability": "recoverable",
            "manualRequired": False,
            "driftPolicy": "strict",
            "collisionPolicy": "block",
            "checkpointRef": {"beforeHash": "h2", "afterHash": second_hash},
        },
    ]
    store = _undo_test_store(tmp_path)
    _write_undo_manifest(store, payload)
    manifest = parse_and_validate_undo_manifest(payload)
    plan = plan_move_undo_dry_run(library_root=library, manifest=manifest)
    assert plan.recoverable_count == 2
    second.unlink()

    result = execute_move_undo_from_store(library_root=library, store=store, plan=plan)

    assert result.manifest_status == "partial"
    assert result.recovered_count == 1
    assert result.failed_count == 1
    assert (library / "a.txt").exists()
    assert not (library / "b.txt").exists()
    updated = json.loads(store.undo_manifest_path("plan-1").read_text(encoding="utf-8"))
    assert updated["status"] == "partial"


def test_undo_execute_blocks_source_collision_at_recheck(tmp_path: Path) -> None:
    from application.undo_dry_run_planner import plan_move_undo_dry_run
    from application.undo_manifest_loader import parse_and_validate_undo_manifest
    from application.undo_move_executor import execute_move_undo_from_store

    library, after_hash = _recoverable_layout(tmp_path)
    payload = _move_undo_manifest_dict(after_hash=after_hash)
    store = _undo_test_store(tmp_path)
    _write_undo_manifest(store, payload)
    manifest = parse_and_validate_undo_manifest(payload)
    plan = plan_move_undo_dry_run(library_root=library, manifest=manifest)
    assert plan.recoverable_count == 1
    (library / "chapter.txt").write_text("occupied", encoding="utf-8")

    result = execute_move_undo_from_store(library_root=library, store=store, plan=plan)

    assert result.recovered_count == 0
    assert result.failed_count == 1
    assert result.items[0].status == "recovery_failed"
    assert result.items[0].reason == "source_occupied"
    assert (tmp_path / "duplicate" / "lib" / "chapter.txt").exists()


def test_undo_execute_blocks_missing_file_before_execution(tmp_path: Path) -> None:
    from application.undo_dry_run_planner import plan_move_undo_dry_run
    from application.undo_manifest_loader import parse_and_validate_undo_manifest
    from application.undo_move_executor import execute_move_undo_from_store

    library, after_hash = _recoverable_layout(tmp_path)
    (tmp_path / "duplicate" / "lib" / "chapter.txt").unlink()
    payload = _move_undo_manifest_dict(after_hash=after_hash)
    store = _undo_test_store(tmp_path)
    _write_undo_manifest(store, payload)
    manifest = parse_and_validate_undo_manifest(payload)
    plan = plan_move_undo_dry_run(library_root=library, manifest=manifest)
    assert plan.blocked_count == 1

    result = execute_move_undo_from_store(library_root=library, store=store, plan=plan)

    assert result.recovered_count == 0
    assert result.excluded_count == 1
    assert result.items[0].status == "excluded"
    assert result.items[0].reason == "dest_missing"


def test_undo_execute_repeat_is_idempotent(tmp_path: Path) -> None:
    from application.undo_dry_run_planner import plan_move_undo_dry_run
    from application.undo_manifest_loader import parse_and_validate_undo_manifest
    from application.undo_move_executor import execute_move_undo_from_store

    library, after_hash = _recoverable_layout(tmp_path)
    payload = _move_undo_manifest_dict(after_hash=after_hash)
    store = _undo_test_store(tmp_path)
    _write_undo_manifest(store, payload)
    manifest = parse_and_validate_undo_manifest(payload)
    plan = plan_move_undo_dry_run(library_root=library, manifest=manifest)

    first = execute_move_undo_from_store(library_root=library, store=store, plan=plan)
    second = execute_move_undo_from_store(library_root=library, store=store, plan=plan)

    assert first.recovered_count == 1
    assert second.no_op is True
    assert second.manifest_status == "completed"
    assert (library / "chapter.txt").read_text(encoding="utf-8") == "hello"


def test_undo_execute_skips_manual_required_items(tmp_path: Path) -> None:
    from application.undo_dry_run_planner import plan_move_undo_dry_run
    from application.undo_manifest_loader import parse_and_validate_undo_manifest
    from application.undo_move_executor import execute_move_undo_from_store

    library, after_hash = _recoverable_layout(tmp_path, content="changed")
    payload = _move_undo_manifest_dict(after_hash="stale-hash", drift_policy="manual")
    store = _undo_test_store(tmp_path)
    _write_undo_manifest(store, payload)
    manifest = parse_and_validate_undo_manifest(payload)
    plan = plan_move_undo_dry_run(library_root=library, manifest=manifest)
    assert plan.manual_required_count == 1

    result = execute_move_undo_from_store(library_root=library, store=store, plan=plan)

    assert result.recovered_count == 0
    assert result.excluded_count == 1
    assert result.items[0].status == "excluded"
    assert (tmp_path / "duplicate" / "lib" / "chapter.txt").exists()


def test_undo_dry_run_is_idempotent(tmp_path: Path) -> None:
    from application.move_source_hash import content_hash_for_move
    from application.undo_dry_run_planner import plan_move_undo_dry_run
    from application.undo_manifest_loader import parse_and_validate_undo_manifest

    library = tmp_path / "lib"
    library.mkdir()
    dup_root = tmp_path / "duplicate" / "lib"
    dup_root.mkdir(parents=True)
    moved = dup_root / "chapter.txt"
    moved.write_text("hello", encoding="utf-8")
    after_hash = content_hash_for_move(moved, size_bytes=moved.stat().st_size)
    manifest = parse_and_validate_undo_manifest(_move_undo_manifest_dict(after_hash=after_hash))
    first = plan_move_undo_dry_run(library_root=library, manifest=manifest)
    second = plan_move_undo_dry_run(library_root=library, manifest=manifest)
    assert first.to_dict() == second.to_dict()


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
