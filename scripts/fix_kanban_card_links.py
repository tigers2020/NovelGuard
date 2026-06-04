#!/usr/bin/env python3
"""Normalize spec/plan links in .devtool/features/*.md cards."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FEATURES = ROOT / ".devtool" / "features"
PREFIX = "../../../docs/superpowers/"


def fix(text: str) -> str:
    text = text.replace("`specs/", f"`{PREFIX}specs/")
    text = text.replace("`plans/", f"`{PREFIX}plans/")
    text = re.sub(r"\(\.\./specs/", f"({PREFIX}specs/", text)
    text = re.sub(r"\(specs/", f"({PREFIX}specs/", text)
    text = re.sub(r"\(\.\./plans/", f"({PREFIX}plans/", text)
    text = re.sub(r"\(plans/", f"({PREFIX}plans/", text)
    return text


def main() -> None:
    for path in FEATURES.rglob("*.md"):
        original = path.read_text(encoding="utf-8")
        updated = fix(original)
        if updated != original:
            path.write_text(updated, encoding="utf-8")
            print(path.relative_to(ROOT))


if __name__ == "__main__":
    main()
