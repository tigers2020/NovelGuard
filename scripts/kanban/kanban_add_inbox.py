#!/usr/bin/env python3
"""Create a Kanban Inbox card under .devtool/features/."""

from __future__ import annotations

import argparse
import sys
from datetime import date

from kanban_common import (
    card_work_id,
    ensure_unique_card,
    load_config,
    normalize_work_id,
    read_card,
    rel_path,
    render_frontmatter,
    repo_path,
    scan_cards,
    slugify,
    utc_now,
)

SCRIPT_NAME = "kanban_add_inbox"

WORK_TYPES = ("feature", "fix", "other")
WORK_TYPE_ALIASES = {
    "feature": "feature",
    "feat": "feature",
    "implement": "feature",
    "implementation": "feature",
    "enhancement": "feature",
    "fix": "fix",
    "bug": "fix",
    "bugfix": "fix",
    "bug-fix": "fix",
    "hotfix": "fix",
    "other": "other",
    "chore": "other",
    "docs": "other",
    "refactor": "other",
    "ops": "other",
    "spike": "other",
    "research": "other",
}


def normalize_work_type(value: str) -> str:
    raw = value.strip().lower()
    if raw in WORK_TYPES:
        return raw
    return WORK_TYPE_ALIASES.get(raw, raw)


def merge_labels(work_type: str, extra: list[str]) -> list[str]:
    labels = [work_type]
    for item in extra:
        tag = item.strip()
        if tag and tag not in labels:
            labels.append(tag)
    return labels


def default_work_id(title: str, when: date | None = None) -> str:
    day = (when or date.today()).isoformat()
    return f"{slugify(title, max_len=48)}-{day}"


def build_body(
    title: str,
    scope: str,
    acceptance: str,
    files_allowed: list[str],
    *,
    work_type: str,
    track: str | None,
    spec: str | None,
    plan: str | None,
) -> str:
    type_label = {"feature": "Feature", "fix": "Bug fix", "other": "Other"}[work_type]
    lines = [f"# {title}", ""]
    if work_type or track or spec or plan:
        lines.extend(["| Field | Value |", "|-------|-------|"])
        lines.append(f"| **Type** | {type_label} (`{work_type}`) |")
        if track:
            lines.append(f"| **Track** | {track} |")
        if spec:
            lines.append(f"| **Spec** | `{spec}` |")
        if plan:
            lines.append(f"| **Plan** | `{plan}` |")
        lines.append("")
    if scope.strip():
        lines.extend(["## Scope", "", scope.strip(), ""])
    lines.extend(
        [
            "## Acceptance",
            "",
            acceptance.strip(),
            "",
            "## files_allowed",
            "",
        ]
    )
    for item in files_allowed:
        lines.append(f"- `{item}`")
    lines.append("")
    return "\n".join(lines)


def find_work_id_conflict(config: dict, work_id: str) -> str | None:
    for path in scan_cards(config):
        meta, _ = read_card(path)
        if card_work_id(meta, path.stem) == work_id:
            col = str(meta.get("status") or "unknown")
            return f"{rel_path(path)} (status={col})"
    return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Add a Kanban Inbox card.")
    parser.add_argument("title", help="Short card title")
    parser.add_argument("--work-id", help="work_id / epic (default: slug-title-YYYY-MM-DD)")
    parser.add_argument("--scope", default="", help="Problem / scope markdown")
    parser.add_argument("--acceptance", required=True, help="Acceptance criteria (plain or markdown)")
    parser.add_argument(
        "--files-allowed",
        nargs="+",
        default=[".devtool/features/", "docs/agent/"],
        help="Path prefixes allowed during planning",
    )
    parser.add_argument("--track", default=None)
    parser.add_argument("--spec", default=None, help="Optional spec path")
    parser.add_argument("--plan", default=None, help="Optional plan path")
    parser.add_argument("--priority", default="medium", choices=("low", "medium", "high"))
    parser.add_argument(
        "--work-type",
        required=True,
        choices=WORK_TYPES,
        metavar="TYPE",
        help="feature (new capability), fix (bug), other (chore/docs/refactor/ops/…)",
    )
    parser.add_argument(
        "--labels",
        nargs="*",
        default=[],
        help="Extra labels (work_type is always added first)",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    work_type = normalize_work_type(args.work_type)
    if work_type not in WORK_TYPES:
        print(
            f"BLOCKED: invalid work_type {args.work_type!r}; use feature, fix, or other",
            file=sys.stderr,
        )
        return 2

    config = load_config()
    work_id = normalize_work_id(args.work_id or default_work_id(args.title))
    conflict = find_work_id_conflict(config, work_id)
    if conflict:
        print(f"BLOCKED: work_id {work_id} already used by {conflict}", file=sys.stderr)
        return 2

    existing, blocker = ensure_unique_card(config, "inbox", work_id)
    if blocker:
        print(f"BLOCKED: {blocker}", file=sys.stderr)
        return 2
    if existing:
        print(f"BLOCKED: inbox card already exists: {rel_path(existing)}", file=sys.stderr)
        return 2

    card_id = f"{work_id}-inbox"
    path = repo_path(config["board_root"]) / f"{card_id}.md"
    body = build_body(
        args.title,
        args.scope,
        args.acceptance,
        list(args.files_allowed),
        work_type=work_type,
        track=args.track,
        spec=args.spec,
        plan=args.plan,
    )
    meta = {
        "id": card_id,
        "status": "inbox",
        "work_id": work_id,
        "epic": work_id,
        "work_type": work_type,
        "priority": args.priority,
        "created": utc_now(),
        "labels": merge_labels(work_type, list(args.labels)),
        "acceptance": args.acceptance.strip(),
        "files_allowed": list(args.files_allowed),
        "automation_state": "created",
    }
    if args.track:
        meta["track"] = args.track

    if not args.dry_run:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(render_frontmatter(meta, body), encoding="utf-8")

    print(rel_path(path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
