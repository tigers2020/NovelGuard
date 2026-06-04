#!/usr/bin/env python3
"""Migrate kanban cards from v1 columns to v2 event-pipeline columns.

v1: triage, spec, plan, todo, scheduled, ready, in-progress, review, done, blocked
v2: inbox, spec-draft, spec-review, plan-draft, plan-review, todo, scheduled,
    ready-gate, in-progress, verify, done, blocked

Usage:
  python scripts/kanban/migrate_kanban_columns_v2.py --dry-run
  python scripts/kanban/migrate_kanban_columns_v2.py
  python scripts/kanban/sync_kanban_folders.py
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

_KANBAN_DIR = Path(__file__).resolve().parent
if str(_KANBAN_DIR) not in sys.path:
    sys.path.insert(0, str(_KANBAN_DIR))

from kanban_common import (  # noqa: E402
    COLUMN_ALIASES,
    FEATURES_DIR,
    ROOT,
    read_card,
    render_frontmatter,
)

# v1 status -> v2 status (simple mapping; spec/plan use approval heuristics)
SIMPLE_MAP: dict[str, str] = {
    key: value
    for key, value in COLUMN_ALIASES.items()
    if key
    not in (
        "spec-draft",
        "spec-review",
        "plan-draft",
        "plan-review",
        "ready-gate",
        "in-progress",
        "inbox",
        "todo",
        "scheduled",
        "verify",
        "done",
        "blocked",
    )
}

# filename suffix replacements (order matters — longer first)
SUFFIX_MAP: list[tuple[str, str]] = [
    ("-ready-gate", "-ready-gate"),  # idempotent
    ("-spec-review", "-spec-review"),
    ("-spec-draft", "-spec-draft"),
    ("-plan-review", "-plan-review"),
    ("-plan-draft", "-plan-draft"),
    ("-in-progress", "-in-progress"),
    ("-scheduled", "-scheduled"),
    ("-triage", "-inbox"),
    ("-ready", "-ready-gate"),
    ("-review", "-verify"),
    ("-spec", "-spec-review"),  # default; may override below
    ("-plan", "-plan-review"),  # default; may override below
]

BODY_REPLACEMENTS: list[tuple[str, str]] = [
    ("status: triage", "status: inbox"),
    ("status: ready", "status: ready-gate"),
    ("status: review", "status: verify"),
    ("→ **ready**", "→ **ready-gate**"),
    ("→ **review**", "→ **verify**"),
    ("→ **triage**", "→ **inbox**"),
    ("at **triage**", "at **inbox**"),
    ("at **ready**", "at **ready-gate**"),
    ("at **review**", "at **verify**"),
    ("**Ready**", "**Ready Gate**"),
    ("[Ready]", "[Ready Gate]"),
    ("# [Ready]", "# [Ready Gate]"),
    ("# [Review]", "# [Verify]"),
    ("# [Triage]", "# [Inbox]"),
    ("# [Spec]", "# [Spec Review]"),
    ("# [Plan]", "# [Plan Review]"),
    ("| **Triage** |", "| **Inbox** |"),
    ("move card to **done**", "move card to **done**"),
]


def has_approval(meta: dict, body: str, kind: str) -> bool:
    flag = f"{kind}_approved"
    if meta.get(flag) is True:
        return True
    if meta.get("status") == f"{kind}-review":
        return True
    patterns = [
        r"\*\*Approved\*\*",
        rf"{kind} approved ✓",
        rf"\[{kind} card\].*approved ✓",
        r"approved ✓",
        r"status: approved",
    ]
    combined = body.lower()
    return any(re.search(p, combined, re.IGNORECASE) for p in patterns)


def map_status(raw: str, meta: dict, body: str) -> str:
    key = raw.strip().lower().replace("_", "-")
    if key in ("spec", "spec-draft", "spec-review"):
        if key == "spec-review" or has_approval(meta, body, "spec"):
            return "spec-review"
        return "spec-draft"
    if key in ("plan", "plan-draft", "plan-review"):
        if key == "plan-review" or has_approval(meta, body, "plan"):
            return "plan-review"
        return "plan-draft"
    return SIMPLE_MAP.get(key, COLUMN_ALIASES.get(key, key))


def map_filename(name: str, new_status: str) -> str:
    stem = name
    if stem.endswith(".md"):
        stem = stem[:-3]

    status_suffixes = {
        "inbox": "-inbox",
        "spec-draft": "-spec-draft",
        "spec-review": "-spec-review",
        "plan-draft": "-plan-draft",
        "plan-review": "-plan-review",
        "todo": "-todo",
        "scheduled": "-scheduled",
        "ready-gate": "-ready-gate",
        "in-progress": "-in-progress",
        "verify": "-verify",
        "blocked": "-blocked",
    }

    for old, new in SUFFIX_MAP:
        if stem.endswith(old):
            stem = stem[: -len(old)]
            break

    suffix = status_suffixes.get(new_status, "")
    if suffix and not stem.endswith(suffix):
        return f"{stem}{suffix}.md"
    return f"{stem}.md" if name.endswith(".md") else name


def update_body_links(body: str, old_name: str, new_name: str) -> str:
    if old_name == new_name:
        updated = body
    else:
        updated = body.replace(old_name, new_name)
        old_stem = old_name.removesuffix(".md")
        new_stem = new_name.removesuffix(".md")
        updated = updated.replace(old_stem, new_stem)
    for old, new in BODY_REPLACEMENTS:
        updated = updated.replace(old, new)
    return updated


def migrate_card(path: Path, *, dry_run: bool) -> list[str]:
    logs: list[str] = []
    text = path.read_text(encoding="utf-8")
    meta, body = read_card(path)
    raw_status = str(meta.get("status", path.parent.name if path.parent.name != "features" else "inbox"))
    new_status = map_status(raw_status, meta, body)
    new_name = map_filename(path.name, new_status)
    new_body = update_body_links(body, path.name, new_name)
    meta["status"] = new_status

    if new_status in ("spec-review",) and meta.get("spec_approved") is None and has_approval(meta, new_body, "spec"):
        meta["spec_approved"] = True
    if new_status in ("plan-review",) and meta.get("plan_approved") is None and has_approval(meta, new_body, "plan"):
        meta["plan_approved"] = True

    updated = render_frontmatter(meta, new_body)
    dest_dir = FEATURES_DIR / "done" if new_status == "done" else FEATURES_DIR
    dest_dir.mkdir(parents=True, exist_ok=True)
    target = dest_dir / new_name

    changed = raw_status != new_status or path.name != new_name or updated != text
    if not changed:
        return logs

    rel_old = path.relative_to(ROOT)
    rel_new = target.relative_to(ROOT)
    if dry_run:
        logs.append(f"[dry-run] {rel_old} -> {rel_new} (status: {raw_status} -> {new_status})")
        return logs

    if path.resolve() != target.resolve():
        if target.exists() and target.resolve() != path.resolve():
            logs.append(f"SKIP collision: {rel_new} already exists")
            return logs
        target.write_text(updated, encoding="utf-8")
        path.unlink()
        logs.append(f"{rel_old} -> {rel_new} (status: {raw_status} -> {new_status})")
    else:
        path.write_text(updated, encoding="utf-8")
        logs.append(f"{rel_old} (status: {raw_status} -> {new_status})")
    return logs


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate kanban columns v1 -> v2")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing")
    args = parser.parse_args()

    paths = sorted(FEATURES_DIR.rglob("*.md"))
    if not paths:
        raise SystemExit(f"No cards under {FEATURES_DIR}")

    all_logs: list[str] = []
    for path in paths:
        all_logs.extend(migrate_card(path, dry_run=args.dry_run))

    if not all_logs:
        print("No cards needed migration.")
    else:
        for line in all_logs:
            print(line)
        print(f"\n{'Would migrate' if args.dry_run else 'Migrated'} {len(all_logs)} change(s).")
        if not args.dry_run:
            print("Run: python scripts/kanban/sync_kanban_folders.py")


if __name__ == "__main__":
    main()
