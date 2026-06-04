#!/usr/bin/env python3
"""Migrate docs/agent/KANBAN.yml cards to Kanban Markdown (.devtool/features/)."""

from __future__ import annotations

import argparse
import re
from datetime import UTC, datetime
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
KANBAN_YML = ROOT / "docs" / "agent" / "KANBAN.yml"
FEATURES_DIR = ROOT / ".devtool" / "features"
NOW_ISO = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.000Z")
TODAY = datetime.now(UTC).strftime("%Y-%m-%d")

# Legacy KANBAN.full.yml column -> NovelGuard board status (see .vscode/settings.json)
COLUMN_TO_STATUS = {
    "proposed": "todo",
    "ready": "ready",
    "in_progress": "in-progress",
    "done": "done",
    "cancelled": "blocked",
}

COLUMN_ORDER = ["proposed", "ready", "in_progress", "done", "cancelled"]


def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[`'\"]+", "", text)
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")[:60] or "card"


def card_priority(column: str, card: dict) -> str:
    if column == "in_progress":
        return "high"
    if column == "proposed":
        return "medium"
    if column == "ready":
        return "medium"
    if column == "cancelled":
        return "low"
    return "low"


def build_labels(card: dict) -> list[str]:
    labels: list[str] = ["roadmap-pr"]
    track = card.get("track")
    if track:
        labels.append(f"track-{track}")
    wave = card.get("wave")
    if wave:
        labels.append(f"wave-{slugify(str(wave))}")
    mutation = card.get("mutation")
    if mutation:
        labels.append("mutation")
    return labels


def normalize_doc_link(value: str) -> str:
    """Make spec/plan paths clickable from .devtool/features/<status>/."""
    prefix = "../../../docs/superpowers/"
    for token in ("`specs/", "`plans/", "(../specs/", "(specs/", "(../plans/", "(plans/"):
        if token in value:
            repl = token.replace("specs/", f"{prefix}specs/").replace("plans/", f"{prefix}plans/")
            value = value.replace(token, repl)
    if value.startswith("docs/superpowers/"):
        return value.replace("docs/superpowers/", prefix, 1)
    return value


def format_links(card: dict) -> str:
    rows: list[str] = []
    for key in ("track", "wave", "spec", "plan", "branch", "mutation", "note"):
        val = card.get(key)
        if val:
            if key in ("spec", "plan"):
                val = normalize_doc_link(str(val))
            rows.append(f"| **{key.replace('_', ' ').title()}** | {val} |")
    if not rows:
        return ""
    header = "| Field | Value |\n|-------|-------|\n"
    return header + "\n".join(rows) + "\n"


def card_filename(card_id: str, title: str) -> str:
    base = slugify(f"{card_id}-{title}")
    return f"{base}-{TODAY}.md"


def render_card(card: dict, *, status: str, order: int) -> str:
    card_id = str(card["id"])
    title = str(card.get("title", card_id))
    priority = card_priority(card.get("column", ""), card)
    labels = build_labels(card)
    body_links = format_links(card)

    frontmatter = {
        "id": slugify(f"{card_id}-{TODAY}"),
        "status": status,
        "priority": priority,
        "assignee": "",
        "dueDate": "",
        "created": NOW_ISO,
        "modified": NOW_ISO,
        "labels": labels,
        "order": order,
    }
    yaml_block = yaml.safe_dump(
        frontmatter, sort_keys=False, allow_unicode=True
    ).strip()

    lines = [
        "---",
        yaml_block,
        "---",
        "",
        f"# {card_id} — {title}",
        "",
    ]
    if body_links:
        lines.append(body_links)
    return "\n".join(lines)


def load_kanban(path: Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected mapping in {path}")
    return data


def group_cards_by_column(cards: list[dict]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {c: [] for c in COLUMN_ORDER}
    for card in cards:
        column = str(card.get("column", "proposed"))
        if column not in grouped:
            grouped[column] = []
        grouped[column].append(card)
    return grouped


def write_features(cards: list[dict], *, dry_run: bool) -> list[Path]:
    written: list[Path] = []
    grouped = group_cards_by_column(cards)

    for column in COLUMN_ORDER:
        status = COLUMN_TO_STATUS[column]
        status_dir = FEATURES_DIR / status
        if not dry_run:
            status_dir.mkdir(parents=True, exist_ok=True)

        for order, card in enumerate(grouped.get(column, [])):
            content = render_card(card, status=status, order=order)
            path = status_dir / card_filename(str(card["id"]), str(card.get("title", "")))
            written.append(path)
            if dry_run:
                print(f"would write {path.relative_to(ROOT)}")
            else:
                path.write_text(content, encoding="utf-8")
    return written


def write_meta_stub(data: dict, *, dry_run: bool) -> None:
    meta = data.get("meta") or {}
    stub = {
        "meta": {
            **meta,
            "board": ".devtool/features",
            "board_format": "kanban-markdown",
            "migrated": TODAY,
            "open_board": 'Cmd/Ctrl+Shift+P → "Open Kanban Board"',
        },
        "columns": data.get("columns") or list(COLUMN_TO_STATUS.keys()),
        "note": (
            "PR cards live as markdown under .devtool/features/<status>/. "
            "Regenerate from KANBAN.full.yml via scripts/migrate_roadmap_to_kanban.py "
            "only when bulk-importing; day-to-day status moves happen in the Kanban board."
        ),
    }
    out = ROOT / "docs" / "agent" / "KANBAN.yml"
    text = (
        "# Roadmap PR kanban — Kanban Markdown (source of truth for card status).\n"
        "# Cards: .devtool/features/<status>/*.md — open with Kanban Markdown extension.\n"
        "# Scope / narrative: docs/superpowers/roadmap/<track>-*.md\n"
        "# Non-roadmap tickets: docs/agent/BACKLOG.yml\n"
        "# Full YAML card export (archive): docs/agent/KANBAN.full.yml\n\n"
        + yaml.safe_dump(stub, sort_keys=False, allow_unicode=True)
    )
    if dry_run:
        print(f"would write {out.relative_to(ROOT)} (meta stub)")
    else:
        out.write_text(text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run", action="store_true", help="Print paths only, do not write files"
    )
    parser.add_argument(
        "--keep-full",
        action="store_true",
        help="Skip archiving KANBAN.yml to KANBAN.full.yml (already archived)",
    )
    args = parser.parse_args()

    if not KANBAN_YML.exists():
        raise SystemExit(f"Missing {KANBAN_YML}")

    data = load_kanban(KANBAN_YML)
    cards = data.get("cards") or []
    if not cards:
        raise SystemExit(
            "No cards in KANBAN.yml — if already migrated, edit .devtool/features/ directly."
        )

    full_archive = ROOT / "docs" / "agent" / "KANBAN.full.yml"
    if not args.keep_full and not args.dry_run and not full_archive.exists():
        full_archive.write_text(KANBAN_YML.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"archived → {full_archive.relative_to(ROOT)}")

    if not args.dry_run and FEATURES_DIR.exists():
        import shutil

        shutil.rmtree(FEATURES_DIR)

    paths = write_features(cards, dry_run=args.dry_run)
    write_meta_stub(data, dry_run=args.dry_run)
    print(f"{'would migrate' if args.dry_run else 'migrated'} {len(paths)} cards → .devtool/features/")


if __name__ == "__main__":
    main()
