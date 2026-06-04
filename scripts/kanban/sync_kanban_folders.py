#!/usr/bin/env python3
"""Sync kanban card files for the Kanban Markdown VS Code extension."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_KANBAN_DIR = Path(__file__).resolve().parent
if str(_KANBAN_DIR) not in sys.path:
    sys.path.insert(0, str(_KANBAN_DIR))

from kanban_common import (  # noqa: E402
    FEATURES_DIR,
    ROOT,
    WORKFLOW_COLUMNS,
    normalize_status,
    render_frontmatter,
    safe_read_card,
)


def target_dir_for(status: str) -> Path:
    if status == "done":
        path = FEATURES_DIR / "done"
        path.mkdir(parents=True, exist_ok=True)
        return path
    return FEATURES_DIR


def _read_card_or_log(path: Path, logs: list[str]) -> tuple[dict, str] | None:
    parsed = safe_read_card(path)
    if parsed is None:
        logs.append(f"skip unreadable {path.relative_to(ROOT)}")
    return parsed


def _sync_one_card(path: Path, *, dry_run: bool) -> list[str]:
    logs: list[str] = []
    card = _read_card_or_log(path, logs)
    if card is None:
        return logs
    meta, body = card
    parent = path.parent.name
    raw_status = str(meta.get("status", parent if parent in WORKFLOW_COLUMNS else "inbox"))
    status = normalize_status(raw_status, parent)
    text_before = path.read_text(encoding="utf-8") if path.exists() else ""
    if meta.get("status") != status:
        meta["status"] = status
    rendered = render_frontmatter(meta, body)

    target = target_dir_for(status) / path.name
    if path.resolve() != target.resolve():
        rel_old = path.relative_to(ROOT)
        rel_new = target.relative_to(ROOT)
        if not dry_run:
            target.write_text(rendered, encoding="utf-8")
            path.unlink()
        logs.append(f"{rel_old} -> {rel_new} (status={status})")
    elif rendered != text_before:
        if not dry_run:
            path.write_text(rendered, encoding="utf-8")
        logs.append(f"{path.relative_to(ROOT)} (status -> {status})")
    return logs


def _cleanup_empty_workflow_dirs() -> list[str]:
    logs: list[str] = []
    for child in sorted(FEATURES_DIR.iterdir()):
        if (
            child.is_dir()
            and child.name in WORKFLOW_COLUMNS
            and child.name != "done"
            and not any(child.glob("*.md"))
        ):
            child.rmdir()
            logs.append(f"removed empty {child.relative_to(ROOT)}/")
    return logs


def _bundle_done_cards_if_needed() -> None:
    done_dir = FEATURES_DIR / "done"
    if done_dir.is_dir() and any(done_dir.glob("*.md")):
        from bundle_done_kanban_cards import bundle_done_dir

        bundle_done_dir(done_dir, dry_run=False)


def sync_board(*, dry_run: bool = False) -> list[str]:
    """Flatten cards to board-visible paths. Returns human-readable change lines."""
    logs: list[str] = []
    for path in sorted(FEATURES_DIR.rglob("*.md")):
        logs.extend(_sync_one_card(path, dry_run=dry_run))
    if not dry_run:
        logs.extend(_cleanup_empty_workflow_dirs())
        _bundle_done_cards_if_needed()
    return logs


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Flatten Kanban cards to .devtool/features/*.md (status in frontmatter)."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print moves without writing files or bundling done cards",
    )
    args = parser.parse_args(argv)
    lines = sync_board(dry_run=args.dry_run)
    for line in lines:
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
