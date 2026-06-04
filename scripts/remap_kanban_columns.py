#!/usr/bin/env python3
"""Remap legacy kanban status folders/frontmatter to the NovelGuard PR workflow columns."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
FEATURES = ROOT / ".devtool" / "features"

# legacy folder/status id -> new status id
LEGACY_TO_NEW: dict[str, str] = {
    "proposed": "todo",
    "ready": "ready",
    "in-progress": "in-progress",
    "in_progress": "in-progress",
    "done": "done",
    "cancelled": "blocked",
    "backlog": "triage",
    "todo": "todo",
    "review": "review",
    "blocked": "blocked",
    "triage": "triage",
    "spec": "spec",
    "plan": "plan",
    "scheduled": "scheduled",
}


def split_frontmatter(text: str) -> tuple[dict, str]:
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    meta = yaml.safe_load(parts[1]) or {}
    body = parts[2].lstrip("\n")
    return meta, body


def render_frontmatter(meta: dict, body: str) -> str:
    block = yaml.safe_dump(meta, sort_keys=False, allow_unicode=True).strip()
    return f"---\n{block}\n---\n\n{body}"


def infer_legacy_status(path: Path) -> str:
    parent = path.parent.name
    if parent != "features":
        return parent
    meta, _ = split_frontmatter(path.read_text(encoding="utf-8"))
    return str(meta.get("status", "triage"))


def main() -> None:
    paths = sorted(FEATURES.rglob("*.md"))
    if not paths:
        raise SystemExit(f"No cards under {FEATURES}")

    for path in paths:
        text = path.read_text(encoding="utf-8")
        meta, body = split_frontmatter(text)
        legacy = infer_legacy_status(path)
        new_status = LEGACY_TO_NEW.get(legacy, legacy)
        meta["status"] = new_status
        updated = render_frontmatter(meta, body)

        target_dir = FEATURES / new_status
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / path.name
        target.write_text(updated, encoding="utf-8")
        if path.resolve() != target.resolve():
            path.unlink()

    # remove empty legacy dirs
    for child in FEATURES.iterdir():
        if child.is_dir() and not any(child.glob("*.md")):
            child.rmdir()

    print(f"remapped {len(paths)} cards")


if __name__ == "__main__":
    main()
