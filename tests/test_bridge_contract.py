from __future__ import annotations

import json
import logging
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any

import pytest

from app.bridge_api import BridgeApi
from app.bridge_contract import (
    ApplyFailedError,
    EmptySelectionError,
    FinalizeError,
    InvalidSelectionScopeError,
    PreviewApplyError,
    RepairApplyError,
    RepairPreviewError,
    SnapshotContractError,
    clamp_query_limit,
    validate_app_info,
    validate_app_snapshot,
    validate_duplicate_group_detail,
    validate_file_rows_page,
    validate_finalize_result,
    validate_finalize_summary,
    validate_move_preview,
    validate_quality_repair_preview,
    validate_quality_rows_page,
    validate_resolve_auto_approve_summary,
    validate_review_rows_page,
    validate_selection_scope,
)
from app.bridge_parity import PYWEBVIEW_API_METHODS
from app.selection_fingerprint import selection_fingerprint
from app.session_factory import create_bridge_api, create_library_session
from application.app_settings import AppSettings
from application.file_row_query import normalize_file_rows_query, text_sort_key
from application.library_folder_persistence import normalize_library_folder_path
from application.ports.filesystem_apply import ApplyRowResult
from application.quality_analyzer import analyze_quality
from application.scan_settings import SettingsValidationError, parse_extension_filter
from application.settings_store import SettingsStore
from domain.apply_models import PreviewOperation
from domain.apply_path_policy import build_move_duplicate_dest_relative, validate_move_operation
from domain.duplicate_exact import find_exact_duplicate_groups
from domain.models import FileRecord, make_file_id
from domain.quality import make_issue_id
from domain.settings_keys import SETTINGS_KEY_LIBRARY_LAST_FOLDER_PATH
from infrastructure import filesystem_scanner
from infrastructure.content_hasher import hash_file
from infrastructure.local_filesystem_apply import LocalFilesystemApplyAdapter
from infrastructure.memory_library_index import MemoryLibraryIndex
from infrastructure.sqlite_library_index import SqliteLibraryIndex
from tests.fixtures.bridge_contract_fixtures import VALID_SNAPSHOT


def _sibling_duplicate_root(library_root: Path) -> Path:
    return library_root.parent / "duplicate" / library_root.name


def _resolve_preview_dest(library_root: Path, dest_display: str) -> Path:
    norm = dest_display.replace("\\", "/")
    if norm.startswith("../"):
        return (library_root.parent / norm[3:]).resolve()
    return (library_root / norm).resolve()


def _memory_api() -> BridgeApi:
    return create_bridge_api(
        create_library_session(MemoryLibraryIndex(), settings=AppSettings()),
    )


@pytest.mark.parametrize(
    "forbidden_key",
    ["fileList", "reviewRows", "rows", "reviewRowsPage", "fileRows"],
)
def test_validate_app_snapshot_rejects_forbidden_arrays(forbidden_key: str) -> None:
    bad = {**VALID_SNAPSHOT, forbidden_key: [{"id": "x"}]}
    with pytest.raises(SnapshotContractError):
        validate_app_snapshot(bad)


def test_validate_app_snapshot_accepts_valid() -> None:
    validate_app_snapshot(VALID_SNAPSHOT)


def test_empty_explicit_rows_rejected() -> None:
    with pytest.raises(EmptySelectionError):
        validate_selection_scope({"type": "explicit_rows", "rowIds": []})


def test_current_query_requires_view_mode() -> None:
    with pytest.raises(InvalidSelectionScopeError):
        validate_selection_scope({"type": "current_query", "query": {}, "excludeRowIds": []})


def test_clamp_query_limit_max_200() -> None:
    assert clamp_query_limit({"viewMode": "action", "limit": 999}) == 200


def test_pywebview_api_methods_match_locked_contract() -> None:
    """Canonical list: app.bridge_parity.PYWEBVIEW_API_METHODS (mirrors bridgeParity.ts)."""
    assert len(PYWEBVIEW_API_METHODS) == 31
    assert PYWEBVIEW_API_METHODS[0] == "get_app_info"
    assert PYWEBVIEW_API_METHODS[-1] == "cancel_finalize"


def test_bridge_api_exposes_pywebview_methods() -> None:
    api = _memory_api()
    for name in PYWEBVIEW_API_METHODS:
        assert hasattr(api, name), f"BridgeApi missing {name}"
        assert callable(getattr(api, name))


def test_get_app_info_returns_required_keys() -> None:
    api = _memory_api()
    info = api.get_app_info()
    validate_app_info(info)
    assert info["appName"] == "NovelGuard"
    assert info["version"]
    assert info["buildType"] in ("dev", "production", "packaged")
    assert info["frontendBuild"] == "web/build"
    assert isinstance(info["pythonRuntime"], str)


def test_query_file_rows_empty_library_shape() -> None:
    api = _memory_api()
    page = api.query_file_rows({"cursor": None, "limit": 50})
    validate_file_rows_page(page)
    assert page["rows"] == []
    assert page["pageInfo"]["totalFiltered"] == 0
    assert page["pageInfo"]["hasMore"] is False


def test_normalize_file_rows_query_defaults() -> None:
    normalized = normalize_file_rows_query({"cursor": None})
    assert normalized.sort_field == "path"
    assert normalized.sort_direction == "asc"
    assert normalized.search_term is None
    assert normalized.cursor_offset == 0
    assert normalized.limit == 100


def test_normalize_file_rows_query_limit_clamped_to_500() -> None:
    normalized = normalize_file_rows_query({"limit": 999})
    assert normalized.limit == 500


def test_text_sort_key_case_and_unicode_parity() -> None:
    assert text_sort_key("File.TXT") == text_sort_key("file.txt")
    assert text_sort_key("토끼.txt") == text_sort_key("토끼.txt")
    assert text_sort_key("café") == text_sort_key("CAFÉ")
    assert text_sort_key(".Md") == text_sort_key(".md")


def test_normalize_file_rows_query_malformed_cursor_is_zero() -> None:
    normalized = normalize_file_rows_query({"cursor": "not-a-number", "limit": 10})
    assert normalized.cursor_offset == 0


def test_query_file_rows_invalid_sort_field_rejected() -> None:
    api = _memory_api()
    with pytest.raises(PreviewApplyError) as exc_info:
        api.query_file_rows({"sort": {"field": "notAllowed", "direction": "asc"}})
    assert exc_info.value.reason == "INVALID_SORT_FIELD"


def test_query_file_rows_invalid_filter_value_rejected() -> None:
    api = _memory_api()
    with pytest.raises(PreviewApplyError) as exc_info:
        api.query_file_rows({"filters": {"duplicateGroup": "maybe"}})
    assert exc_info.value.reason == "INVALID_FILTER_VALUE"


def test_bridge_api_get_snapshot_valid() -> None:
    api = _memory_api()
    snap = api.get_snapshot()
    validate_app_snapshot(snap)


def test_bridge_api_query_review_rows_valid() -> None:
    api = _memory_api()
    page = api.query_review_rows({"viewMode": "action", "limit": 50})
    assert len(page["rows"]) <= 200


def test_bridge_api_get_move_preview_requires_selection() -> None:
    api = _memory_api()
    preview = api.get_move_preview({"type": "explicit_rows", "rowIds": ["row-1"]})
    assert "rows" in preview
    assert preview["hasPendingApply"] is (preview["summary"]["operationCount"] > 0)
    assert "previewToken" in preview
    assert isinstance(preview["libraryRevision"], int)


def test_selection_fingerprint_explicit_rows_stable() -> None:
    sel = {"type": "explicit_rows", "rowIds": ["a", "b"]}
    fp = selection_fingerprint(sel)
    assert len(fp) == 64
    assert selection_fingerprint({"type": "explicit_rows", "rowIds": ["b", "a"]}) == fp
    # Golden vector shared with web/src/types/selection.test.ts (TS sha256)
    assert fp == "2d8872962e2b383329d55d654943dff923ff7278832153e5c5a8c5cca2497328"


def test_apply_missing_token_raises() -> None:
    api = _memory_api()
    with pytest.raises(PreviewApplyError) as exc:
        api.apply_resolved_actions(
            {"selection": {"type": "explicit_rows", "rowIds": ["row-1"]}, "previewToken": ""}
        )
    assert exc.value.reason == "MISSING_PREVIEW_TOKEN"


def test_apply_after_discard_raises_no_pending() -> None:
    api = _memory_api()
    sel = {"type": "explicit_rows", "rowIds": ["row-1"]}
    preview = api.get_move_preview(sel)
    api.discard_move_preview({"previewToken": preview["previewToken"]})
    with pytest.raises(PreviewApplyError) as exc:
        api.apply_resolved_actions({"selection": sel, "previewToken": preview["previewToken"]})
    assert exc.value.reason == "NO_PENDING_APPLY"


def test_discard_idempotent_on_mismatch() -> None:
    api = _memory_api()
    api.get_move_preview({"type": "explicit_rows", "rowIds": ["row-1"]})
    api.discard_move_preview({"previewToken": "unknown-token"})
    snap = api.get_snapshot()
    assert snap["work"]["resolve"]["hasPendingApply"] is False


def test_discard_quality_repair_preview_idempotent_on_mismatch(tmp_path: Path) -> None:
    (tmp_path / "korean.txt").write_bytes("안녕".encode("cp949"))
    session = create_library_session(MemoryLibraryIndex())
    session.select_folder(str(tmp_path))
    api = create_bridge_api(session)
    api.start_scan()
    _scan_until_idle(api)
    enc_row = _encoding_issue_row(api)
    preview = api.get_quality_repair_preview({"issueIds": [enc_row["id"]]})
    api.discard_quality_repair_preview({"repairPreviewToken": "unknown-token"})
    snap = api.get_snapshot()
    assert snap["work"]["quality"]["hasPendingQualityRepair"] is False
    api.discard_quality_repair_preview(
        {"repairPreviewToken": preview["repairPreviewToken"]},
    )
    snap = api.get_snapshot()
    assert snap["work"]["quality"]["hasPendingQualityRepair"] is False


def test_get_finalize_report_not_found(tmp_path: Path) -> None:
    session = create_library_session(MemoryLibraryIndex())
    session.select_folder(str(tmp_path))
    api = create_bridge_api(session)
    with pytest.raises(FinalizeError) as exc_info:
        api.get_finalize_report("missing-report-id")
    assert exc_info.value.reason == "REPORT_NOT_FOUND"


def test_set_app_setting_unknown_key_rejected() -> None:
    api = _memory_api()
    with pytest.raises(PreviewApplyError) as exc_info:
        api.set_app_setting("not.a.real.key", True)
    assert exc_info.value.reason == "INVALID_SETTING_VALUE"


def test_set_work_mode_updates_snapshot() -> None:
    api = _memory_api()
    api.set_work_mode("quality")
    snap = api.get_snapshot()
    assert snap["work"]["activeMode"] == "quality"


def test_set_work_mode_rejects_finalize_mode() -> None:
    api = _memory_api()
    with pytest.raises(PreviewApplyError) as exc_info:
        api.set_work_mode("finalize")
    assert exc_info.value.reason == "INVALID_WORK_MODE"
    assert api.get_snapshot()["work"]["activeMode"] == "resolve"


def test_make_file_id_stable() -> None:
    a = make_file_id("novels/a.txt", 100, 1_700_000_000_000_000_000)
    b = make_file_id("novels/a.txt", 100, 1_700_000_000_000_000_000)
    assert a == b
    assert len(a) == 64
    assert make_file_id("novels/b.txt", 100, 1_700_000_000_000_000_000) != a


def test_scan_hashes_same_stem_even_when_sizes_differ(tmp_path: Path) -> None:
    body = "shared novel body " * 80
    payload = body.encode("utf-8")
    (tmp_path / "series-v1.txt").write_bytes(payload)
    (tmp_path / "series-v2.txt").write_bytes(payload + b"\n")
    files: list[FileRecord] = []

    filesystem_scanner.scan_folder(
        str(tmp_path),
        on_progress=lambda _p, _l: None,
        cancel_check=lambda: False,
        out=files.append,
        use_content_probe=True,
    )
    by_name = {record.name: record for record in files}
    assert by_name["series-v1.txt"].size_bytes != by_name["series-v2.txt"].size_bytes
    assert by_name["series-v1.txt"].content_sha256 is not None
    assert by_name["series-v2.txt"].content_sha256 is not None


