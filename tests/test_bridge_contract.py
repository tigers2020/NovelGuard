from __future__ import annotations

import time
from pathlib import Path

import pytest

from app.bridge_api import BridgeApi
from app.bridge_contract import (
    EmptySelectionError,
    InvalidSelectionScopeError,
    PreviewApplyError,
    SnapshotContractError,
    clamp_query_limit,
    validate_app_snapshot,
    validate_quality_rows_page,
    validate_review_rows_page,
    validate_selection_scope,
)
from app.bridge_parity import PYWEBVIEW_API_METHODS
from app.selection_fingerprint import selection_fingerprint
from app.session_factory import create_library_session
from application.library_session import LibrarySession
from application.quality_analyzer import analyze_quality
from domain.duplicate_exact import find_exact_duplicate_groups
from domain.models import FileRecord, make_file_id
from domain.quality import make_issue_id
from infrastructure import filesystem_scanner
from infrastructure.content_hasher import hash_file
from infrastructure.memory_library_index import MemoryLibraryIndex
from infrastructure.sqlite_library_index import SqliteLibraryIndex
from tests.fixtures.bridge_contract_fixtures import VALID_SNAPSHOT


def _memory_api() -> BridgeApi:
    return BridgeApi(create_library_session(MemoryLibraryIndex()))


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
    api = BridgeApi(session)
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
    api = BridgeApi(session)
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


def test_query_review_rows_exact_duplicate_pair(tmp_path: Path) -> None:
    payload = "same story content\n"
    (tmp_path / "copy_a.txt").write_text(payload, encoding="utf-8")
    (tmp_path / "copy_b.txt").write_text(payload, encoding="utf-8")
    session = create_library_session(MemoryLibraryIndex())
    session.select_folder(str(tmp_path))
    api = BridgeApi(session)
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
    api = BridgeApi(session)
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
    api = BridgeApi(session)
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
    api = BridgeApi(session)
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
    api = BridgeApi(session)
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
    api = BridgeApi(session)
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
    api = BridgeApi(session)
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
    api = BridgeApi(session)
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
