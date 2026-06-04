#!/usr/bin/env python3
"""Move each card into .devtool/features/<status>/ matching frontmatter status."""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
FEATURES = ROOT / ".devtool" / "features"


def split_frontmatter(text: str) -> tuple[dict, str]:
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    return yaml.safe_load(parts[1]) or {}, parts[2].lstrip("\n")


def main() -> None:
    for path in sorted(FEATURES.rglob("*.md")):
        text = path.read_text(encoding="utf-8")
        meta, _ = split_frontmatter(text)
        status = str(meta.get("status", "triage")).strip()
        if not status:
            status = "triage"
        target_dir = FEATURES / status
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / path.name
        if path.resolve() == target.resolve():
            continue
        target.write_text(text, encoding="utf-8")
        path.unlink()
        print(f"{path.relative_to(ROOT)} -> {target.relative_to(ROOT)}")

    for child in sorted(FEATURES.iterdir()):
        if child.is_dir() and child.name != "features" and not any(child.glob("*.md")):
            child.rmdir()


if __name__ == "__main__":
    main()