def test_scan_folder_finds_txt_and_md(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("hello", encoding="utf-8")
    (tmp_path / "b.md").write_text("# x", encoding="utf-8")
    (tmp_path / "skip.exe").write_bytes(b"\x00")
    files: list[FileRecord] = []

    filesystem_scanner.scan_folder(
        str(tmp_path),
        on_progress=lambda _p, _l: None,
        cancel_check=lambda: False,
        out=files.append,
    )
    names = {f.name for f in files}
    assert names == {"a.txt", "b.md"}
    assert all(f.content_sha256 is None for f in files)


def test_scan_folder_include_hidden_finds_dotfile(tmp_path: Path) -> None:
    (tmp_path / ".hidden.txt").write_text("secret", encoding="utf-8")
    (tmp_path / "visible.txt").write_text("ok", encoding="utf-8")
    files: list[FileRecord] = []

    filesystem_scanner.scan_folder(
        str(tmp_path),
        on_progress=lambda _p, _l: None,
        cancel_check=lambda: False,
        out=files.append,
        include_hidden=True,
    )
    assert {f.name for f in files} == {".hidden.txt", "visible.txt"}


def test_parse_extension_filter_rejects_invalid() -> None:
    with pytest.raises(SettingsValidationError):
        parse_extension_filter("")
    with pytest.raises(SettingsValidationError):
        parse_extension_filter("txt")
    with pytest.raises(SettingsValidationError):
        parse_extension_filter(".")
    with pytest.raises(SettingsValidationError):
        parse_extension_filter("*.txt")


def test_query_log_entries_contract_probe_and_warning_filter() -> None:
    api = _memory_api()
    logging.getLogger("application.contract_probe").info("contract probe")
    page = api.query_log_entries({"limit": 10})
    assert any("contract probe" in entry["message"] for entry in page["entries"])
    logging.getLogger("application.contract_probe").info("info level msg")
    logging.getLogger("application.contract_probe").warning("warn level msg")
    page_warn = api.query_log_entries({"level": "WARNING", "limit": 50})
    assert any(entry["message"] == "warn level msg" for entry in page_warn["entries"])
    assert not any(entry["message"] == "info level msg" for entry in page_warn["entries"])


def test_get_logs_artifacts_audit_tail_metadata(tmp_path: Path) -> None:
    session = create_library_session(MemoryLibraryIndex(), settings=AppSettings())
    session.select_folder(str(tmp_path))
    api = create_bridge_api(session)
    audit_path = session.audit_log_path()
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text('{"event":"test"}\n', encoding="utf-8")
    payload = api.get_logs_artifacts()
    kinds = {item["kind"] for item in payload["artifacts"]}
    assert "audit_tail" in kinds


def test_restore_last_library_folder_after_restart(tmp_path: Path) -> None:
    lib = tmp_path / "library"
    lib.mkdir()
    (lib / "chapter.txt").write_text("body", encoding="utf-8")
    settings = AppSettings(SettingsStore(tmp_path / "settings.json"))
    settings.set_value(
        SETTINGS_KEY_LIBRARY_LAST_FOLDER_PATH, normalize_library_folder_path(str(lib.resolve()))
    )

    session = create_library_session(settings=settings)
    api = create_bridge_api(session)
    api.start_scan()
    _scan_until_idle(api)
    assert api.get_snapshot()["library"]["fileCount"] == 1

    session2 = create_library_session(settings=settings)
    assert session2.index.folder_path == normalize_library_folder_path(str(lib.resolve()))
    assert len(session2.index.files()) == 1
    assert session2.scan_state() == "success"

    saved, source = settings.get_value(SETTINGS_KEY_LIBRARY_LAST_FOLDER_PATH)
    assert source == "persisted"
    assert saved == normalize_library_folder_path(str(lib.resolve()))


def test_select_folder_via_dialog_persists_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    lib = tmp_path / "novels"
    lib.mkdir()
    settings = AppSettings(SettingsStore(tmp_path / "settings.json"))
    session = create_library_session(MemoryLibraryIndex(), settings=settings)

    class _FakeTk:
        def withdraw(self) -> None:
            return None

        def destroy(self) -> None:
            return None

        def attributes(self, *_args: object, **_kwargs: object) -> None:
            return None

    monkeypatch.setattr("tkinter.Tk", _FakeTk)
    monkeypatch.setattr(
        "tkinter.filedialog.askdirectory",
        lambda **_kwargs: str(lib),
    )
    session.select_folder()

    saved, source = settings.get_value(SETTINGS_KEY_LIBRARY_LAST_FOLDER_PATH)
    assert source == "persisted"
    assert saved == normalize_library_folder_path(str(lib.resolve()))


def test_select_folder_explicit_path_does_not_overwrite_persisted(tmp_path: Path) -> None:
    lib = tmp_path / "saved"
    lib.mkdir()
    other = tmp_path / "other"
    other.mkdir()
    settings = AppSettings(SettingsStore(tmp_path / "settings.json"))
    settings.set_value(
        SETTINGS_KEY_LIBRARY_LAST_FOLDER_PATH, normalize_library_folder_path(str(lib.resolve()))
    )
    session = create_library_session(MemoryLibraryIndex(), settings=settings)
    session.select_folder(str(other))
    saved, _ = settings.get_value(SETTINGS_KEY_LIBRARY_LAST_FOLDER_PATH)
    assert saved == normalize_library_folder_path(str(lib.resolve()))


def test_restore_skips_ephemeral_persisted_folder(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("NOVELGUARD_ALLOW_EPHEMERAL_LIBRARY", raising=False)
    ephemeral = tmp_path / "pytest-of-user" / "test_run0"
    ephemeral.mkdir(parents=True)
    settings = AppSettings(SettingsStore(tmp_path / "settings.json"))
    settings.set_value(SETTINGS_KEY_LIBRARY_LAST_FOLDER_PATH, str(ephemeral.resolve()))
    session = create_library_session(MemoryLibraryIndex(), settings=settings)
    assert session.index.folder_path is None


def test_scan_include_hidden_setting(tmp_path: Path) -> None:
    (tmp_path / ".secret.txt").write_text("x", encoding="utf-8")
    session = create_library_session(MemoryLibraryIndex(), settings=AppSettings())
    session.select_folder(str(tmp_path))
    api = create_bridge_api(session)
    api.set_app_setting("scan.includeHidden", True)
    api.start_scan()
    _scan_until_idle(api)
    page = api.query_file_rows({"limit": 50})
    names = {row["name"] for row in page["rows"]}
    assert ".secret.txt" in names


def test_query_review_rows_empty_valid_14a() -> None:
    api = _memory_api()
    page = api.query_review_rows({"viewMode": "action", "limit": 50})
    assert page["rows"] == []
    validate_review_rows_page(page)


def test_bridge_api_scan_populates_file_count(tmp_path: Path) -> None:
    (tmp_path / "one.txt").write_text("a", encoding="utf-8")
    (tmp_path / "two.txt").write_text("b", encoding="utf-8")
    session = create_library_session(MemoryLibraryIndex())
    session.select_folder(str(tmp_path))
    api = create_bridge_api(session)
    rev_before = api.get_snapshot()["work"]["resolve"]["libraryRevision"]
    api.start_scan()
    deadline = time.monotonic() + 5.0
    snap = api.get_snapshot()
    while snap["work"]["scan"]["state"] == "running" and time.monotonic() < deadline:
        time.sleep(0.05)
        snap = api.get_snapshot()
    assert snap["work"]["scan"]["state"] == "success"
    assert snap["library"]["fileCount"] == 2
    assert snap["work"]["resolve"]["groupCount"] == 0
    rev_after = snap["work"]["resolve"]["libraryRevision"]
    assert rev_after > rev_before


def test_cancel_scan_discards_partial(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from infrastructure.filesystem_scanner import ScanStreamResult

    (tmp_path / "a.txt").write_text("x", encoding="utf-8")
    session = create_library_session(MemoryLibraryIndex(), settings=AppSettings())
    session.select_folder(str(tmp_path))
    api = create_bridge_api(session)
    api.start_scan()
    deadline = time.monotonic() + 5.0
    snap = api.get_snapshot()
    while snap["work"]["scan"]["state"] != "success" and time.monotonic() < deadline:
        time.sleep(0.05)
        snap = api.get_snapshot()
    assert snap["library"]["fileCount"] == 1
    rev_after_first = snap["work"]["resolve"]["libraryRevision"]

    (tmp_path / "b.txt").write_text("y", encoding="utf-8")
    (tmp_path / "c.txt").write_text("z", encoding="utf-8")

    cancel_flag = {"hit": False}

    def slow_scan(
        folder_path: str,
        *,
        on_progress,
        cancel_check,
        on_record,
        extensions=None,
        include_hidden=False,
        on_paths_collected=None,
        out=None,
    ) -> ScanStreamResult:
        _ = on_paths_collected
        sink = on_record if on_record is not None else out
        if sink is None:
            raise TypeError("on_record or out required")
        _ = include_hidden
        for i in range(50):
            if cancel_check():
                cancel_flag["hit"] = True
                return ScanStreamResult(completed=False, cancelled=True, scanned_count=i)
            rel = f"f{i}.txt"
            record = FileRecord(
                id=make_file_id(rel, 1, i),
                relative_path=rel,
                name=f"f{i}.txt",
                size_bytes=1,
                modified_at_ns=i,
                extension=".txt",
            )
            sink(record)
            on_progress(i * 2, "slow")
            time.sleep(0.02)
        return ScanStreamResult(completed=True, cancelled=False, scanned_count=50)

    def slow_scan_adapter(
        folder_path: str,
        *,
        on_progress,
        cancel_check,
        out,
        extensions=None,
        include_hidden=False,
        on_paths_collected=None,
    ) -> ScanStreamResult:
        return slow_scan(
            folder_path,
            on_progress=on_progress,
            cancel_check=cancel_check,
            on_record=out,
            extensions=extensions,
            include_hidden=include_hidden,
            on_paths_collected=on_paths_collected,
        )

    session._scan_folder = slow_scan_adapter  # noqa: SLF001
    api.start_scan()
    time.sleep(0.15)
    rev_before_cancel = api.get_snapshot()["work"]["resolve"]["libraryRevision"]
    api.cancel_run()
    deadline = time.monotonic() + 5.0
    snap = api.get_snapshot()
    while snap["work"]["scan"]["state"] == "running" and time.monotonic() < deadline:
        time.sleep(0.05)
        snap = api.get_snapshot()
    assert cancel_flag["hit"] is True
    assert snap["library"]["fileCount"] == 1
    assert snap["work"]["resolve"]["libraryRevision"] == rev_before_cancel == rev_after_first


def test_hash_file_hello_golden(tmp_path: Path) -> None:
    path = tmp_path / "hello.txt"
    path.write_text("hello", encoding="utf-8")
    assert hash_file(path) == "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"


def test_find_exact_duplicate_groups_keeper_by_size() -> None:
    content = "a" * 64
    keeper = FileRecord(
        id=make_file_id("z_keeper.txt", 50, 1),
        relative_path="z_keeper.txt",
        name="z_keeper.txt",
        size_bytes=50,
        modified_at_ns=1,
        extension=".txt",
        content_sha256=content,
    )
    other = FileRecord(
        id=make_file_id("a_other.txt", 50, 2),
        relative_path="a_other.txt",
        name="a_other.txt",
        size_bytes=50,
        modified_at_ns=2,
        extension=".txt",
        content_sha256=content,
    )
    groups = find_exact_duplicate_groups([keeper, other])
    assert len(groups) == 1
    assert groups[0].keeper_id == other.id


def test_sqlite_library_index_round_trip(tmp_path: Path) -> None:
    db = tmp_path / "library.db"
    index = SqliteLibraryIndex(db)
    folder = normalize_library_folder_path(str(tmp_path / "lib"))
    record = FileRecord(
        id=make_file_id("a.txt", 5, 1),
        relative_path="a.txt",
        name="a.txt",
        size_bytes=5,
        modified_at_ns=1,
        extension=".txt",
        content_sha256="abc",
    )
    index.replace_files(folder, [record])
    loaded = index.files()
    assert len(loaded) == 1
    assert loaded[0].content_sha256 == "abc"
    assert index.folder_path == folder


def test_sqlite_library_index_file_sort_keys_populated(tmp_path: Path) -> None:
    db = tmp_path / "library.db"
    index = SqliteLibraryIndex(db)
    folder = normalize_library_folder_path(str(tmp_path / "lib"))
    record = FileRecord(
        id=make_file_id("Café.txt", 5, 1),
        relative_path="sub/Café.txt",
        name="Café.txt",
        size_bytes=5,
        modified_at_ns=1,
        extension=".TXT",
        content_sha256="abc",
        encoding_status="UTF-8",
    )
    index.replace_files(folder, [record])
    with sqlite3.connect(db) as conn:
        row = conn.execute(
            """
            SELECT name_key, relative_path_key, extension_key, encoding_key
            FROM files WHERE folder_path = ? AND id = ?
            """,
            (folder, record.id),
        ).fetchone()
    assert row is not None
    assert row[0] == text_sort_key("Café.txt")
    assert row[1] == text_sort_key("sub/Café.txt")
    assert row[2] == text_sort_key(".TXT")
    assert row[3] == text_sort_key("UTF-8")
    assert row[0] != ""
    assert row[1] != ""


def test_sqlite_library_index_has_file_review_projection_table(tmp_path: Path) -> None:
    db = tmp_path / "library.db"
    SqliteLibraryIndex(db)
    with sqlite3.connect(db) as conn:
        found = conn.execute("""
            SELECT name FROM sqlite_master
            WHERE type = 'table' AND name = 'file_review_projection'
            """).fetchone()
    assert found is not None


def test_sqlite_query_file_rows_sort_and_search(tmp_path: Path) -> None:
    folder = tmp_path / "lib"
    folder.mkdir()
    (folder / "beta.txt").write_text("b", encoding="utf-8")
    (folder / "alpha.txt").write_text("a", encoding="utf-8")
    session = create_library_session(SqliteLibraryIndex(tmp_path / "lib.db"))
    session.select_folder(str(folder))
    api = create_bridge_api(session)
    api.start_scan()
    _scan_until_idle(api)

    by_path = api.query_file_rows({"sort": {"field": "path", "direction": "asc"}, "limit": 10})
    paths = [row["path"] for row in by_path["rows"]]
    assert paths == sorted(paths)

    by_name_desc = api.query_file_rows(
        {"sort": {"field": "name", "direction": "desc"}, "limit": 10}
    )
    names = [row["name"] for row in by_name_desc["rows"]]
    assert names == sorted(names, reverse=True)

    search = api.query_file_rows({"search": "alpha", "limit": 10})
    assert search["pageInfo"]["totalFiltered"] == 1
    assert search["rows"][0]["name"] == "alpha.txt"


def test_query_file_rows_cursor_pagination(tmp_path: Path) -> None:
    folder = tmp_path / "lib"
    folder.mkdir()
    for index in range(5):
        (folder / f"file_{index}.txt").write_bytes(b"x")
    session = create_library_session(SqliteLibraryIndex(tmp_path / "page.db"))
    session.select_folder(str(folder))
    api = create_bridge_api(session)
    api.start_scan()
    _scan_until_idle(api)

    first = api.query_file_rows({"limit": 2, "cursor": None})
    assert len(first["rows"]) == 2
    assert first["pageInfo"]["hasMore"] is True
    second = api.query_file_rows({"limit": 2, "cursor": first["pageInfo"]["nextCursor"]})
    assert len(second["rows"]) == 2
    assert first["rows"][0]["id"] != second["rows"][0]["id"]


def test_query_file_rows_filter_duplicate_group_none(tmp_path: Path) -> None:
    folder = tmp_path / "lib"
    folder.mkdir()
    (folder / "solo.txt").write_bytes(b"only")
    session = create_library_session(SqliteLibraryIndex(tmp_path / "filter.db"))
    session.select_folder(str(folder))
    api = create_bridge_api(session)
    api.start_scan()
    _scan_until_idle(api)

    page = api.query_file_rows({"filters": {"duplicateGroup": "none"}, "limit": 50})
    assert page["pageInfo"]["totalFiltered"] >= 1
    assert all(row.get("duplicateGroupId") is None for row in page["rows"])


def test_query_file_rows_exact_duplicate_enrichment(tmp_path: Path) -> None:
    payload = "duplicate story body\n"
    (tmp_path / "keeper.txt").write_text(payload, encoding="utf-8")
    (tmp_path / "copy.txt").write_text(payload, encoding="utf-8")
    session = create_library_session(SqliteLibraryIndex(tmp_path / "dup.db"))
    session.select_folder(str(tmp_path))
    api = create_bridge_api(session)
    api.start_scan()
    _scan_until_idle(api)

    page = api.query_file_rows({"limit": 50})
    assert page["pageInfo"]["totalFiltered"] == 2
    group_ids = {row.get("duplicateGroupId") for row in page["rows"]}
    assert len(group_ids) == 1
    assert None not in group_ids
    assert sum(1 for row in page["rows"] if row.get("isKeeper")) == 1


def test_sqlite_library_index_legacy_db_backfills_file_keys(tmp_path: Path) -> None:
    db = tmp_path / "legacy.db"
    folder = str(tmp_path / "lib")
    file_id = make_file_id("legacy.txt", 10, 1)
    with sqlite3.connect(db) as conn:
        conn.executescript("""
            CREATE TABLE files (
              id TEXT PRIMARY KEY,
              folder_path TEXT NOT NULL,
              relative_path TEXT NOT NULL,
              name TEXT NOT NULL,
              size_bytes INTEGER NOT NULL,
              modified_at_ns INTEGER NOT NULL,
              extension TEXT NOT NULL,
              content_sha256 TEXT,
              encoding_status TEXT
            );
            """)
        conn.execute(
            """
            INSERT INTO files (
              id, folder_path, relative_path, name, size_bytes, modified_at_ns,
              extension, content_sha256, encoding_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                file_id,
                folder,
                "legacy.txt",
                "legacy.txt",
                10,
                1,
                ".txt",
                None,
                "ascii",
            ),
        )
        conn.commit()

    SqliteLibraryIndex(db)
    with sqlite3.connect(db) as conn:
        row = conn.execute(
            "SELECT name_key, relative_path_key FROM files WHERE id = ?",
            (file_id,),
        ).fetchone()
    assert row is not None
    assert row[0] == text_sort_key("legacy.txt")
    assert row[1] == text_sort_key("legacy.txt")


def _scan_until_idle(api: BridgeApi) -> dict:
    deadline = time.monotonic() + 30.0
    snap = api.get_snapshot()
    while time.monotonic() < deadline:
        if snap["work"]["scan"]["state"] == "running":
            time.sleep(0.05)
            snap = api.get_snapshot()
            continue
        if snap["pipeline"]["phase"] != "idle":
            time.sleep(0.05)
            snap = api.get_snapshot()
            continue
        break
    return snap


def test_scan_does_not_persist_near_text_preview(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("hello world\n" * 100, encoding="utf-8")
    session = create_library_session(MemoryLibraryIndex())
    session.select_folder(str(tmp_path))
    api = create_bridge_api(session)
    api.start_scan()
    _scan_until_idle(api)
    for record in session.index.files():
        assert record.near_text_preview is None


def test_append_files_batch_increments_count_without_full_replace(tmp_path: Path) -> None:
    index = SqliteLibraryIndex(tmp_path / "lib.db")
    folder = str(tmp_path)
    index.activate_library_folder(folder)

    def _row(name: str) -> FileRecord:
        return FileRecord(
            id=make_file_id(name, 1, 1),
            relative_path=name,
            name=name,
            size_bytes=1,
            modified_at_ns=1,
            extension=".txt",
        )

    index.append_files_batch(folder, [_row("a.txt")], reset=True)
    assert index.file_count() == 1
    index.append_files_batch(folder, [_row("b.txt")], reset=False)
    assert index.file_count() == 2
    names = {f.name for f in index.files()}
    assert names == {"a.txt", "b.txt"}


def test_append_files_batch_reset_empty_clears_folder(tmp_path: Path) -> None:
    index = SqliteLibraryIndex(tmp_path / "lib.db")
    folder = str(tmp_path)
    index.activate_library_folder(folder)

    def _row(name: str) -> FileRecord:
        return FileRecord(
            id=make_file_id(name, 1, 1),
            relative_path=name,
            name=name,
            size_bytes=1,
            modified_at_ns=1,
            extension=".txt",
        )

    index.append_files_batch(folder, [_row("old.txt")], reset=True)
    assert index.file_count() == 1
    index.append_files_batch(folder, [], reset=True)
    assert index.file_count() == 0


def test_snapshot_includes_index_ready_and_deep_analysis_flags(tmp_path: Path) -> None:
    (tmp_path / "one.txt").write_text("x", encoding="utf-8")
    session = create_library_session(MemoryLibraryIndex())
    session.select_folder(str(tmp_path))
    api = create_bridge_api(session)
    snap = api.get_snapshot()
    assert snap["work"]["scan"]["indexReady"] is False
    assert snap["work"]["scan"]["deepAnalysisComplete"] is False
    api.start_scan()
    _scan_until_idle(api)
    snap = api.get_snapshot()
    assert snap["work"]["scan"]["indexReady"] is True
    assert snap["work"]["scan"]["deepAnalysisComplete"] is True


def _wait_deep_analysis_complete(api: BridgeApi, *, timeout: float = 120.0) -> dict:
    deadline = time.monotonic() + timeout
    snap = api.get_snapshot()
    while time.monotonic() < deadline:
        if snap["work"]["scan"]["deepAnalysisComplete"]:
            return snap
        time.sleep(0.05)
        snap = api.get_snapshot()
    return snap


def test_resolve_snapshot_split_counts_with_near_rows(tmp_path: Path) -> None:
    (tmp_path / "alpha.txt").write_text(_near_similar_body("alpha"), encoding="utf-8")
    (tmp_path / "beta.txt").write_text(_near_similar_body("beta"), encoding="utf-8")
    session = create_library_session(MemoryLibraryIndex())
    session.select_folder(str(tmp_path))
    api = create_bridge_api(session)
    api.start_scan()
    _wait_deep_analysis_complete(api)
    snap = api.get_snapshot()
    validate_app_snapshot(snap)
    resolve = snap["work"]["resolve"]
    assert resolve["moveReadyCount"] >= 0
    assert resolve["reviewSignalCount"] >= 0
    assert resolve["moveReadyCount"] + resolve["reviewSignalCount"] == resolve["queueCount"]
    if resolve["reviewSignalCount"] > 0:
        assert resolve["moveReadyCount"] < resolve["queueCount"]


def test_large_library_counts_near_duplicate_groups(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from application import scan_pipeline_constants

    monkeypatch.setattr(scan_pipeline_constants, "SCAN_DEEP_ANALYSIS_BACKGROUND_THRESHOLD", 2)
    (tmp_path / "alpha.txt").write_text(_near_similar_body("alpha"), encoding="utf-8")
    (tmp_path / "beta.txt").write_text(_near_similar_body("beta"), encoding="utf-8")
    session = create_library_session(MemoryLibraryIndex())
    session.select_folder(str(tmp_path))
    api = create_bridge_api(session)
    api.start_scan()
    _scan_until_idle(api)
    snap = _wait_deep_analysis_complete(api)
    assert snap["work"]["scan"]["deepAnalysisComplete"] is True
    assert snap["library"]["duplicateGroups"] >= 1
    assert snap["pipeline"]["phase"] == "idle"
    near_page = api.query_review_rows(
        {"viewMode": "groups", "limit": 50, "filters": {"types": ["near"]}}
    )
    validate_review_rows_page(near_page)
    assert any(row["type"] == "near" and row["rowKind"] == "group" for row in near_page["rows"])


def test_snapshot_rejects_legacy_scan_phase(tmp_path: Path) -> None:
    session = create_library_session(MemoryLibraryIndex())
    session.select_folder(str(tmp_path))
    api = create_bridge_api(session)
    snap = api.get_snapshot()
    snap["pipeline"]["phase"] = "scan"
    with pytest.raises(SnapshotContractError):
        validate_app_snapshot(snap)


def test_snapshot_rejects_unknown_pipeline_phase(tmp_path: Path) -> None:
    session = create_library_session(MemoryLibraryIndex())
    session.select_folder(str(tmp_path))
    api = create_bridge_api(session)
    snap = api.get_snapshot()
    snap["pipeline"]["phase"] = "bogus"
    with pytest.raises(SnapshotContractError):
        validate_app_snapshot(snap)


def test_scan_increments_file_count_after_first_persist_batch(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    import application.scan_pipeline_constants as scan_constants

    monkeypatch.setattr(scan_constants, "SCAN_PERSIST_BATCH_SIZE", 2)
    for i in range(5):
        (tmp_path / f"f{i}.txt").write_text("x\n", encoding="utf-8")

    session = create_library_session(SqliteLibraryIndex(tmp_path / "idx.db"))
    session.select_folder(str(tmp_path))
    index = session.index
    original_append = index.append_files_batch
    first_batch_done = threading.Event()
    release_after_first = threading.Event()

    def wrapping_append(folder_path: str, files: list, *, reset: bool = False) -> None:
        original_append(folder_path, files, reset=reset)
        if not first_batch_done.is_set():
            first_batch_done.set()
            release_after_first.wait(timeout=5.0)  # hold after first commit, before probe continues

    monkeypatch.setattr(index, "append_files_batch", wrapping_append)
    api = create_bridge_api(session)
    api.start_scan()

    assert first_batch_done.wait(timeout=5.0), "first persist batch never committed"
    snap = api.get_snapshot()
    assert 0 < snap["library"]["fileCount"] < 5
    release_after_first.set()
    _scan_until_idle(api)
    assert api.get_snapshot()["library"]["fileCount"] == 5


def test_index_ready_before_scan_success(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    import application.library_session as library_session_module
    import application.scan_pipeline_constants as scan_constants
    from domain.duplicate_exact import find_exact_duplicate_groups as real_find_groups

    monkeypatch.setattr(scan_constants, "SCAN_PERSIST_BATCH_SIZE", 1)
    (tmp_path / "a.txt").write_text("a\n", encoding="utf-8")
    (tmp_path / "b.txt").write_text("b\n", encoding="utf-8")

    exact_index_reached = threading.Event()
    release_exact_index = threading.Event()

    def gated_exact_groups(files: list[FileRecord]) -> list:
        exact_index_reached.set()
        release_exact_index.wait(timeout=5.0)
        return real_find_groups(files)

    monkeypatch.setattr(
        library_session_module,
        "find_exact_duplicate_groups",
        gated_exact_groups,
    )

    session = create_library_session(MemoryLibraryIndex())
    session.select_folder(str(tmp_path))
    api = create_bridge_api(session)
    api.start_scan()

    assert exact_index_reached.wait(timeout=5.0), "exact_index phase not reached"
    snap = api.get_snapshot()
    assert snap["work"]["scan"]["indexReady"] is True
    assert snap["work"]["scan"]["state"] == "running"

    release_exact_index.set()
    _scan_until_idle(api)
    snap = api.get_snapshot()
    assert snap["work"]["scan"]["state"] == "success"


def test_scan_emits_probe_not_legacy_scan_phase(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("x", encoding="utf-8")
    session = create_library_session(MemoryLibraryIndex())
    session.select_folder(str(tmp_path))
    api = create_bridge_api(session)
    api.start_scan()
    deadline = time.monotonic() + 10.0
    phases: set[str] = set()
    while time.monotonic() < deadline:
        snap = api.get_snapshot()
        phases.add(snap["pipeline"]["phase"])
        if snap["work"]["scan"]["state"] == "success":
            break
        time.sleep(0.02)
    _scan_until_idle(api)
    assert "scan" not in phases
    assert "probe" in phases or "persist" in phases


def test_scan_observes_scan_persist_phase(tmp_path: Path) -> None:
    for i in range(4):
        (tmp_path / f"f{i}.txt").write_text("x\n", encoding="utf-8")
    session = create_library_session(MemoryLibraryIndex())
    session.select_folder(str(tmp_path))
    api = create_bridge_api(session)
    index = session.index
    original_append = index.append_files_batch
    release_tail_persist = threading.Event()

    def hold_tail_persist(folder_path: str, files: list, *, reset: bool = False) -> None:
        with session._lock:
            in_tail = session._pipeline_phase == "scan_persist"
        if in_tail and files:
            release_tail_persist.wait(timeout=2.0)
        original_append(folder_path, files, reset=reset)

    index.append_files_batch = hold_tail_persist  # type: ignore[method-assign]
    try:
        api.start_scan()
        deadline = time.monotonic() + 10.0
        saw_scan_persist = False
        while time.monotonic() < deadline:
            snap = api.get_snapshot()
            if snap["pipeline"]["phase"] == "scan_persist":
                saw_scan_persist = True
                assert "인덱스 저장" in snap["pipeline"]["label"]
                release_tail_persist.set()
                break
            time.sleep(0.005)
        _scan_until_idle(api)
        assert saw_scan_persist
    finally:
        release_tail_persist.set()
        index.append_files_batch = original_append  # type: ignore[method-assign]


def test_update_review_decisions_approve_persists(tmp_path: Path) -> None:
    payload = "same story content\n"
    (tmp_path / "copy_a.txt").write_text(payload, encoding="utf-8")
    (tmp_path / "copy_b.txt").write_text(payload, encoding="utf-8")
    session = create_library_session(MemoryLibraryIndex())
    session.select_folder(str(tmp_path))
    api = create_bridge_api(session)
    api.start_scan()
    _scan_until_idle(api)
    page = api.query_review_rows({"viewMode": "all", "limit": 50})
    file_rows = [row for row in page["rows"] if row.get("rowKind") == "file"]
    file_row = next(row for row in file_rows if row.get("status") == "unreviewed")
    assert file_row.get("status") == "unreviewed"

    result = api.update_review_decisions(
        {
            "selection": {"type": "explicit_rows", "rowIds": [file_row["id"]]},
            "command": "approve",
        }
    )
    assert result["updatedCount"] == 1
    assert result["libraryRevision"] >= 1

    snap = api.get_snapshot()
    assert snap["work"]["resolve"]["approvedCount"] >= 1

    page_after = api.query_review_rows({"viewMode": "all", "limit": 50})
    approved_row = next(row for row in page_after["rows"] if row["id"] == file_row["id"])
    assert approved_row["status"] == "approved"


def test_query_review_rows_exact_duplicate_pair(tmp_path: Path) -> None:
    payload = "same story content\n"
    (tmp_path / "copy_a.txt").write_text(payload, encoding="utf-8")
    (tmp_path / "copy_b.txt").write_text(payload, encoding="utf-8")
    session = create_library_session(MemoryLibraryIndex())
    session.select_folder(str(tmp_path))
    api = create_bridge_api(session)
    api.start_scan()
    snap = _scan_until_idle(api)
    assert snap["work"]["scan"]["state"] == "success"
    assert snap["work"]["scan"]["exactAutoApprovedCount"] >= 1
    assert snap["work"]["resolve"]["approvedCount"] >= 1
    page = api.query_review_rows({"viewMode": "all", "limit": 50})
    validate_review_rows_page(page)
    assert len(page["rows"]) >= 3
    assert all(row["type"] == "exact" for row in page["rows"])
    assert any(row["rowKind"] == "group" for row in page["rows"])

    file_rows = [row for row in page["rows"] if row.get("rowKind") == "file"]
    assert len(file_rows) == 2
    keeper_row = max(file_rows, key=lambda row: row["name"])
    non_keeper_row = min(file_rows, key=lambda row: row["name"])
    assert keeper_row["status"] == "unreviewed"
    assert keeper_row["proposedAction"] == "keep"
    assert non_keeper_row["status"] == "approved"
    assert non_keeper_row["proposedAction"] == "move_duplicate"


def test_scan_exact_auto_approved_count_zero_without_duplicates(tmp_path: Path) -> None:
    (tmp_path / "solo.txt").write_text("unique story\n", encoding="utf-8")
    session = create_library_session(MemoryLibraryIndex())
    session.select_folder(str(tmp_path))
    api = create_bridge_api(session)
    api.start_scan()
    snap = _scan_until_idle(api)
    assert snap["work"]["scan"]["state"] == "success"
    assert snap["work"]["scan"]["exactAutoApprovedCount"] == 0


def test_scan_exact_auto_approved_count_resets_on_rescan(tmp_path: Path) -> None:
    payload = "same story content\n"
    (tmp_path / "copy_a.txt").write_text(payload, encoding="utf-8")
    (tmp_path / "copy_b.txt").write_text(payload, encoding="utf-8")
    session = create_library_session(MemoryLibraryIndex())
    session.select_folder(str(tmp_path))
    api = create_bridge_api(session)
    api.start_scan()
    first = _scan_until_idle(api)
    assert first["work"]["scan"]["exactAutoApprovedCount"] >= 1
    api.start_scan()
    second = _scan_until_idle(api)
    assert second["work"]["scan"]["state"] == "success"
    assert second["work"]["scan"]["exactAutoApprovedCount"] == 0


def test_snapshot_duplicate_group_count(tmp_path: Path) -> None:
    text = "duplicate me"
    (tmp_path / "one.txt").write_text(text, encoding="utf-8")
    (tmp_path / "two.txt").write_text(text, encoding="utf-8")
    session = create_library_session(MemoryLibraryIndex())
    session.select_folder(str(tmp_path))
    api = create_bridge_api(session)
    api.start_scan()
    snap = _scan_until_idle(api)
    assert snap["work"]["resolve"]["groupCount"] >= 1
    assert snap["library"]["duplicateGroups"] >= 1


def test_query_review_rows_near_filter_empty(tmp_path: Path) -> None:
    text = "duplicate me"
    (tmp_path / "one.txt").write_text(text, encoding="utf-8")
    (tmp_path / "two.txt").write_text(text, encoding="utf-8")
    session = create_library_session(MemoryLibraryIndex())
    session.select_folder(str(tmp_path))
    api = create_bridge_api(session)
    api.start_scan()
    _scan_until_idle(api)
    page = api.query_review_rows({"viewMode": "all", "limit": 50, "filters": {"types": ["near"]}})
    assert page["rows"] == []
    validate_review_rows_page(page)


def test_query_review_rows_near_filter_returns_near_groups(tmp_path: Path) -> None:
    (tmp_path / "alpha.txt").write_text(_near_similar_body("alpha"), encoding="utf-8")
    (tmp_path / "beta.txt").write_text(_near_similar_body("beta"), encoding="utf-8")
    session = create_library_session(MemoryLibraryIndex())
    session.select_folder(str(tmp_path))
    api = create_bridge_api(session)
    api.start_scan()
    _wait_deep_analysis_complete(api)
    page = api.query_review_rows(
        {"viewMode": "groups", "limit": 50, "filters": {"types": ["near"]}}
    )
    validate_review_rows_page(page)
    assert any(row["type"] == "near" and row["rowKind"] == "group" for row in page["rows"])


def test_analyze_quality_empty_file(tmp_path: Path) -> None:
    folder = tmp_path / "lib"
    folder.mkdir()
    empty = folder / "empty.txt"
    empty.write_bytes(b"")
    record = FileRecord(
        id=make_file_id("empty.txt", 0, 1),
        relative_path="empty.txt",
        name="empty.txt",
        size_bytes=0,
        modified_at_ns=1,
        extension=".txt",
    )
    issues = analyze_quality(str(folder), [record])
    assert len(issues) == 1
    assert issues[0].kind == "empty_file"
    assert issues[0].issue_id == make_issue_id(record.id, "empty_file")


def test_analyze_quality_tiny_file(tmp_path: Path) -> None:
    folder = tmp_path / "lib"
    folder.mkdir()
    tiny = folder / "tiny.txt"
    tiny.write_bytes(b"x")
    record = FileRecord(
        id=make_file_id("tiny.txt", 1, 1),
        relative_path="tiny.txt",
        name="tiny.txt",
        size_bytes=1,
        modified_at_ns=1,
        extension=".txt",
    )
    issues = analyze_quality(str(folder), [record])
    assert len(issues) == 1
    assert issues[0].kind == "tiny_file"


def test_analyze_quality_invalid_utf8(tmp_path: Path) -> None:
    folder = tmp_path / "lib"
    folder.mkdir()
    bad = folder / "bad.txt"
    bad.write_bytes(b"\xff\xfe")
    record = FileRecord(
        id=make_file_id("bad.txt", 2, 1),
        relative_path="bad.txt",
        name="bad.txt",
        size_bytes=2,
        modified_at_ns=1,
        extension=".txt",
    )
    issues = analyze_quality(str(folder), [record])
    assert len(issues) == 1
    assert issues[0].kind == "invalid_utf8"


def test_analyze_quality_uses_scan_cache_for_invalid_utf8_without_disk_read() -> None:
    record = FileRecord(
        id=make_file_id("bad.txt", 2, 1),
        relative_path="bad.txt",
        name="bad.txt",
        size_bytes=2,
        modified_at_ns=1,
        extension=".txt",
        encoding_status="invalid_utf8",
    )

    def fail_read(_path: Path) -> bytes:
        raise AssertionError("disk read should not run when scan cache has invalid_utf8")

    issues = analyze_quality("/missing/lib", [record], read_bytes=fail_read)
    assert len(issues) == 1
    assert issues[0].kind == "invalid_utf8"


def test_analyze_quality_read_error(tmp_path: Path) -> None:
    folder = tmp_path / "lib"
    folder.mkdir()
    record = FileRecord(
        id=make_file_id("missing.txt", 10, 1),
        relative_path="missing.txt",
        name="missing.txt",
        size_bytes=10,
        modified_at_ns=1,
        extension=".txt",
    )

    def fail_read(_path: Path) -> bytes:
        raise OSError("simulated read failure")

    issues = analyze_quality(str(folder), [record], read_bytes=fail_read)
    assert len(issues) == 1
    assert issues[0].kind == "read_error"


def test_query_quality_rows_detects_issues(tmp_path: Path) -> None:
    (tmp_path / "empty.txt").write_bytes(b"")
    (tmp_path / "tiny.txt").write_bytes(b"x")
    (tmp_path / "bad.txt").write_bytes(b"\xff\xfe")
    session = create_library_session(MemoryLibraryIndex())
    session.select_folder(str(tmp_path))
    api = create_bridge_api(session)
    api.start_scan()
    snap = _scan_until_idle(api)
    assert snap["work"]["scan"]["state"] == "success"
    assert snap["fileListSummary"]["issueCount"] == 3

    small_page = api.query_quality_rows({"issueType": "small_file", "limit": 50})
    validate_quality_rows_page(small_page)
    assert len(small_page["rows"]) == 2
    assert small_page["pageInfo"]["totalFiltered"] == 2
    assert small_page["summary"]["issueCount"] == 2
    assert all(row["id"].startswith("quality:") for row in small_page["rows"])

    encoding_page = api.query_quality_rows({"issueType": "encoding", "limit": 50})
    assert len(encoding_page["rows"]) == 1
    assert encoding_page["pageInfo"]["totalFiltered"] == 1
    assert encoding_page["summary"]["errorCount"] >= 1
    assert encoding_page["rows"][0]["issueType"] == "encoding"


def test_query_quality_rows_limit_capped_at_200(tmp_path: Path) -> None:
    for i in range(250):
        (tmp_path / f"empty_{i}.txt").write_bytes(b"")
    session = create_library_session(MemoryLibraryIndex())
    session.select_folder(str(tmp_path))
    api = create_bridge_api(session)
    api.start_scan()
    _scan_until_idle(api)
    page = api.query_quality_rows({"issueType": "small_file", "limit": 999})
    validate_quality_rows_page(page)
    assert len(page["rows"]) <= 200


def test_get_quality_issue_detail_from_cache(tmp_path: Path) -> None:
    target_name = "empty_issue_fixture.txt"
    (tmp_path / target_name).write_bytes(b"")
    session = create_library_session(MemoryLibraryIndex())
    session.select_folder(str(tmp_path))
    api = create_bridge_api(session)
    api.start_scan()
    _scan_until_idle(api)
    page = api.query_quality_rows({"issueType": "small_file", "limit": 10})
    row = next((r for r in page["rows"] if r["name"] == target_name), None)
    assert (
        row is not None
    ), f"expected small_file row for {target_name}, got {[r['name'] for r in page['rows']]}"
    detail = api.get_quality_issue_detail(row["id"])
    assert detail["status"] == "ok"
    inner = detail["detail"]
    assert inner["id"] == row["id"]
    assert inner["name"] == target_name
    assert isinstance(inner["libraryRevision"], int)
    assert inner["evidence"]["kind"] == "empty_file"
    assert detail.get("status") != "stale"


def test_get_quality_issue_detail_not_found_normalized_id(tmp_path: Path) -> None:
    session = create_library_session(MemoryLibraryIndex())
    session.select_folder(str(tmp_path))
    api = create_bridge_api(session)
    detail = api.get_quality_issue_detail("deadbeef")
    assert detail["status"] == "not_found"
    assert detail["message"] == "quality_issue_not_found"
    assert detail["id"] == "quality:deadbeef"


def test_get_quality_issue_detail_malformed_id_not_found(tmp_path: Path) -> None:
    session = create_library_session(MemoryLibraryIndex())
    session.select_folder(str(tmp_path))
    api = create_bridge_api(session)
    for bad_id in ("", "   ", "quality:quality:deadbeef"):
        detail = api.get_quality_issue_detail(bad_id)
        assert detail["status"] == "not_found"
        assert detail["message"] == "quality_issue_not_found"


def test_get_quality_issue_detail_invalid_utf8_evidence(tmp_path: Path) -> None:
    (tmp_path / "bad.txt").write_bytes(b"\xff\xfe")
    session = create_library_session(MemoryLibraryIndex())
    session.select_folder(str(tmp_path))
    api = create_bridge_api(session)
    api.start_scan()
    _scan_until_idle(api)
    page = api.query_quality_rows({"issueType": "encoding", "limit": 10})
    assert len(page["rows"]) >= 1
    row = page["rows"][0]
    detail = api.get_quality_issue_detail(row["id"])
    assert detail["status"] == "ok"
    inner = detail["detail"]
    assert inner["evidence"]["kind"] == "invalid_utf8"
    assert inner["repairEligibility"]["futureAction"] == "utf8_convert"
    assert inner["repairEligibility"]["eligible"] is True
    assert inner["repairEligibility"]["reason"] == "ready"


def test_get_quality_issue_detail_id_without_prefix(tmp_path: Path) -> None:
    (tmp_path / "empty.txt").write_bytes(b"")
    session = create_library_session(MemoryLibraryIndex())
    session.select_folder(str(tmp_path))
    api = create_bridge_api(session)
    api.start_scan()
    _scan_until_idle(api)
    page = api.query_quality_rows({"issueType": "small_file", "limit": 1})
    row = page["rows"][0]
    domain_id = row["id"].removeprefix("quality:")
    detail = api.get_quality_issue_detail(domain_id)
    assert detail["status"] == "ok"
    assert detail["detail"]["id"] == row["id"]


def test_query_quality_rows_sort_name_asc(tmp_path: Path) -> None:
    import unicodedata

    (tmp_path / "가.txt").write_bytes(b"x")
    (tmp_path / "나.txt").write_bytes(b"x")
    (tmp_path / "a.txt").write_bytes(b"x")
    session = create_library_session(MemoryLibraryIndex())
    session.select_folder(str(tmp_path))
    api = create_bridge_api(session)
    api.start_scan()
    _scan_until_idle(api)
    page = api.query_quality_rows(
        {"issueType": "small_file", "limit": 50, "sort": {"field": "name", "direction": "asc"}},
    )
    names = [row["name"] for row in page["rows"]]
    assert names == sorted(
        names,
        key=lambda value: unicodedata.normalize("NFC", value).casefold(),
    )


def test_query_quality_rows_invalid_sort_field_rejected(tmp_path: Path) -> None:
    (tmp_path / "empty.txt").write_bytes(b"")
    session = create_library_session(MemoryLibraryIndex())
    session.select_folder(str(tmp_path))
    api = create_bridge_api(session)
    api.start_scan()
    _scan_until_idle(api)
    with pytest.raises(PreviewApplyError) as exc_info:
        api.query_quality_rows(
            {
                "issueType": "small_file",
                "sort": {"field": "notAllowed", "direction": "asc"},
            },
        )
    assert exc_info.value.reason == "INVALID_SORT_FIELD"


def test_query_quality_rows_stable_sort_order(tmp_path: Path) -> None:
    for i in range(4):
        (tmp_path / f"empty_{i}.txt").write_bytes(b"")
    session = create_library_session(MemoryLibraryIndex())
    session.select_folder(str(tmp_path))
    api = create_bridge_api(session)
    api.start_scan()
    _scan_until_idle(api)
    query = {
        "issueType": "small_file",
        "limit": 50,
        "sort": {"field": "severity", "direction": "desc"},
    }
    first = api.query_quality_rows(query)
    second = api.query_quality_rows(query)
    assert [row["id"] for row in first["rows"]] == [row["id"] for row in second["rows"]]


def test_query_quality_rows_severity_desc_errors_first(tmp_path: Path) -> None:
    (tmp_path / "empty.txt").write_bytes(b"")
    (tmp_path / "bad.txt").write_bytes(b"\xff\xfe")
    session = create_library_session(MemoryLibraryIndex())
    session.select_folder(str(tmp_path))
    api = create_bridge_api(session)
    api.start_scan()
    _scan_until_idle(api)
    page = api.query_quality_rows(
        {
            "issueType": "encoding",
            "limit": 50,
            "sort": {"field": "severity", "direction": "desc"},
        },
    )
    encoding_rows = [row for row in page["rows"] if row["issueType"] == "encoding"]
    if len(encoding_rows) >= 2:
        severities = [row["severity"] for row in encoding_rows]
        assert severities.index("error") < severities.index("warning")


def test_query_quality_rows_unknown_issue_type_empty(tmp_path: Path) -> None:
    (tmp_path / "empty.txt").write_bytes(b"")
    session = create_library_session(MemoryLibraryIndex())
    session.select_folder(str(tmp_path))
    api = create_bridge_api(session)
    api.start_scan()
    _scan_until_idle(api)
    page = api.query_quality_rows({"issueType": "near", "limit": 50})
    assert page["rows"] == []
    validate_quality_rows_page(page)


def test_snapshot_quality_counts(tmp_path: Path) -> None:
    (tmp_path / "empty.txt").write_bytes(b"")
    (tmp_path / "bad.txt").write_bytes(b"\xff\xfe")
    session = create_library_session(MemoryLibraryIndex())
    session.select_folder(str(tmp_path))
    api = create_bridge_api(session)
    api.start_scan()
    snap = _scan_until_idle(api)
    assert snap["work"]["quality"]["smallFileAnomalyCount"] == 1
    assert snap["work"]["quality"]["encodingIssueCount"] == 1
    assert snap["fileListSummary"]["issueCount"] == 2


def test_sqlite_quality_issues_folder_scoped(tmp_path: Path) -> None:
    db = tmp_path / "library.db"
    index = SqliteLibraryIndex(db)
    folder_a = normalize_library_folder_path(str(tmp_path / "a"))
    folder_b = normalize_library_folder_path(str(tmp_path / "b"))
    record = FileRecord(
        id=make_file_id("only.txt", 0, 1),
        relative_path="only.txt",
        name="only.txt",
        size_bytes=0,
        modified_at_ns=1,
        extension=".txt",
    )
    issues_a = analyze_quality(folder_a, [record])
    index.replace_files(folder_a, [record])
    index.replace_quality_issues(folder_a, issues_a)
    assert len(index.quality_issues()) == 1

    index.replace_files(folder_b, [])
    index.replace_quality_issues(folder_b, [])
    assert index.quality_issues() == []


def _move_op(
    *,
    source: str = "a/keep.txt",
    dest: str = "a/keep.txt",
) -> PreviewOperation:
    return PreviewOperation(
        row_id="file:g1:f1",
        action="move_duplicate",
        source_path=source,
        dest_path=dest,
        source_file_id="f1",
        source_size=10,
        source_content_hash="abc",
    )


def test_apply_path_policy_blocks_path_traversal(tmp_path: Path) -> None:
    root = tmp_path / "lib"
    root.mkdir()
    result = validate_move_operation(
        root,
        _move_op(source="../outside.txt", dest="outside.txt"),
        destination_exists=False,
    )
    assert not result.allowed
    assert result.reason == "path_traversal"


def test_apply_path_policy_blocks_absolute_dest(tmp_path: Path) -> None:
    root = tmp_path / "lib"
    root.mkdir()
    (root / "src.txt").write_text("x", encoding="utf-8")
    result = validate_move_operation(
        root,
        _move_op(source="src.txt", dest="/absolute/dup.txt"),
        destination_exists=False,
    )
    assert not result.allowed
    assert result.reason in ("absolute_path", "path_traversal", "invalid_target")


def test_apply_path_policy_blocks_destination_exists(tmp_path: Path) -> None:
    root = tmp_path / "lib"
    root.mkdir()
    ext_dup = tmp_path / "duplicate" / "lib"
    ext_dup.mkdir(parents=True)
    (ext_dup / "dup.txt").write_text("exists", encoding="utf-8")
    (root / "src.txt").write_text("src", encoding="utf-8")
    result = validate_move_operation(
        root,
        _move_op(source="src.txt", dest="dup.txt"),
        destination_exists=True,
    )
    assert not result.allowed
    assert result.reason == "destination_exists"


def test_apply_path_policy_allows_valid_move(tmp_path: Path) -> None:
    root = tmp_path / "lib"
    root.mkdir()
    (root / "src.txt").write_text("src", encoding="utf-8")
    dest_rel = build_move_duplicate_dest_relative("duplicate", "src.txt")
    result = validate_move_operation(
        root,
        _move_op(source="src.txt", dest=dest_rel),
        destination_exists=False,
    )
    assert result.allowed
    assert result.reason is None


def test_filesystem_apply_moves_file(tmp_path: Path) -> None:
    root = tmp_path / "lib"
    root.mkdir()
    src = root / "src.txt"
    src.write_text("payload", encoding="utf-8")
    dest = tmp_path / "duplicate" / "lib" / "src.txt"
    adapter = LocalFilesystemApplyAdapter()
    assert adapter.move_file(src, dest).outcome == "ok"
    assert dest.read_text(encoding="utf-8") == "payload"
    assert not src.exists()


def test_filesystem_apply_move_rejects_existing_destination(tmp_path: Path) -> None:
    root = tmp_path / "lib"
    (root / "duplicate").mkdir(parents=True)
    (root / "duplicate" / "taken.txt").write_text("taken", encoding="utf-8")
    src = root / "src.txt"
    src.write_text("src", encoding="utf-8")
    dest = root / "duplicate" / "taken.txt"
    adapter = LocalFilesystemApplyAdapter()
    result = adapter.move_file(src, dest)
    assert result.outcome == "error"
    assert result.error is not None
    assert "destination exists" in result.error
    assert src.exists()
    assert dest.read_text(encoding="utf-8") == "taken"


def test_filesystem_apply_ensure_parent_dir(tmp_path: Path) -> None:
    root = tmp_path / "lib"
    root.mkdir()
    dest = root / "nested" / "dir" / "file.txt"
    adapter = LocalFilesystemApplyAdapter()
    assert adapter.ensure_parent_dir(dest).outcome == "ok"
    assert (root / "nested" / "dir").is_dir()


def _duplicate_api(tmp_path: Path, audit_path: Path | None = None) -> BridgeApi:
    payload = "same story content\n"
    (tmp_path / "copy_a.txt").write_text(payload, encoding="utf-8")
    (tmp_path / "copy_b.txt").write_text(payload, encoding="utf-8")
    session = create_library_session(MemoryLibraryIndex())
    session.select_folder(str(tmp_path))
    api = create_bridge_api(session, audit_log_path=audit_path)
    api.start_scan()
    _scan_until_idle(api)
    return api


def _quad_duplicate_api(
    tmp_path: Path,
    *,
    audit_path: Path | None = None,
    filesystem: LocalFilesystemApplyAdapter | None = None,
) -> BridgeApi:
    payload = "same story content\n"
    for index in range(4):
        (tmp_path / f"copy_{index}.txt").write_text(payload, encoding="utf-8")
    session = create_library_session(MemoryLibraryIndex())
    session.select_folder(str(tmp_path))
    kwargs: dict = {"audit_log_path": audit_path}
    if filesystem is not None:
        kwargs["filesystem"] = filesystem
    api = create_bridge_api(session, **kwargs)
    api.start_scan()
    _scan_until_idle(api)
    return api


class _FailOnNthMoveAdapter(LocalFilesystemApplyAdapter):
    def __init__(self, fail_on: int) -> None:
        self._fail_on = fail_on
        self._move_calls = 0

    def move_file(self, src: Path, dest: Path) -> ApplyRowResult:
        self._move_calls += 1
        if self._move_calls >= self._fail_on:
            return ApplyRowResult(outcome="error", error="injected failure")
        return super().move_file(src, dest)


def test_real_move_preview_lists_duplicate_member(tmp_path: Path) -> None:
    api = _duplicate_api(tmp_path)
    page = api.query_review_rows({"viewMode": "all", "limit": 50})
    move_row = next(row for row in page["rows"] if row.get("proposedAction") == "move_duplicate")
    preview = api.get_move_preview({"type": "explicit_rows", "rowIds": [move_row["id"]]})
    validate_move_preview(preview)
    assert preview["summary"]["operationCount"] >= 1
    assert preview["rows"][0]["id"].startswith("file:")
    assert preview["rows"][0]["action"] == "move_duplicate"


def test_current_query_move_preview_includes_auto_approved_duplicate(tmp_path: Path) -> None:
    api = _duplicate_api(tmp_path)
    page = api.query_review_rows({"viewMode": "all", "limit": 50})
    file_rows = [row for row in page["rows"] if row.get("rowKind") == "file"]
    move_row = next(row for row in file_rows if row.get("proposedAction") == "move_duplicate")
    keeper_row = next(row for row in file_rows if row.get("proposedAction") == "keep")
    assert move_row["status"] == "approved"

    action_page = api.query_review_rows({"viewMode": "action", "limit": 50})
    action_file_ids = {row["id"] for row in action_page["rows"] if row.get("rowKind") == "file"}
    assert move_row["id"] in action_file_ids

    selection = {
        "type": "current_query",
        "query": {"viewMode": "action", "limit": 50},
        "excludeRowIds": [],
    }
    preview = api.get_move_preview(selection)
    validate_move_preview(preview)
    assert preview["summary"]["operationCount"] >= 1
    preview_ids = {row["id"] for row in preview["rows"]}
    assert move_row["id"] in preview_ids
    assert keeper_row["id"] not in preview_ids


def test_real_apply_moves_duplicate_file(
    tmp_path: Path, tmp_path_factory: pytest.TempPathFactory
) -> None:
    audit_file = tmp_path_factory.mktemp("audit") / "apply-audit.jsonl"
    api = _duplicate_api(tmp_path, audit_path=audit_file)
    page = api.query_review_rows({"viewMode": "all", "limit": 50})
    move_row = next(row for row in page["rows"] if row.get("proposedAction") == "move_duplicate")
    sel = {"type": "explicit_rows", "rowIds": [move_row["id"]]}
    preview = api.get_move_preview(sel)
    api.apply_resolved_actions({"selection": sel, "previewToken": preview["previewToken"]})
    src_name = move_row["name"]
    assert not (tmp_path / src_name).exists()
    assert (_sibling_duplicate_root(tmp_path) / src_name).exists()
    snap = api.get_snapshot()
    assert snap["work"]["resolve"]["hasPendingApply"] is False


def test_apply_succeeds_for_approved_near_after_preview(
    tmp_path: Path, tmp_path_factory: pytest.TempPathFactory
) -> None:
    (tmp_path / "alpha.txt").write_text(_near_similar_body("alpha"), encoding="utf-8")
    (tmp_path / "beta.txt").write_text(_near_similar_body("beta"), encoding="utf-8")
    audit_file = tmp_path_factory.mktemp("audit") / "near-apply-audit.jsonl"
    session = create_library_session(MemoryLibraryIndex())
    session.select_folder(str(tmp_path))
    api = create_bridge_api(session, audit_log_path=audit_file)
    api.start_scan()
    _scan_until_idle(api)
    near_page = api.query_review_rows(
        {"viewMode": "all", "limit": 50, "filters": {"types": ["near"]}}
    )
    file_rows = [row for row in near_page["rows"] if row["rowKind"] == "file"]
    if len(file_rows) < 2:
        pytest.skip("near duplicate group not detected in fixture")
    summary = api.summarize_auto_select_keepers(
        {"viewMode": "all", "limit": 50, "filters": {"types": ["near"]}}
    )
    if summary["keeperRowIds"]:
        api.update_review_decisions(
            {
                "selection": {"type": "explicit_rows", "rowIds": summary["keeperRowIds"]},
                "command": "setKeeper",
            }
        )
    api.update_review_decisions(
        {
            "selection": {
                "type": "current_query",
                "query": {
                    "viewMode": "all",
                    "limit": 50,
                    "filters": {"types": ["near"], "status": ["unreviewed"]},
                },
                "excludeRowIds": [],
            },
            "command": "approve",
        }
    )
    refreshed = api.query_review_rows(
        {"viewMode": "all", "limit": 50, "filters": {"types": ["near"]}}
    )
    move_row = next(
        (
            row
            for row in refreshed["rows"]
            if row.get("rowKind") == "file" and row.get("proposedAction") == "move_duplicate"
        ),
        None,
    )
    if move_row is None:
        pytest.skip("no near move_duplicate rows after approve")
    sel = {"type": "explicit_rows", "rowIds": [move_row["id"]]}
    preview = api.get_move_preview(sel)
    validate_move_preview(preview)
    assert preview["summary"]["operationCount"] >= 1
    api.apply_resolved_actions({"selection": sel, "previewToken": preview["previewToken"]})
    src_name = move_row["name"]
    assert not (tmp_path / src_name).exists()
    assert (_sibling_duplicate_root(tmp_path) / src_name).exists()
    snap = api.get_snapshot()
    assert snap["work"]["resolve"]["hasPendingApply"] is False


def test_apply_stale_after_file_change(tmp_path: Path) -> None:
    api = _duplicate_api(tmp_path)
    page = api.query_review_rows({"viewMode": "all", "limit": 50})
    move_row = next(row for row in page["rows"] if row.get("proposedAction") == "move_duplicate")
    sel = {"type": "explicit_rows", "rowIds": [move_row["id"]]}
    preview = api.get_move_preview(sel)
    path = tmp_path / move_row["path"]
    path.write_text(path.read_text(encoding="utf-8") + "changed\n", encoding="utf-8")
    with pytest.raises(PreviewApplyError) as exc:
        api.apply_resolved_actions({"selection": sel, "previewToken": preview["previewToken"]})
    assert exc.value.reason == "STALE_PREVIEW"
    snap = api.get_snapshot()
    assert snap["work"]["resolve"]["hasPendingApply"] is False


def test_bridge_stale_revision_clears_pending(tmp_path: Path) -> None:
    api = _duplicate_api(tmp_path)
    page = api.query_review_rows({"viewMode": "all", "limit": 50})
    move_row = next(row for row in page["rows"] if row.get("proposedAction") == "move_duplicate")
    sel = {"type": "explicit_rows", "rowIds": [move_row["id"]]}
    preview = api.get_move_preview(sel)
    api._session.increment_library_revision()
    with pytest.raises(PreviewApplyError) as exc:
        api.apply_resolved_actions({"selection": sel, "previewToken": preview["previewToken"]})
    assert exc.value.reason == "STALE_PREVIEW"
    assert api.get_snapshot()["work"]["resolve"]["hasPendingApply"] is False


def test_move_preview_targets_sibling_duplicate_folder(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("dup\n", encoding="utf-8")
    (tmp_path / "b.txt").write_text("dup\n", encoding="utf-8")
    session = create_library_session(MemoryLibraryIndex())
    session.select_folder(str(tmp_path))
    api = create_bridge_api(session)
    api.start_scan()
    _scan_until_idle(api)
    page = api.query_review_rows({"viewMode": "all", "limit": 50})
    move_row = next(row for row in page["rows"] if row.get("proposedAction") == "move_duplicate")
    preview = api.get_move_preview({"type": "explicit_rows", "rowIds": [move_row["id"]]})
    validate_move_preview(preview)
    assert preview["summary"]["operationCount"] == 1
    row = preview["rows"][0]
    assert row["destPath"].startswith("../duplicate/")
    assert not row["destPath"].startswith("duplicate/")


def test_apply_reuse_token_raises_no_pending(tmp_path: Path) -> None:
    api = _duplicate_api(tmp_path)
    page = api.query_review_rows({"viewMode": "all", "limit": 50})
    move_row = next(row for row in page["rows"] if row.get("proposedAction") == "move_duplicate")
    sel = {"type": "explicit_rows", "rowIds": [move_row["id"]]}
    preview = api.get_move_preview(sel)
    api.apply_resolved_actions({"selection": sel, "previewToken": preview["previewToken"]})
    with pytest.raises(PreviewApplyError) as exc:
        api.apply_resolved_actions({"selection": sel, "previewToken": preview["previewToken"]})
    assert exc.value.reason == "NO_PENDING_APPLY"


def test_select_folder_during_apply_raises_library_busy(tmp_path: Path) -> None:
    api = _duplicate_api(tmp_path)
    api._session.set_apply_in_progress(True)
    with pytest.raises(PreviewApplyError) as exc:
        api.select_folder()
    assert exc.value.reason == "LIBRARY_BUSY"


def test_start_scan_during_apply_raises_library_busy(tmp_path: Path) -> None:
    api = _duplicate_api(tmp_path)
    api._session.set_apply_in_progress(True)
    with pytest.raises(PreviewApplyError) as exc:
        api.start_scan()
    assert exc.value.reason == "LIBRARY_BUSY"


def test_partial_apply_batch_records_audit_and_raises(
    tmp_path: Path, tmp_path_factory: pytest.TempPathFactory
) -> None:
    audit_file = tmp_path_factory.mktemp("audit") / "apply-audit.jsonl"
    fs = _FailOnNthMoveAdapter(fail_on=3)
    api = _quad_duplicate_api(tmp_path, audit_path=audit_file, filesystem=fs)
    page = api.query_review_rows({"viewMode": "all", "limit": 50})
    move_rows = [row for row in page["rows"] if row.get("proposedAction") == "move_duplicate"]
    assert len(move_rows) >= 3
    sel = {"type": "explicit_rows", "rowIds": [row["id"] for row in move_rows[:3]]}
    preview = api.get_move_preview(sel)
    assert preview["summary"]["operationCount"] == 3

    with pytest.raises(ApplyFailedError) as exc:
        api.apply_resolved_actions({"selection": sel, "previewToken": preview["previewToken"]})
    assert exc.value.reason == "APPLY_FAILED"
    assert exc.value.details.get("partialSuccess") is True
    assert exc.value.details.get("succeededCount") == 2

    batch = move_rows[:3]
    moved = [
        row["name"] for row in batch if (_sibling_duplicate_root(tmp_path) / row["name"]).exists()
    ]
    unmoved = [row["name"] for row in batch if (tmp_path / row["name"]).exists()]
    assert len(moved) == 2
    assert len(unmoved) == 1

    records = [
        json.loads(line) for line in audit_file.read_text(encoding="utf-8").splitlines() if line
    ]
    row_events = [record for record in records if record.get("event") == "apply_row"]
    outcomes = [record["outcome"] for record in row_events]
    assert outcomes.count("ok") == 2
    assert outcomes.count("error") == 1
    assert api.get_snapshot()["work"]["resolve"]["hasPendingApply"] is False


def test_get_duplicate_group_detail_members_and_keeper(tmp_path: Path) -> None:
    api = _duplicate_api(tmp_path)
    page = api.query_review_rows({"viewMode": "groups", "limit": 50})
    group_row = next(r for r in page["rows"] if r["rowKind"] == "group")
    gid = group_row["groupId"]
    assert isinstance(gid, str)
    detail = api.get_duplicate_group_detail(gid)
    validate_duplicate_group_detail(detail)
    assert detail["status"] == "ok"
    assert len(detail["members"]) >= 2
    assert sum(1 for m in detail["members"] if m["isKeeper"]) == 1
    assert detail["members"][0]["integrity"]["issueCount"] >= 0


def test_detail_keeper_follows_set_keeper(tmp_path: Path) -> None:
    api = _duplicate_api(tmp_path)
    page = api.query_review_rows({"viewMode": "groups", "limit": 50})
    group_row = next(r for r in page["rows"] if r["rowKind"] == "group")
    gid = group_row["groupId"]
    file_row = next(
        r
        for r in page["rows"]
        if r["rowKind"] == "file" and r["proposedAction"] == "move_duplicate"
    )
    new_keeper_id = file_row["id"].split(":")[-1]
    api.update_review_decisions(
        {
            "selection": {"type": "explicit_rows", "rowIds": [file_row["id"]]},
            "command": "setKeeper",
            "keeperFileId": new_keeper_id,
        }
    )
    detail = api.get_duplicate_group_detail(gid)
    assert detail["status"] == "ok"
    assert detail["keeperFileId"] == new_keeper_id


def test_get_duplicate_group_detail_not_found(tmp_path: Path) -> None:
    api = _duplicate_api(tmp_path)
    detail = api.get_duplicate_group_detail("dup-nonexistent")
    validate_duplicate_group_detail(detail)
    assert detail["status"] == "not_found"
    assert detail["members"] == []


def test_pick_keeper_file_id_tie_break_size_mtime_path_id() -> None:
    from domain.keeper_selection import pick_keeper_file_id
    from domain.models import FileRecord

    def record(*, id_char: str, path: str, size: int, mtime: int) -> FileRecord:
        return FileRecord(
            id=id_char * 64,
            relative_path=path,
            name=path.split("/")[-1],
            size_bytes=size,
            modified_at_ns=mtime,
            extension=".txt",
        )

    larger = record(id_char="a", path="z.txt", size=200, mtime=1)
    smaller = record(id_char="b", path="a.txt", size=100, mtime=1)
    assert pick_keeper_file_id([smaller, larger]) == larger.id

    older = record(id_char="c", path="a.txt", size=100, mtime=1)
    newer = record(id_char="d", path="z.txt", size=100, mtime=2)
    assert pick_keeper_file_id([older, newer]) == newer.id

    path_a = record(id_char="e", path="alpha.txt", size=100, mtime=1)
    path_z = record(id_char="f", path="zeta.txt", size=100, mtime=1)
    assert pick_keeper_file_id([path_a, path_z]) == path_z.id


def test_near_non_keeper_skeleton_has_move_duplicate_proposed_action() -> None:
    from application.near_review_rows_builder import build_near_review_rows
    from domain.duplicate_near import NearDuplicateGroup
    from domain.models import FileRecord

    keeper = FileRecord(
        id="k" * 64,
        relative_path="keep.txt",
        name="keep.txt",
        size_bytes=200,
        modified_at_ns=2,
        extension=".txt",
    )
    other = FileRecord(
        id="o" * 64,
        relative_path="other.txt",
        name="other.txt",
        size_bytes=100,
        modified_at_ns=1,
        extension=".txt",
    )
    files_by_id = {keeper.id: keeper, other.id: other}
    groups = [
        NearDuplicateGroup(
            group_id="near:test",
            member_file_ids=(keeper.id, other.id),
            pairs=(),
            max_similarity=0.9,
        )
    ]
    rows = build_near_review_rows(groups, files_by_id)
    non_keeper = next(
        row for row in rows if row["rowKind"] == "file" and row["id"].endswith(other.id)
    )
    assert non_keeper["proposedAction"] == "move_duplicate"
    assert non_keeper["targetFolder"] == "duplicate/"


def test_bulk_approve_near_file_row_updates_member(tmp_path: Path) -> None:
    (tmp_path / "alpha.txt").write_text(_near_similar_body("alpha"), encoding="utf-8")
    (tmp_path / "beta.txt").write_text(_near_similar_body("beta"), encoding="utf-8")
    session = create_library_session(MemoryLibraryIndex())
    session.select_folder(str(tmp_path))
    api = create_bridge_api(session)
    api.start_scan()
    _wait_deep_analysis_complete(api)
    near_page = api.query_review_rows(
        {"viewMode": "all", "limit": 50, "filters": {"types": ["near"]}}
    )
    file_rows = [
        row
        for row in near_page["rows"]
        if row["rowKind"] == "file" and row.get("status") == "unreviewed"
    ]
    if not file_rows:
        pytest.skip("no near duplicate groups in fixture")
    file_row = file_rows[0]
    result = api.update_review_decisions(
        {
            "selection": {"type": "explicit_rows", "rowIds": [file_row["id"]]},
            "command": "approve",
        }
    )
    assert result["updatedCount"] == 1
    from application.review_state_merge import _file_id_from_row_id

    file_id = _file_id_from_row_id(str(file_row["id"]))
    assert file_id is not None
    stored = session.index.load_review_state(session.index.folder_path or str(tmp_path))
    assert stored.members.get(file_id) == "approved"
    page_after = api.query_review_rows({"viewMode": "all", "limit": 50})
    approved_row = next(
        (row for row in page_after["rows"] if row["id"] == file_row["id"]),
        None,
    )
    if approved_row is not None:
        assert approved_row["status"] == "approved"
        assert approved_row["proposedAction"] in {"keep", "move_duplicate"}


def _near_similar_body(seed: str) -> str:
    paragraph = (
        "The quick brown fox jumps over the lazy dog. "
        "Near duplicate detection uses normalized text n-grams. "
    )
    return (paragraph * 12) + f" variant-{seed} "


def test_normalize_text_for_near_dup_deterministic() -> None:
    from domain.duplicate_near import normalize_text_for_near_dup

    raw = "  Hello\r\nWorld  "
    assert normalize_text_for_near_dup(raw) == normalize_text_for_near_dup(raw)
    assert normalize_text_for_near_dup(raw) == "hello world"


def test_near_duplicate_blocking_reduces_pairs() -> None:
    from domain.duplicate_near import NearDuplicateInput, find_near_duplicate_groups

    files: list[NearDuplicateInput] = []
    for index in range(20):
        body = _near_similar_body(f"txt-{index}")
        files.append(
            NearDuplicateInput(
                file_id=f"txt-{index}",
                path=f"t{index}.txt",
                extension=".txt",
                content_hash=f"hash-txt-{index}",
                size_bytes=len(body),
                mtime_ns=index,
                text=body,
            )
        )
    for index in range(20):
        body = _near_similar_body(f"json-{index}")
        files.append(
            NearDuplicateInput(
                file_id=f"json-{index}",
                path=f"j{index}.json",
                extension=".json",
                content_hash=f"hash-json-{index}",
                size_bytes=len(body),
                mtime_ns=100 + index,
                text=body,
            )
        )
    result = find_near_duplicate_groups(
        files,
        exact_group_by_file_id={},
        near_batch_id="batch-test",
    )
    naive = 40 * 39 // 2
    within_family_max = 2 * (20 * 19 // 2)
    assert result.stats.candidate_pair_count <= within_family_max
    assert result.stats.candidate_pair_count < naive


def test_near_duplicate_skips_same_exact_group(tmp_path: Path) -> None:
    from domain.duplicate_exact import find_exact_duplicate_groups
    from domain.duplicate_near import NearDuplicateInput, find_near_duplicate_groups
    from domain.models import FileRecord, make_file_id

    body = _near_similar_body("dup")
    records = [
        FileRecord(
            id=make_file_id(f"{name}.txt", len(body), i),
            relative_path=f"{name}.txt",
            name=f"{name}.txt",
            size_bytes=len(body),
            modified_at_ns=i,
            extension=".txt",
            content_sha256="samehash",
        )
        for i, name in enumerate(("a", "b"))
    ]
    exact_map = {
        member_id: group.group_id
        for group in find_exact_duplicate_groups(records)
        for member_id in group.member_ids
    }
    inputs = [
        NearDuplicateInput(
            file_id=record.id,
            path=record.relative_path,
            extension=record.extension,
            content_hash=record.content_sha256,
            size_bytes=record.size_bytes,
            mtime_ns=record.modified_at_ns,
            text=body,
        )
        for record in records
    ]
    result = find_near_duplicate_groups(
        inputs,
        exact_group_by_file_id=exact_map,
        near_batch_id="batch-exact-skip",
    )
    assert result.stats.accepted_pair_count == 0


def test_query_review_rows_near_after_similar_scan(tmp_path: Path) -> None:
    (tmp_path / "alpha.txt").write_text(_near_similar_body("alpha"), encoding="utf-8")
    (tmp_path / "beta.txt").write_text(_near_similar_body("beta"), encoding="utf-8")
    session = create_library_session(MemoryLibraryIndex())
    session.select_folder(str(tmp_path))
    api = create_bridge_api(session)
    api.start_scan()
    _wait_deep_analysis_complete(api)
    near_page = api.query_review_rows(
        {"viewMode": "all", "limit": 50, "filters": {"types": ["near"]}}
    )
    validate_review_rows_page(near_page)
    assert near_page["rows"]
    assert all(row["type"] == "near" for row in near_page["rows"])
    assert any(row["rowKind"] == "group" for row in near_page["rows"])


def test_get_near_duplicate_group_detail(tmp_path: Path) -> None:
    (tmp_path / "alpha.txt").write_text(_near_similar_body("alpha"), encoding="utf-8")
    (tmp_path / "beta.txt").write_text(_near_similar_body("beta"), encoding="utf-8")
    session = create_library_session(MemoryLibraryIndex())
    session.select_folder(str(tmp_path))
    api = create_bridge_api(session)
    api.start_scan()
    _scan_until_idle(api)
    near_page = api.query_review_rows(
        {"viewMode": "all", "limit": 50, "filters": {"types": ["near"]}}
    )
    group_row = next((row for row in near_page["rows"] if row["rowKind"] == "group"), None)
    if group_row is None:
        return
    detail = api.get_duplicate_group_detail(group_row["groupId"])
    validate_duplicate_group_detail(detail)
    assert detail["status"] == "ok"
    assert detail["type"] == "near"
    assert detail["evidence"]["matchKind"] == "near_ngram_v1"


def test_preview_skips_unapproved_near_duplicate_rows(tmp_path: Path) -> None:
    (tmp_path / "alpha.txt").write_text(_near_similar_body("alpha"), encoding="utf-8")
    (tmp_path / "beta.txt").write_text(_near_similar_body("beta"), encoding="utf-8")
    session = create_library_session(MemoryLibraryIndex())
    session.select_folder(str(tmp_path))
    api = create_bridge_api(session)
    api.start_scan()
    _scan_until_idle(api)
    near_page = api.query_review_rows(
        {"viewMode": "all", "limit": 50, "filters": {"types": ["near"]}}
    )
    file_row = next((row for row in near_page["rows"] if row["rowKind"] == "file"), None)
    if file_row is None:
        return
    preview = api.get_move_preview({"type": "explicit_rows", "rowIds": [file_row["id"]]})
    validate_move_preview(preview)
    assert preview["summary"]["operationCount"] == 0


def test_approve_near_group_member_persists(tmp_path: Path) -> None:
    (tmp_path / "alpha.txt").write_text(_near_similar_body("alpha"), encoding="utf-8")
    (tmp_path / "beta.txt").write_text(_near_similar_body("beta"), encoding="utf-8")
    session = create_library_session(MemoryLibraryIndex())
    session.select_folder(str(tmp_path))
    api = create_bridge_api(session)
    api.start_scan()
    _scan_until_idle(api)
    near_page = api.query_review_rows(
        {"viewMode": "all", "limit": 50, "filters": {"types": ["near"]}}
    )
    file_rows = [row for row in near_page["rows"] if row["rowKind"] == "file"]
    if len(file_rows) < 2:
        pytest.skip("near duplicate group not detected in fixture")
    target = file_rows[0]
    result = api.update_review_decisions(
        {
            "selection": {"type": "explicit_rows", "rowIds": [target["id"]]},
            "command": "approve",
        }
    )
    assert result["updatedCount"] >= 1
    folder = session._index.folder_path
    assert folder is not None
    stored = session._index.load_review_state(folder)
    assert any(status == "approved" for status in stored.members.values())


def test_preview_allows_near_approved_move_duplicate(tmp_path: Path) -> None:
    (tmp_path / "alpha.txt").write_text(_near_similar_body("alpha"), encoding="utf-8")
    (tmp_path / "beta.txt").write_text(_near_similar_body("beta"), encoding="utf-8")
    session = create_library_session(MemoryLibraryIndex())
    session.select_folder(str(tmp_path))
    api = create_bridge_api(session)
    api.start_scan()
    _scan_until_idle(api)
    near_page = api.query_review_rows(
        {"viewMode": "all", "limit": 50, "filters": {"types": ["near"]}}
    )
    file_rows = [row for row in near_page["rows"] if row["rowKind"] == "file"]
    if len(file_rows) < 2:
        pytest.skip("near duplicate group not detected in fixture")
    summary = api.summarize_auto_select_keepers(
        {"viewMode": "all", "limit": 50, "filters": {"types": ["near"]}}
    )
    if summary["keeperRowIds"]:
        api.update_review_decisions(
            {
                "selection": {"type": "explicit_rows", "rowIds": summary["keeperRowIds"]},
                "command": "setKeeper",
            }
        )
    api.update_review_decisions(
        {
            "selection": {
                "type": "current_query",
                "query": {
                    "viewMode": "all",
                    "limit": 50,
                    "filters": {"types": ["near"], "status": ["unreviewed"]},
                },
                "excludeRowIds": [],
            },
            "command": "approve",
        }
    )
    refreshed = api.query_review_rows(
        {"viewMode": "all", "limit": 50, "filters": {"types": ["near"]}}
    )
    move_rows = [
        row
        for row in refreshed["rows"]
        if row.get("rowKind") == "file" and row.get("proposedAction") == "move_duplicate"
    ]
    if not move_rows:
        pytest.skip("no near move_duplicate rows after approve")
    preview = api.get_move_preview({"type": "explicit_rows", "rowIds": [move_rows[0]["id"]]})
    validate_move_preview(preview)
    assert preview["summary"]["operationCount"] >= 1
    assert preview["rows"][0]["action"] == "move_duplicate"


def test_summarize_auto_select_keepers_counts_unreviewed_file_rows(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("x" * 100, encoding="utf-8")
    (tmp_path / "b.txt").write_text("x" * 100, encoding="utf-8")
    session = create_library_session(MemoryLibraryIndex())
    session.select_folder(str(tmp_path))
    api = create_bridge_api(session)
    api.start_scan()
    _scan_until_idle(api)
    summary = api.summarize_auto_select_keepers({"viewMode": "all", "limit": 50})
    assert summary["targetCount"] >= 0
    assert summary["keeperCount"] <= summary["targetCount"]
    assert summary["moveCandidateCount"] == max(0, summary["targetCount"] - summary["keeperCount"])
    assert isinstance(summary["keeperRowIds"], list)


def _synthetic_exact_group_fixture(
    count: int,
    *,
    group_id: str = "exact:" + "a" * 64,
) -> tuple[list[dict[str, object]], dict[str, FileRecord], dict[str, set[str]]]:
    rows: list[dict[str, object]] = []
    files_by_id: dict[str, FileRecord] = {}
    member_ids: set[str] = set()
    for index in range(count):
        file_id = f"{index:064x}"
        member_ids.add(file_id)
        files_by_id[file_id] = FileRecord(
            id=file_id,
            relative_path=f"dup/file-{index}.txt",
            name=f"file-{index}.txt",
            size_bytes=100 + index,
            modified_at_ns=index,
            extension=".txt",
            content_sha256=f"{index:064x}",
        )
        rows.append(
            {
                "id": f"file:dup-{file_id}",
                "rowKind": "file",
                "groupId": group_id,
                "type": "exact",
                "status": "unreviewed",
                "name": f"file-{index}.txt",
                "proposedAction": "move_duplicate",
            }
        )
    return rows, files_by_id, {group_id: member_ids}


def test_summarize_resolve_auto_approve_full_filter_no_500_cap() -> None:
    from application.auto_select_summary import summarize_auto_select_keepers
    from application.summarize_resolve_auto_approve import summarize_resolve_auto_approve

    rows, files_by_id, members_by_group = _synthetic_exact_group_fixture(600)
    query = {"viewMode": "all", "limit": 50, "filters": {"types": ["exact"]}}
    capped = summarize_auto_select_keepers(rows, query, files_by_id=files_by_id)
    full = summarize_resolve_auto_approve(
        rows,
        query,
        files_by_id=files_by_id,
        members_by_group=members_by_group,
    )
    validate_resolve_auto_approve_summary(full)
    assert capped["targetCount"] == 500
    assert full["unreviewedCount"] == 600
    assert full["moveCandidateCount"] == 599
    assert full["keeperCount"] == 1


def test_summarize_resolve_auto_approve_keeper_uses_full_group_membership() -> None:
    from application.summarize_resolve_auto_approve import summarize_resolve_auto_approve

    group_id = "exact:" + "b" * 64
    large_id = "a" * 64
    small_id = "c" * 64
    files_by_id = {
        large_id: FileRecord(
            id=large_id,
            relative_path="large.txt",
            name="large.txt",
            size_bytes=200,
            modified_at_ns=1,
            extension=".txt",
            content_sha256="1" * 64,
        ),
        small_id: FileRecord(
            id=small_id,
            relative_path="small.txt",
            name="small.txt",
            size_bytes=50,
            modified_at_ns=2,
            extension=".txt",
            content_sha256="2" * 64,
        ),
    }
    rows = [
        {
            "id": f"file:dup-{large_id}",
            "rowKind": "file",
            "groupId": group_id,
            "type": "exact",
            "status": "approved",
            "name": "large.txt",
            "proposedAction": "keep",
        },
        {
            "id": f"file:dup-{small_id}",
            "rowKind": "file",
            "groupId": group_id,
            "type": "exact",
            "status": "unreviewed",
            "name": "small.txt",
            "proposedAction": "move_duplicate",
        },
    ]
    summary = summarize_resolve_auto_approve(
        rows,
        {"viewMode": "all", "limit": 50, "filters": {"types": ["exact"]}},
        files_by_id=files_by_id,
        members_by_group={group_id: {large_id, small_id}},
    )
    assert summary["unreviewedCount"] == 1
    assert summary["keeperCount"] == 0
    assert summary["moveCandidateCount"] == 1


def _resolve_auto_approve_job_until_terminal(api: BridgeApi) -> dict[str, Any]:
    deadline = time.monotonic() + 10.0
    snap = api.get_snapshot()
    job = snap["resolveAutoApproveJob"]
    while time.monotonic() < deadline and job["status"] == "running":
        time.sleep(0.02)
        snap = api.get_snapshot()
        job = snap["resolveAutoApproveJob"]
    return job


def test_resolve_auto_approve_job_snapshot_idle_by_default() -> None:
    snap = _memory_api().get_snapshot()
    job = snap["resolveAutoApproveJob"]
    assert job["status"] == "idle"
    assert job["summary"] is None


def test_start_resolve_auto_approve_job_polls_dry_run_summary(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("x" * 100, encoding="utf-8")
    (tmp_path / "b.txt").write_text("x" * 100, encoding="utf-8")
    session = create_library_session(MemoryLibraryIndex())
    session.select_folder(str(tmp_path))
    api = create_bridge_api(session)
    api.start_scan()
    _scan_until_idle(api)
    revision_before = session.library_revision()
    query = {"viewMode": "all", "limit": 50}
    direct = api.summarize_resolve_auto_approve(query)
    accepted = api.start_resolve_auto_approve_job(query)
    assert accepted == {"accepted": True}
    job = _resolve_auto_approve_job_until_terminal(api)
    assert job["status"] == "complete"
    assert job["summary"] is not None
    validate_resolve_auto_approve_summary(job["summary"])
    assert job["summary"]["unreviewedCount"] == direct["unreviewedCount"]
    assert job["summary"]["keeperCount"] == direct["keeperCount"]
    assert job["summary"]["moveCandidateCount"] == direct["moveCandidateCount"]
    assert session.library_revision() == revision_before


def test_start_resolve_auto_approve_job_rejects_when_already_running() -> None:
    import application.summarize_resolve_auto_approve as summarize_module

    rows, files_by_id, members_by_group = _synthetic_exact_group_fixture(200)
    session = create_library_session(MemoryLibraryIndex())
    with session._lock:  # noqa: SLF001
        session._review_rows_cache = rows
        session._files_by_id = files_by_id
    session.build_review_members_by_group = lambda: members_by_group  # type: ignore[method-assign]
    api = create_bridge_api(session)
    query = {"viewMode": "all", "limit": 50, "filters": {"types": ["exact"]}}
    original_stream = summarize_module._stream_file_rows

    def slow_stream(*args: Any, **kwargs: Any) -> list[dict[str, Any]]:
        time.sleep(0.02)
        return original_stream(*args, **kwargs)

    summarize_module._stream_file_rows = slow_stream
    try:
        api.start_resolve_auto_approve_job(query)
        with pytest.raises(PreviewApplyError, match="JOB_ALREADY_RUNNING"):
            api.start_resolve_auto_approve_job(query)
        _resolve_auto_approve_job_until_terminal(api)
    finally:
        summarize_module._stream_file_rows = original_stream


def test_start_resolve_auto_approve_job_rejects_no_targets() -> None:
    api = _memory_api()
    with pytest.raises(PreviewApplyError, match="NO_UNREVIEWED_TARGETS"):
        api.start_resolve_auto_approve_job({"viewMode": "all", "limit": 50})


def test_cancel_resolve_auto_approve_job_marks_cancelled() -> None:
    import application.summarize_resolve_auto_approve as summarize_module

    rows, files_by_id, members_by_group = _synthetic_exact_group_fixture(800)
    session = create_library_session(MemoryLibraryIndex())
    with session._lock:  # noqa: SLF001
        session._review_rows_cache = rows
        session._files_by_id = files_by_id
    session.build_review_members_by_group = lambda: members_by_group  # type: ignore[method-assign]
    api = create_bridge_api(session)
    query = {"viewMode": "all", "limit": 50, "filters": {"types": ["exact"]}}
    original_stream = summarize_module._stream_file_rows

    def slow_stream(*args: Any, **kwargs: Any) -> list[dict[str, Any]]:
        time.sleep(0.02)
        return original_stream(*args, **kwargs)

    summarize_module._stream_file_rows = slow_stream
    try:
        api.start_resolve_auto_approve_job(query)
        api.cancel_resolve_auto_approve_job()
        job = _resolve_auto_approve_job_until_terminal(api)
    finally:
        summarize_module._stream_file_rows = original_stream
    assert job["status"] == "cancelled"


def test_summarize_resolve_auto_approve_bridge_counts_unreviewed_file_rows(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("x" * 100, encoding="utf-8")
    (tmp_path / "b.txt").write_text("x" * 100, encoding="utf-8")
    session = create_library_session(MemoryLibraryIndex())
    session.select_folder(str(tmp_path))
    api = create_bridge_api(session)
    api.start_scan()
    _scan_until_idle(api)
    summary = api.summarize_resolve_auto_approve({"viewMode": "all", "limit": 50})
    validate_resolve_auto_approve_summary(summary)
    assert summary["unreviewedCount"] >= 0
    assert summary["keeperCount"] <= summary["unreviewedCount"]
    assert summary["moveCandidateCount"] == max(
        0, summary["unreviewedCount"] - summary["keeperCount"]
    )


def test_relation_token_precedence_v2_is_version_not_numeric() -> None:
    from domain.filename_relation import normalize_filename_for_relation

    parsed = normalize_filename_for_relation("Novel v2.txt", relative_path="Novel v2.txt")
    assert parsed.version_markers == ("v2",)
    assert parsed.numeric_tokens == ()

    parsed_v10 = normalize_filename_for_relation("Title v10.txt", relative_path="Title v10.txt")
    assert parsed_v10.version_markers == ("v10",)
    assert 10 not in parsed_v10.numeric_tokens

    parsed_v01 = normalize_filename_for_relation("Story v01.txt", relative_path="Story v01.txt")
    assert parsed_v01.version_markers == ("v01",)
    assert 1 not in parsed_v01.numeric_tokens


def test_relation_batch_and_cluster_ids_are_deterministic() -> None:
    from application.relation_batch_id import filename_set_digest, make_relation_batch_id
    from domain.filename_relation import detect_filename_relations
    from domain.models import FileRecord

    files = [
        FileRecord(
            id="a" * 64,
            relative_path="Series/Novel 01.txt",
            name="Novel 01.txt",
            size_bytes=100,
            modified_at_ns=1,
            extension=".txt",
            content_sha256="h1",
        ),
        FileRecord(
            id="b" * 64,
            relative_path="Series/Novel 02.txt",
            name="Novel 02.txt",
            size_bytes=100,
            modified_at_ns=2,
            extension=".txt",
            content_sha256="h2",
        ),
    ]
    digest = filename_set_digest(files)
    batch_a = make_relation_batch_id(library_revision=3, filename_set_digest_value=digest)
    batch_b = make_relation_batch_id(library_revision=3, filename_set_digest_value=digest)
    assert batch_a == batch_b

    result_a = detect_filename_relations(
        files,
        exact_membership_by_file_id={},
        near_membership_by_file_id={},
        relation_batch_id=batch_a,
    )
    result_b = detect_filename_relations(
        files,
        exact_membership_by_file_id={},
        near_membership_by_file_id={},
        relation_batch_id=batch_b,
    )
    assert [group.group_id for group in result_a.groups] == [
        group.group_id for group in result_b.groups
    ]


def test_relation_does_not_group_generic_chapter_across_folders() -> None:
    from domain.filename_relation import RELATION_KINDS_V1, detect_filename_relations
    from domain.models import FileRecord

    files = [
        FileRecord(
            id="a" * 64,
            relative_path="FolderA/Chapter 01.txt",
            name="Chapter 01.txt",
            size_bytes=100,
            modified_at_ns=1,
            extension=".txt",
        ),
        FileRecord(
            id="b" * 64,
            relative_path="FolderB/Chapter 02.txt",
            name="Chapter 02.txt",
            size_bytes=100,
            modified_at_ns=2,
            extension=".txt",
        ),
    ]
    result = detect_filename_relations(
        files,
        exact_membership_by_file_id={},
        near_membership_by_file_id={},
        relation_batch_id="batch-test",
    )
    assert result.groups == ()
    for group in result.groups:
        assert group.relation_kind in RELATION_KINDS_V1


def test_relation_groups_generic_chapter_in_same_parent() -> None:
    from domain.filename_relation import RELATION_KINDS_V1, detect_filename_relations
    from domain.models import FileRecord

    files = [
        FileRecord(
            id="a" * 64,
            relative_path="Series/Chapter 01.txt",
            name="Chapter 01.txt",
            size_bytes=100,
            modified_at_ns=1,
            extension=".txt",
        ),
        FileRecord(
            id="b" * 64,
            relative_path="Series/Chapter 02.txt",
            name="Chapter 02.txt",
            size_bytes=100,
            modified_at_ns=2,
            extension=".txt",
        ),
    ]
    result = detect_filename_relations(
        files,
        exact_membership_by_file_id={},
        near_membership_by_file_id={},
        relation_batch_id="batch-test",
    )
    assert len(result.groups) == 1
    assert result.groups[0].relation_kind in RELATION_KINDS_V1


def test_relation_title_prefix_overlap_same_folder() -> None:
    from domain.filename_relation import detect_filename_relations
    from domain.models import FileRecord

    files = [
        FileRecord(
            id="a" * 64,
            relative_path="Series/Alpha Chronicle.txt",
            name="Alpha Chronicle.txt",
            size_bytes=100,
            modified_at_ns=1,
            extension=".txt",
        ),
        FileRecord(
            id="b" * 64,
            relative_path="Series/Alpha Chronicle Side Story.txt",
            name="Alpha Chronicle Side Story.txt",
            size_bytes=100,
            modified_at_ns=2,
            extension=".txt",
        ),
    ]
    result = detect_filename_relations(
        files,
        exact_membership_by_file_id={},
        near_membership_by_file_id={},
        relation_batch_id="batch-prefix",
    )
    assert len(result.groups) == 1
    assert result.groups[0].relation_kind == "title_prefix_overlap"
    assert result.groups[0].confidence_label == "low"


def test_relation_no_prefix_overlap_unrelated_titles() -> None:
    from domain.filename_relation import detect_filename_relations
    from domain.models import FileRecord

    files = [
        FileRecord(
            id="a" * 64,
            relative_path="FolderA/Completely Different Alpha.txt",
            name="Completely Different Alpha.txt",
            size_bytes=100,
            modified_at_ns=1,
            extension=".txt",
        ),
        FileRecord(
            id="b" * 64,
            relative_path="FolderB/Another Story Entirely Beta.txt",
            name="Another Story Entirely Beta.txt",
            size_bytes=100,
            modified_at_ns=2,
            extension=".txt",
        ),
    ]
    result = detect_filename_relations(
        files,
        exact_membership_by_file_id={},
        near_membership_by_file_id={},
        relation_batch_id="batch-prefix-neg",
    )
    assert result.groups == ()


def test_relation_no_prefix_overlap_when_prefix_too_short() -> None:
    from domain.filename_relation import detect_filename_relations
    from domain.models import FileRecord

    files = [
        FileRecord(
            id="a" * 64,
            relative_path="Series/Short Title.txt",
            name="Short Title.txt",
            size_bytes=100,
            modified_at_ns=1,
            extension=".txt",
        ),
        FileRecord(
            id="b" * 64,
            relative_path="Series/Short Title Bonus.txt",
            name="Short Title Bonus.txt",
            size_bytes=100,
            modified_at_ns=2,
            extension=".txt",
        ),
    ]
    result = detect_filename_relations(
        files,
        exact_membership_by_file_id={},
        near_membership_by_file_id={},
        relation_batch_id="batch-prefix-short",
    )
    assert result.groups == ()


def test_include_relation_false_skips_relation_rows(tmp_path: Path) -> None:
    (tmp_path / "Novel 01.txt").write_text("x", encoding="utf-8")
    (tmp_path / "Novel 02.txt").write_text("y", encoding="utf-8")
    session = create_library_session(MemoryLibraryIndex(), settings=AppSettings())
    session.select_folder(str(tmp_path))
    api = create_bridge_api(session)
    payload = api.get_app_setting("include_relation")
    assert payload["value"] is True
    assert payload["source"] == "default"
    api.set_app_setting("include_relation", False)  # type: ignore[arg-type]
    api.start_scan()
    _scan_until_idle(api)
    page = api.query_review_rows(
        {"viewMode": "all", "limit": 50, "filters": {"types": ["relation"]}}
    )
    assert page["rows"] == []


def test_query_review_rows_relation_after_enabled_scan(tmp_path: Path) -> None:
    (tmp_path / "Novel 01.txt").write_text("x", encoding="utf-8")
    (tmp_path / "Novel 02.txt").write_text("y", encoding="utf-8")
    session = create_library_session(MemoryLibraryIndex())
    session.select_folder(str(tmp_path))
    api = create_bridge_api(session)
    api.set_app_setting("include_relation", True)  # type: ignore[arg-type]
    api.start_scan()
    _scan_until_idle(api)
    relation_page = api.query_review_rows(
        {"viewMode": "all", "limit": 50, "filters": {"types": ["relation"]}}
    )
    validate_review_rows_page(relation_page)
    if relation_page["rows"]:
        assert all(row["type"] == "relation" for row in relation_page["rows"])
        assert all(
            row.get("relationKind")
            in (
                "same_title_series",
                "chapter_sequence",
                "version_variant",
                "title_prefix_overlap",
            )
            for row in relation_page["rows"]
            if row.get("relationKind")
        )


def test_get_relation_group_detail(tmp_path: Path) -> None:
    (tmp_path / "Novel 01.txt").write_text("x", encoding="utf-8")
    (tmp_path / "Novel 02.txt").write_text("y", encoding="utf-8")
    session = create_library_session(MemoryLibraryIndex())
    session.select_folder(str(tmp_path))
    api = create_bridge_api(session)
    api.set_app_setting("include_relation", True)  # type: ignore[arg-type]
    api.start_scan()
    _scan_until_idle(api)
    relation_page = api.query_review_rows(
        {"viewMode": "all", "limit": 50, "filters": {"types": ["relation"]}}
    )
    group_row = next((row for row in relation_page["rows"] if row["rowKind"] == "group"), None)
    if group_row is None:
        return
    detail = api.get_duplicate_group_detail(group_row["groupId"])
    validate_duplicate_group_detail(detail)
    assert detail["type"] == "relation"
    assert detail["evidence"]["matchKind"] == "relation_filename_v1"


def test_preview_skips_unapproved_relation_rows(tmp_path: Path) -> None:
    (tmp_path / "Novel 01.txt").write_text("x", encoding="utf-8")
    (tmp_path / "Novel 02.txt").write_text("y", encoding="utf-8")
    session = create_library_session(MemoryLibraryIndex())
    session.select_folder(str(tmp_path))
    api = create_bridge_api(session)
    api.set_app_setting("include_relation", True)  # type: ignore[arg-type]
    api.start_scan()
    _scan_until_idle(api)
    relation_page = api.query_review_rows(
        {"viewMode": "all", "limit": 50, "filters": {"types": ["relation"]}}
    )
    file_row = next((row for row in relation_page["rows"] if row["rowKind"] == "file"), None)
    if file_row is None:
        return
    preview = api.get_move_preview({"type": "explicit_rows", "rowIds": [file_row["id"]]})
    validate_move_preview(preview)
    assert preview["summary"]["operationCount"] == 0


def test_preview_accepts_approved_relation_rows(tmp_path: Path) -> None:
    (tmp_path / "Novel 01.txt").write_text("x", encoding="utf-8")
    (tmp_path / "Novel 02.txt").write_text("y", encoding="utf-8")
    session = create_library_session(MemoryLibraryIndex())
    session.select_folder(str(tmp_path))
    api = create_bridge_api(session)
    api.set_app_setting("include_relation", True)  # type: ignore[arg-type]
    api.start_scan()
    _scan_until_idle(api)
    relation_page = api.query_review_rows(
        {"viewMode": "all", "limit": 50, "filters": {"types": ["relation"]}}
    )
    file_row = next(
        (
            row
            for row in relation_page["rows"]
            if row["rowKind"] == "file" and row.get("proposedAction") == "move_duplicate"
        ),
        None,
    )
    if file_row is None:
        return
    api.update_review_decisions(
        {
            "selection": {"type": "explicit_rows", "rowIds": [file_row["id"]]},
            "command": "approve",
        }
    )
    preview = api.get_move_preview({"type": "explicit_rows", "rowIds": [file_row["id"]]})
    validate_move_preview(preview)
    assert preview["summary"]["operationCount"] >= 1
    assert preview["rows"][0]["action"] == "move_duplicate"


def _encoding_issue_row(api: BridgeApi) -> dict:
    page = api.query_quality_rows({"issueType": "encoding", "limit": 20})
    assert page["rows"], "expected encoding quality row"
    return page["rows"][0]


def test_quality_repair_preview_cp949_success(tmp_path: Path) -> None:
    text = "안녕하세요"
    (tmp_path / "korean.txt").write_bytes(text.encode("cp949"))
    session = create_library_session(MemoryLibraryIndex())
    session.select_folder(str(tmp_path))
    api = create_bridge_api(session)
    api.start_scan()
    _scan_until_idle(api)
    row = _encoding_issue_row(api)
    preview = api.get_quality_repair_preview({"issueIds": [row["id"]]})
    validate_quality_repair_preview(preview)
    assert preview["summary"]["operationCount"] == 1
    assert preview["rows"][0]["sourceEncoding"] == "cp949"
    assert preview["rows"][0]["encodingConfidence"] == "high"
    api.apply_quality_repair(
        {"issueIds": [row["id"]], "repairPreviewToken": preview["repairPreviewToken"]}
    )
    repaired = (tmp_path / "korean.txt").read_text(encoding="utf-8")
    assert repaired == text
    page = api.query_quality_rows({"issueType": "encoding", "limit": 20})
    assert all(r["id"] != row["id"] for r in page["rows"])


def test_quality_repair_rejects_empty_file_issue(tmp_path: Path) -> None:
    (tmp_path / "empty.txt").write_bytes(b"")
    (tmp_path / "korean.txt").write_bytes("x".encode("cp949"))
    session = create_library_session(MemoryLibraryIndex())
    session.select_folder(str(tmp_path))
    api = create_bridge_api(session)
    api.start_scan()
    _scan_until_idle(api)
    small = api.query_quality_rows({"issueType": "small_file", "limit": 5})["rows"][0]
    with pytest.raises(RepairPreviewError) as exc_info:
        api.get_quality_repair_preview({"issueIds": [small["id"]]})
    assert exc_info.value.reason == "MIXED_OR_INELIGIBLE_SELECTION"


def test_quality_repair_batch_limit(tmp_path: Path) -> None:
    session = create_library_session(MemoryLibraryIndex())
    session.select_folder(str(tmp_path))
    api = create_bridge_api(session)
    with pytest.raises(RepairPreviewError) as exc_info:
        api.get_quality_repair_preview({"issueIds": [f"quality:{i}" for i in range(11)]})
    assert exc_info.value.reason == "BATCH_LIMIT_EXCEEDED"


def test_move_preview_blocked_when_repair_pending(tmp_path: Path) -> None:
    (tmp_path / "korean.txt").write_bytes("안녕".encode("cp949"))
    (tmp_path / "a.txt").write_text("a", encoding="utf-8")
    (tmp_path / "b.txt").write_text("b", encoding="utf-8")
    session = create_library_session(MemoryLibraryIndex())
    session.select_folder(str(tmp_path))
    api = create_bridge_api(session)
    api.start_scan()
    _scan_until_idle(api)
    enc_row = _encoding_issue_row(api)
    api.get_quality_repair_preview({"issueIds": [enc_row["id"]]})
    dup_page = api.query_review_rows({"viewMode": "action", "limit": 50})
    file_rows = [r for r in dup_page["rows"] if r.get("rowKind") == "file"]
    if not file_rows:
        return
    with pytest.raises(PreviewApplyError) as exc_info:
        api.get_move_preview({"type": "explicit_rows", "rowIds": [file_rows[0]["id"]]})
    assert exc_info.value.reason == "REPAIR_PREVIEW_ACTIVE"


def test_repair_preview_blocked_when_move_pending(tmp_path: Path) -> None:
    (tmp_path / "korean.txt").write_bytes("안녕".encode("cp949"))
    (tmp_path / "a.txt").write_text("a", encoding="utf-8")
    (tmp_path / "b.txt").write_text("b", encoding="utf-8")
    session = create_library_session(MemoryLibraryIndex())
    session.select_folder(str(tmp_path))
    api = create_bridge_api(session)
    api.start_scan()
    _scan_until_idle(api)
    dup_page = api.query_review_rows({"viewMode": "action", "limit": 50})
    file_rows = [
        r
        for r in dup_page["rows"]
        if r.get("rowKind") == "file" and r.get("proposedAction") == "move_duplicate"
    ]
    if len(file_rows) < 1:
        return
    api.get_move_preview({"type": "explicit_rows", "rowIds": [file_rows[0]["id"]]})
    enc_row = _encoding_issue_row(api)
    with pytest.raises(RepairPreviewError) as exc_info:
        api.get_quality_repair_preview({"issueIds": [enc_row["id"]]})
    assert exc_info.value.reason == "MOVE_PREVIEW_ACTIVE"


def test_quality_repair_stale_file_drift(tmp_path: Path) -> None:
    path = tmp_path / "korean.txt"
    path.write_bytes("안녕".encode("cp949"))
    session = create_library_session(MemoryLibraryIndex())
    session.select_folder(str(tmp_path))
    api = create_bridge_api(session)
    api.start_scan()
    _scan_until_idle(api)
    row = _encoding_issue_row(api)
    preview = api.get_quality_repair_preview({"issueIds": [row["id"]]})
    path.write_bytes(b"changed-by-user")
    with pytest.raises(RepairApplyError) as exc_info:
        api.apply_quality_repair(
            {"issueIds": [row["id"]], "repairPreviewToken": preview["repairPreviewToken"]}
        )
    assert exc_info.value.reason == "STALE_REPAIR_PREVIEW"
    assert "changed-by-user" in path.read_bytes().decode("latin-1")


def test_preview_finalize_cleanup_lists_empty_dirs(tmp_path: Path) -> None:
    (tmp_path / "duplicate" / "empty-slot").mkdir(parents=True)
    (tmp_path / "organized" / "empty-slot").mkdir(parents=True)
    (tmp_path / "solo.txt").write_text("hello", encoding="utf-8")
    session = create_library_session(MemoryLibraryIndex())
    session.select_folder(str(tmp_path))
    api = create_bridge_api(session)
    api.start_scan()
    _scan_until_idle(api)
    preview = api.preview_finalize_cleanup()
    assert "previewedEmptyDirs" in preview
    assert "duplicate/empty-slot" in preview["previewedEmptyDirs"]
    assert "organized/empty-slot" in preview["previewedEmptyDirs"]


def test_get_finalize_summary_requires_library() -> None:
    api = _memory_api()
    with pytest.raises(FinalizeError) as exc_info:
        api.get_finalize_summary()
    assert exc_info.value.reason == "NO_LIBRARY"


def test_get_finalize_summary_after_scan(tmp_path: Path) -> None:
    (tmp_path / "solo.txt").write_text("hello", encoding="utf-8")
    session = create_library_session(MemoryLibraryIndex())
    session.select_folder(str(tmp_path))
    api = create_bridge_api(session)
    api.start_scan()
    _scan_until_idle(api)
    summary = api.get_finalize_summary()
    validate_finalize_summary(summary)
    assert summary["resolve"]["exactUnresolvedQueueCount"] == 0
    assert summary["scanState"] == "success"


def test_finalize_complete_clean_library(tmp_path: Path) -> None:
    (tmp_path / "solo.txt").write_text("hello", encoding="utf-8")
    session = create_library_session(MemoryLibraryIndex())
    session.select_folder(str(tmp_path))
    api = create_bridge_api(session)
    api.start_scan()
    _scan_until_idle(api)
    result = api.run_finalize_verification({"includeCleanup": False})
    validate_finalize_result(result)
    assert result["status"] in ("complete", "complete_with_warnings")
    assert result["blockers"] == []
    assert result["reportId"]
    assert isinstance(result["cleanup"]["previewedEmptyDirs"], list)


def test_finalize_blocked_exact_duplicate_queue(tmp_path: Path) -> None:
    payload = "same\n"
    (tmp_path / "a.txt").write_text(payload, encoding="utf-8")
    (tmp_path / "b.txt").write_text(payload, encoding="utf-8")
    session = create_library_session(MemoryLibraryIndex())
    session.select_folder(str(tmp_path))
    api = create_bridge_api(session)
    api.start_scan()
    _scan_until_idle(api)
    summary = api.get_finalize_summary()
    assert summary["resolve"]["queueCount"] > 0
    assert summary["resolve"]["exactUnresolvedQueueCount"] > 0
    result = api.run_finalize_verification({"includeCleanup": False})
    assert result["status"] == "blocked"
    assert result["reportId"]
    report = api.get_finalize_report(result["reportId"])
    assert report["status"] == "blocked"


def test_cancel_finalize_idempotent_when_idle() -> None:
    api = _memory_api()
    api.cancel_finalize()
    api.cancel_finalize()


def test_append_files_batch_reset_preserves_other_folder_rows(tmp_path: Path) -> None:
    index = SqliteLibraryIndex(tmp_path / "multi.db")
    folder_a = normalize_library_folder_path(str(tmp_path / "a"))
    folder_b = normalize_library_folder_path(str(tmp_path / "b"))

    def _row(folder: str, name: str) -> FileRecord:
        rel = name
        return FileRecord(
            id=make_file_id(rel, 1, 1),
            relative_path=rel,
            name=name,
            size_bytes=1,
            modified_at_ns=1,
            extension=".txt",
        )

    index.append_files_batch(folder_a, [_row(folder_a, "a.txt")], reset=True)
    index.append_files_batch(folder_b, [_row(folder_b, "b.txt")], reset=True)
    index.activate_library_folder(folder_b)
    assert index.file_count() == 1
    index.append_files_batch(folder_a, [_row(folder_a, "a2.txt")], reset=True)
    index.activate_library_folder(folder_b)
    assert index.file_count() == 1
    assert {f.name for f in index.files()} == {"b.txt"}


def test_run_scan_keeps_busy_until_tail_flush_and_indexes_complete(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from infrastructure.filesystem_scanner import ScanStreamResult

    (tmp_path / "one.txt").write_text("x", encoding="utf-8")
    session = create_library_session(MemoryLibraryIndex())
    session.select_folder(str(tmp_path))
    flush_started = threading.Event()
    release_flush = threading.Event()

    def fast_scan(
        folder_path: str,
        *,
        on_progress,
        cancel_check,
        out,
        extensions=None,
        include_hidden=False,
        on_paths_collected=None,
    ) -> ScanStreamResult:
        _ = (
            folder_path,
            on_progress,
            cancel_check,
            extensions,
            include_hidden,
            on_paths_collected,
        )
        record = FileRecord(
            id=make_file_id("one.txt", 1, 1),
            relative_path="one.txt",
            name="one.txt",
            size_bytes=1,
            modified_at_ns=1,
            extension=".txt",
        )
        out(record)
        return ScanStreamResult(completed=True, cancelled=False, scanned_count=1)

    index = session.index
    original_append = index.append_files_batch

    def tracking_append(folder_path: str, files: list, *, reset: bool = False) -> None:
        original_append(folder_path, files, reset=reset)
        if not flush_started.is_set():
            flush_started.set()
            assert session.is_apply_or_scan_busy()
            release_flush.wait(timeout=5.0)

    monkeypatch.setattr(index, "append_files_batch", tracking_append)
    session._scan_folder = fast_scan  # noqa: SLF001
    api = create_bridge_api(session)
    api.start_scan()
    assert flush_started.wait(timeout=5.0), "tail flush never started"
    assert session.is_apply_or_scan_busy()
    release_flush.set()
    _scan_until_idle(api)


def test_scan_normal_completion_flushes_tail_buffer_even_if_cancel_requested_after_scanner_returns(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from infrastructure.filesystem_scanner import ScanStreamResult

    (tmp_path / "a.txt").write_text("a", encoding="utf-8")
    (tmp_path / "b.txt").write_text("b", encoding="utf-8")
    session = create_library_session(MemoryLibraryIndex())
    session.select_folder(str(tmp_path))
    scan_finished = threading.Event()

    def scan_two(
        folder_path: str,
        *,
        on_progress,
        cancel_check,
        out,
        extensions=None,
        include_hidden=False,
        on_paths_collected=None,
    ) -> ScanStreamResult:
        _ = (
            folder_path,
            on_progress,
            cancel_check,
            extensions,
            include_hidden,
            on_paths_collected,
        )
        for name in ("a.txt", "b.txt"):
            out(
                FileRecord(
                    id=make_file_id(name, 1, 1),
                    relative_path=name,
                    name=name,
                    size_bytes=1,
                    modified_at_ns=1,
                    extension=".txt",
                )
            )
        scan_finished.set()
        return ScanStreamResult(completed=True, cancelled=False, scanned_count=2)

    session._scan_folder = scan_two  # noqa: SLF001
    api = create_bridge_api(session)
    api.start_scan()
    assert scan_finished.wait(timeout=5.0)
    api.cancel_run()
    _scan_until_idle(api)
    assert api.get_snapshot()["library"]["fileCount"] == 2


def test_post_scan_exception_is_exposed_in_snapshot(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    import application.library_session as library_session_module

    (tmp_path / "one.txt").write_text("x", encoding="utf-8")
    session = create_library_session(MemoryLibraryIndex())
    session.select_folder(str(tmp_path))
    api = create_bridge_api(session)

    def boom(files: list[FileRecord]) -> list:
        raise RuntimeError("post-scan boom")

    monkeypatch.setattr(library_session_module, "find_exact_duplicate_groups", boom)
    api.start_scan()
    snap = _scan_until_idle(api)
    assert snap["work"]["scan"]["deepAnalysisStatus"] == "error"
    assert snap["work"]["scan"]["deepAnalysisComplete"] is False
    assert "post-scan boom" in (snap["work"]["scan"]["deepAnalysisError"] or "")


def test_finalize_while_scan_raises_library_busy(tmp_path: Path) -> None:
    (tmp_path / "solo.txt").write_text("x", encoding="utf-8")
    session = create_library_session(MemoryLibraryIndex())
    session.select_folder(str(tmp_path))
    api = create_bridge_api(session)
    api.start_scan()
    with pytest.raises(FinalizeError) as exc_info:
        api.run_finalize_verification({"includeCleanup": False})
    assert exc_info.value.reason == "LIBRARY_BUSY"


def test_query_review_rows_available_while_background_analysis(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    import application.library_session as library_session_module
    import application.scan_pipeline_constants as scan_constants

    monkeypatch.setattr(scan_constants, "SCAN_DEEP_ANALYSIS_BACKGROUND_THRESHOLD", 2)
    monkeypatch.setattr(scan_constants, "SCAN_NEAR_FAST_LIBRARY_THRESHOLD", 2)
    for i in range(4):
        (tmp_path / f"f{i}.txt").write_text(f"body-{i}\n", encoding="utf-8")

    relation_started = threading.Event()
    release_relation = threading.Event()
    original_relation = library_session_module.LibrarySession._run_relation_phase

    def slow_relation(self, folder: str, files: list[FileRecord]) -> None:
        relation_started.set()
        release_relation.wait(timeout=5.0)
        original_relation(self, folder, files)

    monkeypatch.setattr(
        library_session_module.LibrarySession,
        "_run_relation_phase",
        slow_relation,
    )

    session = create_library_session(SqliteLibraryIndex(tmp_path / "idx.db"))
    session.select_folder(str(tmp_path))
    api = create_bridge_api(session)
    api.start_scan()

    deadline = time.monotonic() + 5.0
    while time.monotonic() < deadline:
        snap = api.get_snapshot()
        if snap["work"]["scan"]["indexReady"] and relation_started.is_set():
            break
        time.sleep(0.05)
    else:
        pytest.fail("indexReady + relation phase start not reached")

    page = api.query_review_rows({"viewMode": "all", "limit": 50})
    validate_review_rows_page(page)

    release_relation.set()
    _scan_until_idle(api)
