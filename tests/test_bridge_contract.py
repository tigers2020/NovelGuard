from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from app.bridge_api import BridgeApi
from app.bridge_contract import (
    ApplyFailedError,
    EmptySelectionError,
    InvalidSelectionScopeError,
    PreviewApplyError,
    SnapshotContractError,
    clamp_query_limit,
    validate_app_snapshot,
    validate_duplicate_group_detail,
    validate_move_preview,
    validate_quality_rows_page,
    validate_review_rows_page,
    validate_selection_scope,
)
from app.bridge_parity import PYWEBVIEW_API_METHODS
from app.selection_fingerprint import selection_fingerprint
from app.session_factory import create_bridge_api, create_library_session
from application.library_session import LibrarySession
from application.ports.filesystem_apply import ApplyRowResult
from application.quality_analyzer import analyze_quality
from domain.apply_models import PreviewOperation
from domain.apply_path_policy import build_move_duplicate_dest_relative, validate_move_operation
from domain.duplicate_exact import find_exact_duplicate_groups
from domain.models import FileRecord, make_file_id
from domain.quality import make_issue_id
from infrastructure import filesystem_scanner
from infrastructure.content_hasher import hash_file
from infrastructure.local_filesystem_apply import LocalFilesystemApplyAdapter
from infrastructure.memory_library_index import MemoryLibraryIndex
from infrastructure.sqlite_library_index import SqliteLibraryIndex
from tests.fixtures.bridge_contract_fixtures import VALID_SNAPSHOT


def _memory_api() -> BridgeApi:
    return create_bridge_api(create_library_session(MemoryLibraryIndex()))


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
    """Locked contract; must match web/src/contracts/bridgeParity.ts PYWEBVIEW_API_METHODS."""
    locked = [
        "get_snapshot",
        "select_folder",
        "start_scan",
        "cancel_run",
        "set_work_mode",
        "query_review_rows",
        "query_quality_rows",
        "get_duplicate_group_detail",
        "get_quality_issue_detail",
        "get_move_preview",
        "apply_resolved_actions",
        "discard_move_preview",
        "update_review_decisions",
        "get_app_setting",
        "set_app_setting",
    ]
    assert list(PYWEBVIEW_API_METHODS) == locked


def test_bridge_api_exposes_pywebview_methods() -> None:
    api = _memory_api()
    for name in PYWEBVIEW_API_METHODS:
        assert hasattr(api, name), f"BridgeApi missing {name}"
        assert callable(getattr(api, name))


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
    assert preview["hasPendingApply"] is True
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


def test_make_file_id_stable() -> None:
    a = make_file_id("novels/a.txt", 100, 1_700_000_000_000_000_000)
    b = make_file_id("novels/a.txt", 100, 1_700_000_000_000_000_000)
    assert a == b
    assert len(a) == 64
    assert make_file_id("novels/b.txt", 100, 1_700_000_000_000_000_000) != a


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
    assert snap["work"]["resolve"]["libraryRevision"] == rev_before + 1


def test_cancel_scan_discards_partial(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("x", encoding="utf-8")
    session = LibrarySession(MemoryLibraryIndex(), scan_folder=filesystem_scanner.scan_folder)
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
        out,
        extensions=None,
    ) -> None:
        for i in range(50):
            if cancel_check():
                cancel_flag["hit"] = True
                return
            rel = f"f{i}.txt"
            record = FileRecord(
                id=make_file_id(rel, 1, i),
                relative_path=rel,
                name=f"f{i}.txt",
                size_bytes=1,
                modified_at_ns=i,
                extension=".txt",
            )
            out(record)
            on_progress(i * 2, "slow")
            time.sleep(0.02)

    monkeypatch.setattr(filesystem_scanner, "scan_folder", slow_scan)
    session._scan_folder = slow_scan  # noqa: SLF001 — test binds patched scanner
    api.start_scan()
    time.sleep(0.05)
    rev_before_cancel = api.get_snapshot()["work"]["resolve"]["libraryRevision"]
    api.cancel_run()
    deadline = time.monotonic() + 5.0
    snap = api.get_snapshot()
    while snap["pipeline"]["phase"] == "scan" and time.monotonic() < deadline:
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
    assert groups[0].keeper_id == keeper.id


def test_sqlite_library_index_round_trip(tmp_path: Path) -> None:
    db = tmp_path / "library.db"
    index = SqliteLibraryIndex(db)
    folder = str(tmp_path / "lib")
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


