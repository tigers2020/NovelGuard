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
    validate_review_rows_page,
    validate_selection_scope,
)
from app.selection_fingerprint import selection_fingerprint
from app.session_factory import create_library_session
from application.library_session import LibrarySession
from domain.models import FileRecord, make_file_id
from infrastructure import filesystem_scanner
from infrastructure.memory_library_index import MemoryLibraryIndex
from tests.fixtures.bridge_contract_fixtures import VALID_SNAPSHOT


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


def test_bridge_api_get_snapshot_valid() -> None:
    api = BridgeApi()
    snap = api.get_snapshot()
    validate_app_snapshot(snap)


def test_bridge_api_query_review_rows_valid() -> None:
    api = BridgeApi()
    page = api.query_review_rows({"viewMode": "action", "limit": 50})
    assert len(page["rows"]) <= 200


def test_bridge_api_get_move_preview_requires_selection() -> None:
    api = BridgeApi()
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
    api = BridgeApi()
    with pytest.raises(PreviewApplyError) as exc:
        api.apply_resolved_actions(
            {"selection": {"type": "explicit_rows", "rowIds": ["row-1"]}, "previewToken": ""}
        )
    assert exc.value.reason == "MISSING_PREVIEW_TOKEN"


def test_apply_after_discard_raises_no_pending() -> None:
    api = BridgeApi()
    sel = {"type": "explicit_rows", "rowIds": ["row-1"]}
    preview = api.get_move_preview(sel)
    api.discard_move_preview({"previewToken": preview["previewToken"]})
    with pytest.raises(PreviewApplyError) as exc:
        api.apply_resolved_actions({"selection": sel, "previewToken": preview["previewToken"]})
    assert exc.value.reason == "NO_PENDING_APPLY"


def test_discard_idempotent_on_mismatch() -> None:
    api = BridgeApi()
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
    api = BridgeApi()
    page = api.query_review_rows({"viewMode": "action", "limit": 50})
    assert page["rows"] == []
    validate_review_rows_page(page)


def test_bridge_api_scan_populates_file_count(tmp_path: Path) -> None:
    (tmp_path / "one.txt").write_text("a", encoding="utf-8")
    (tmp_path / "two.txt").write_text("b", encoding="utf-8")
    session = create_library_session()
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
