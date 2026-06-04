#!/usr/bin/env python3
"""Merge done Kanban cards of the same kind into one bundle card per group.

Kind = family (pr, ops, …) + track (from card body or labels). Runs after folder
sync so new done cards collapse into the track bundle instead of cluttering Done.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

_KANBAN_DIR = Path(__file__).resolve().parent
if str(_KANBAN_DIR) not in sys.path:
    sys.path.insert(0, str(_KANBAN_DIR))

from kanban_common import (  # noqa: E402
    DONE_DIR,
    read_card,
    rel_path,
    render_frontmatter,
    utc_date,
    utc_now,
)

BUNDLED_CARDS_HEADING = "## Bundled cards"
TODAY = utc_date()
NOW_ISO = utc_now()

TRACK_RE = re.compile(r"\|\s*\*\*Track\*\*\s*\|\s*(\d+)\s*\|", re.IGNORECASE)
HEADING_RE = re.compile(r"^#\s+(.+)$", re.MULTILINE)
PR_SORT_RE = re.compile(r"^pr-(\d+)([a-z]?)", re.IGNORECASE)


@dataclass
class Card:
    path: Path
    meta: dict
    body: str
    family: str
    track: str
    heading: str
    is_bundle: bool
    sort_key: tuple = field(default_factory=tuple)

    @property
    def kind(self) -> str:
        return f"{self.family}:{self.track}"


def family_from_path(path: Path) -> str:
    stem = path.stem.lower()
    if stem.startswith("pr-"):
        return "pr"
    if stem.startswith("ops-"):
        return "ops"
    return "misc"


def track_from_card(meta: dict, body: str) -> str:
    labels = meta.get("labels") or []
    for label in labels:
        if isinstance(label, str) and label.startswith("track-"):
            return label.removeprefix("track-")
    match = TRACK_RE.search(body)
    if match:
        return match.group(1)
    return "unknown"


def heading_from_body(body: str, fallback: str) -> str:
    match = HEADING_RE.search(body)
    return match.group(1).strip() if match else fallback


def is_bundle_card(path: Path, meta: dict, body: str) -> bool:
    if meta.get("bundle") is True:
        return True
    if "-bundle" in path.stem:
        return True
    heading = heading_from_body(body, path.stem)
    return "bundle" in heading.lower()


def pr_sort_key(path: Path, heading: str) -> tuple:
    stem = path.stem.lower()
    match = PR_SORT_RE.match(stem)
    if match:
        return (int(match.group(1)), match.group(2) or "")
    ops_match = re.match(r"^ops-(\d+)", stem)
    if ops_match:
        return (int(ops_match.group(1)), "")
    return (9999, heading.lower())


def parse_card(path: Path) -> Card:
    meta, body = read_card(path)
    family = family_from_path(path)
    track = track_from_card(meta, body)
    heading = heading_from_body(body, path.stem)
    bundle = is_bundle_card(path, meta, body)
    return Card(
        path=path,
        meta=meta,
        body=body,
        family=family,
        track=track,
        heading=heading,
        is_bundle=bundle,
        sort_key=pr_sort_key(path, heading),
    )


def bundle_filename(family: str, track: str) -> str:
    return f"{family}-track-{track}-done-bundle-{TODAY}.md"


def bundle_title(family: str, track: str) -> str:
    if family == "pr":
        return f"Track {track} — PR done bundle"
    if family == "ops":
        return f"Track {track} — OPS done bundle"
    return f"Track {track} — Done bundle"


def legacy_bundle_member(card: Card) -> tuple[str, str]:
    body = card.body.strip()
    body = HEADING_RE.sub("", body, count=1).strip()
    return card.heading, body


def parse_embedded_bundle_members(body: str) -> list[tuple[str, str]]:
    if BUNDLED_CARDS_HEADING not in body:
        return []
    section = body.split(BUNDLED_CARDS_HEADING, 1)[1]
    chunks = re.split(r"\n###\s+", section)
    out: list[tuple[str, str]] = []
    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk:
            continue
        lines = chunk.split("\n", 1)
        title = lines[0].strip()
        rest = lines[1].strip() if len(lines) > 1 else ""
        if title:
            out.append((title, rest))
    return out


def members_from_existing_bundle(bundle: Card) -> list[tuple[str, str]]:
    embedded = parse_embedded_bundle_members(bundle.body)
    if embedded:
        return embedded
    return [legacy_bundle_member(bundle)]


def member_section_from_pairs(pairs: list[tuple[str, str]]) -> str:
    lines = [BUNDLED_CARDS_HEADING, ""]
    for heading, member_body in pairs:
        lines.append(f"### {heading}")
        lines.append("")
        if member_body.strip():
            lines.append(member_body.strip())
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def shared_fields_table(track: str, member_pairs: list[tuple[str, str]]) -> str:
    waves: set[str] = set()
    for _, body in member_pairs:
        wave_match = re.search(r"\|\s*\*\*Wave\*\*\s*\|\s*([^|]+)\s*\|", body)
        if wave_match:
            waves.add(wave_match.group(1).strip())
    rows = [f"| **Track** | {track} |"]
    if len(waves) == 1:
        rows.append(f"| **Wave** | {next(iter(waves))} |")
    rows.append(f"| **Members** | {len(member_pairs)} card(s) |")
    return "| Field | Value |\n|-------|-------|\n" + "\n".join(rows) + "\n"


def merge_member_pairs(existing: Card | None, members: list[Card]) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    seen: set[str] = set()
    if existing:
        for heading, body in members_from_existing_bundle(existing):
            key = heading.lower()
            if key not in seen:
                seen.add(key)
                pairs.append((heading, body))
    for card in sorted(members, key=lambda c: c.sort_key):
        key = card.heading.lower()
        if key in seen:
            continue
        seen.add(key)
        member_body = HEADING_RE.sub("", card.body.strip(), count=1).strip()
        pairs.append((card.heading, member_body))
    return pairs


def build_bundle(
    *,
    family: str,
    track: str,
    member_pairs: list[tuple[str, str]],
    existing: Card | None,
) -> str:
    title = bundle_title(family, track)
    bundle_id = f"{family}-track-{track}-done-bundle-{TODAY}"
    labels = list(existing.meta.get("labels") or []) if existing else []
    label_set = {str(x) for x in labels}
    label_set.add("bundle")
    label_set.add(f"track-{track}")
    if family == "pr":
        label_set.add("roadmap-pr")
    if family == "ops":
        label_set.add("ops")

    meta = {
        "id": bundle_id,
        "status": "done",
        "priority": (existing.meta.get("priority") if existing else "low") or "low",
        "assignee": existing.meta.get("assignee") if existing else None,
        "epic": existing.meta.get("epic") if existing else None,
        "dueDate": existing.meta.get("dueDate") if existing else None,
        "created": (existing.meta.get("created") if existing else NOW_ISO) or NOW_ISO,
        "modified": NOW_ISO,
        "completedAt": existing.meta.get("completedAt") if existing else None,
        "labels": sorted(label_set),
        "bundle": True,
        "bundle_kind": f"{family}:{track}",
        "order": existing.meta.get("order") if existing else "z0",
    }
    body = "\n".join(
        [
            f"# {title}",
            "",
            shared_fields_table(track, member_pairs),
            "",
            member_section_from_pairs(member_pairs),
        ]
    )
    return render_frontmatter(meta, body)


def _cards_by_kind(done_dir: Path) -> dict[str, list[Card]]:
    cards = [parse_card(path) for path in sorted(done_dir.glob("*.md"))]
    groups: dict[str, list[Card]] = {}
    for card in cards:
        groups.setdefault(card.kind, []).append(card)
    return groups


def _partition_group(group: list[Card]) -> tuple[list[Card], list[Card]]:
    bundles = [card for card in group if card.is_bundle]
    members = [card for card in group if not card.is_bundle]
    return bundles, members


def _should_bundle(members: list[Card]) -> bool:
    return len(members) >= 2


def _bundle_output_path(
    done_dir: Path, family: str, track: str, target_bundle: Card | None
) -> Path:
    if target_bundle:
        return target_bundle.path
    return done_dir / bundle_filename(family, track)


def _write_bundle(out_path: Path, content: str, member_count: int, *, dry_run: bool) -> None:
    if dry_run:
        print(f"would write bundle {rel_path(out_path)} ({member_count} members)")
        return
    out_path.write_text(content, encoding="utf-8")
    print(f"wrote bundle {rel_path(out_path)} ({member_count} members)")


def _remove_merged_members(members: list[Card], out_path: Path, *, dry_run: bool) -> None:
    resolved_out = out_path.resolve()
    for card in members:
        if card.path.resolve() == resolved_out:
            continue
        if dry_run:
            print(f"  would remove {rel_path(card.path)}")
        else:
            card.path.unlink()
            print(f"  removed {rel_path(card.path)}")


def _remove_duplicate_bundles(extra_bundles: list[Card], *, dry_run: bool) -> None:
    for extra_bundle in extra_bundles:
        if dry_run:
            print(f"  would remove duplicate bundle {rel_path(extra_bundle.path)}")
        else:
            extra_bundle.path.unlink()
            print(f"  removed duplicate bundle {rel_path(extra_bundle.path)}")


def _bundle_kind_group(
    kind: str,
    group: list[Card],
    done_dir: Path,
    *,
    dry_run: bool,
) -> Path | None:
    bundles, members = _partition_group(group)
    if not _should_bundle(members):
        return None

    family, track = kind.split(":", 1)
    target_bundle = bundles[0] if bundles else None
    member_pairs = merge_member_pairs(target_bundle, members)
    content = build_bundle(
        family=family,
        track=track,
        member_pairs=member_pairs,
        existing=target_bundle,
    )
    out_path = _bundle_output_path(done_dir, family, track, target_bundle)
    _write_bundle(out_path, content, len(member_pairs), dry_run=dry_run)
    _remove_merged_members(members, out_path, dry_run=dry_run)
    _remove_duplicate_bundles(bundles[1:], dry_run=dry_run)
    return out_path


def bundle_done_dir(done_dir: Path, *, dry_run: bool) -> list[Path]:
    if not done_dir.is_dir():
        return []

    written: list[Path] = []
    for kind, group in sorted(_cards_by_kind(done_dir).items()):
        out_path = _bundle_kind_group(kind, group, done_dir, dry_run=dry_run)
        if out_path is not None:
            written.append(out_path)
    return written


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--done-dir",
        type=Path,
        default=DONE_DIR,
        help="Done column folder (default: .devtool/features/done)",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    paths = bundle_done_dir(args.done_dir.resolve(), dry_run=args.dry_run)
    if not paths:
        print("no bundling changes")
    else:
        print(f"{'would update' if args.dry_run else 'updated'} {len(paths)} bundle(s)")


if __name__ == "__main__":
    main()
