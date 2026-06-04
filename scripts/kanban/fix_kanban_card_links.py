#!/usr/bin/env python3
"""Normalize spec/plan links in .devtool/features/*.md cards."""

from __future__ import annotations

import sys
from pathlib import Path

_KANBAN_DIR = Path(__file__).resolve().parent
if str(_KANBAN_DIR) not in sys.path:
    sys.path.insert(0, str(_KANBAN_DIR))

from kanban_common import FEATURES_DIR, ROOT, fix_card_doc_links  # noqa: E402


def main() -> None:
    for path in FEATURES_DIR.rglob("*.md"):
        original = path.read_text(encoding="utf-8")
        updated = fix_card_doc_links(original)
        if updated != original:
            path.write_text(updated, encoding="utf-8")
            print(path.relative_to(ROOT))


if __name__ == "__main__":
    main()