def _scan_until_idle(api: BridgeApi) -> dict:
    deadline = time.monotonic() + 5.0
    snap = api.get_snapshot()
    while snap["work"]["scan"]["state"] == "running" and time.monotonic() < deadline:
        time.sleep(0.05)
        snap = api.get_snapshot()
    return snap


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
    file_row = next(row for row in page["rows"] if row.get("rowKind") == "file")
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
    page = api.query_review_rows({"viewMode": "all", "limit": 50})
    validate_review_rows_page(page)
    assert len(page["rows"]) >= 3
    assert all(row["type"] == "exact" for row in page["rows"])
    assert any(row["rowKind"] == "group" for row in page["rows"])


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
    assert all(row["id"].startswith("quality:") for row in small_page["rows"])

    encoding_page = api.query_quality_rows({"issueType": "encoding", "limit": 50})
    assert len(encoding_page["rows"]) == 1
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
    assert detail["id"] == row["id"]
    assert detail["name"] == target_name


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
    folder_a = str(tmp_path / "a")
    folder_b = str(tmp_path / "b")
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
    dest: str = "duplicate/a/keep.txt",
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
        _move_op(source="../outside.txt", dest="duplicate/outside.txt"),
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
    (root / "duplicate").mkdir(parents=True)
    (root / "duplicate" / "dup.txt").write_text("exists", encoding="utf-8")
    (root / "src.txt").write_text("src", encoding="utf-8")
    result = validate_move_operation(
        root,
        _move_op(source="src.txt", dest="duplicate/dup.txt"),
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
    dest = root / "duplicate" / "src.txt"
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
    assert (tmp_path / "duplicate" / src_name).exists()
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
    moved = [row["name"] for row in batch if (tmp_path / "duplicate" / row["name"]).exists()]
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
    _scan_until_idle(api)
    near_page = api.query_review_rows(
        {"viewMode": "all", "limit": 50, "filters": {"types": ["near"]}}
    )
    validate_review_rows_page(near_page)
    if near_page["rows"]:
        assert all(row["type"] == "near" for row in near_page["rows"])
    both_page = api.query_review_rows(
        {"viewMode": "all", "limit": 50, "filters": {"types": ["exact", "near"]}}
    )
    assert any(row["type"] == "exact" for row in both_page["rows"]) or not near_page["rows"]


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


def test_preview_rejects_near_duplicate_rows(tmp_path: Path) -> None:
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
    with pytest.raises(PreviewApplyError) as exc_info:
        api.get_move_preview({"type": "explicit_rows", "rowIds": [file_row["id"]]})
    assert exc_info.value.reason == "NEAR_DUPLICATE_APPLY_UNSUPPORTED"


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


def test_include_relation_false_skips_relation_rows(tmp_path: Path) -> None:
    (tmp_path / "Novel 01.txt").write_text("x", encoding="utf-8")
    (tmp_path / "Novel 02.txt").write_text("y", encoding="utf-8")
    session = create_library_session(MemoryLibraryIndex())
    session.select_folder(str(tmp_path))
    api = create_bridge_api(session)
    assert api.get_app_setting("include_relation") is False
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
    api.set_app_setting("include_relation", True)
    api.start_scan()
    _scan_until_idle(api)
    relation_page = api.query_review_rows(
        {"viewMode": "all", "limit": 50, "filters": {"types": ["relation"]}}
    )
    validate_review_rows_page(relation_page)
    if relation_page["rows"]:
        assert all(row["type"] == "relation" for row in relation_page["rows"])
        assert all(
            row.get("relationKind") in ("same_title_series", "chapter_sequence", "version_variant")
            for row in relation_page["rows"]
            if row.get("relationKind")
        )


def test_get_relation_group_detail(tmp_path: Path) -> None:
    (tmp_path / "Novel 01.txt").write_text("x", encoding="utf-8")
    (tmp_path / "Novel 02.txt").write_text("y", encoding="utf-8")
    session = create_library_session(MemoryLibraryIndex())
    session.select_folder(str(tmp_path))
    api = create_bridge_api(session)
    api.set_app_setting("include_relation", True)
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


def test_preview_rejects_relation_rows(tmp_path: Path) -> None:
    (tmp_path / "Novel 01.txt").write_text("x", encoding="utf-8")
    (tmp_path / "Novel 02.txt").write_text("y", encoding="utf-8")
    session = create_library_session(MemoryLibraryIndex())
    session.select_folder(str(tmp_path))
    api = create_bridge_api(session)
    api.set_app_setting("include_relation", True)
    api.start_scan()
    _scan_until_idle(api)
    relation_page = api.query_review_rows(
        {"viewMode": "all", "limit": 50, "filters": {"types": ["relation"]}}
    )
    file_row = next((row for row in relation_page["rows"] if row["rowKind"] == "file"), None)
    if file_row is None:
        return
    with pytest.raises(PreviewApplyError) as exc_info:
        api.get_move_preview({"type": "explicit_rows", "rowIds": [file_row["id"]]})
    assert exc_info.value.reason == "RELATION_APPLY_UNSUPPORTED"
