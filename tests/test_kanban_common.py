"""Unit tests for scripts/kanban/kanban_common.py (pure helpers)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_KANBAN_COMMON = _REPO_ROOT / "scripts" / "kanban" / "kanban_common.py"


def _load_kanban_common():
    spec = importlib.util.spec_from_file_location("kanban_common", _KANBAN_COMMON)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["kanban_common"] = module
    spec.loader.exec_module(module)
    return module


kc = _load_kanban_common()


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("inbox", "inbox"),
        ("In Progress", "in-progress"),
        ("ready", "ready-gate"),
        ("triage", "inbox"),
        ("", ""),
    ],
)
def test_normalize_column(raw: str, expected: str) -> None:
    assert kc.normalize_column(raw) == expected


@pytest.mark.parametrize(
    ("raw", "parent", "expected"),
    [
        ("scheduled", "", "scheduled"),
        ("", "todo", "todo"),
        ("in_progress", "", "in-progress"),
    ],
)
def test_normalize_status(raw: str, parent: str, expected: str) -> None:
    assert kc.normalize_status(raw, parent) == expected


def test_slugify_truncates() -> None:
    assert kc.slugify("Hello World!", max_len=5) == "hello"


def test_strip_work_id_stage_suffix() -> None:
    assert kc.strip_work_id_stage_suffix("pr-58-exact-keeper-move-2026-06-04-spec-draft") == (
        "pr-58-exact-keeper-move-2026-06-04"
    )


def test_split_and_render_frontmatter_roundtrip() -> None:
    body = "# Title\n\n## Scope\n\nDone.\n"
    meta = {
        "id": "work-inbox",
        "status": "inbox",
        "labels": ["feature", "track-1"],
        "approved": True,
        "notes": None,
    }
    rendered = kc.render_frontmatter(meta, body)
    parsed_meta, parsed_body = kc.split_frontmatter(rendered)
    assert parsed_meta["id"] == "work-inbox"
    assert parsed_meta["labels"] == ["feature", "track-1"]
    assert parsed_meta["approved"] is True
    assert parsed_meta["notes"] is None
    assert parsed_body.strip().startswith("# Title")


def test_safe_read_card_missing(tmp_path: Path) -> None:
    assert kc.safe_read_card(tmp_path / "missing.md") is None


def test_safe_read_card_reads_valid_card(tmp_path: Path) -> None:
    path = tmp_path / "ok.md"
    path.write_text(
        kc.render_frontmatter({"id": "x-inbox", "status": "inbox"}, "# X\n"),
        encoding="utf-8",
    )
    meta, body = kc.safe_read_card(path) or ({}, "")
    assert meta.get("status") == "inbox"
    assert "# X" in body


def test_fix_card_doc_links() -> None:
    text = "See `specs/foo.md` and (plans/bar.md)"
    fixed = kc.fix_card_doc_links(text)
    assert kc.DOCS_SUPERPOWERS_PREFIX in fixed
    assert "`specs/" not in fixed
