#!/usr/bin/env python3
"""Regenerate generic Plan/Todo cards from spec for an existing work_id."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_KANBAN_DIR = Path(__file__).resolve().parent
if str(_KANBAN_DIR) not in sys.path:
    sys.path.insert(0, str(_KANBAN_DIR))

from kanban_common import (  # noqa: E402
    create_card_if_missing,
    load_config,
    normalize_work_id,
    read_card,
    rel_path,
    write_card,
)
from kanban_inbox_to_scheduled import (  # noqa: E402
    build_plan_template,
    build_todo_content,
    files_allowed,
    find_card_for_stage,
    is_generic_plan_body,
    is_generic_todo_body,
)


def rehydrate(work_id: str, *, dry_run: bool) -> list[str]:
    config = load_config()
    work_id = normalize_work_id(work_id, work_id)
    changed: list[str] = []

    spec_path = find_card_for_stage(config, work_id, "spec-draft")
    plan_path = find_card_for_stage(config, work_id, "plan-draft")
    todo_path = find_card_for_stage(config, work_id, "todo")
    if not spec_path:
        raise SystemExit(f"spec card not found for {work_id}")

    spec_meta, spec_body = read_card(spec_path)
    allowed = files_allowed(spec_meta, spec_body)
    if not allowed:
        allowed = [".devtool/features/", "scripts/", "src/", "web/src/", "tests/"]

    if not plan_path or is_generic_plan_body(read_card(plan_path)[1]):
        plan_body = build_plan_template(spec_path, work_id, allowed)
        if plan_path:
            meta, _ = read_card(plan_path)
            meta["approved"] = True
            meta["approved_by"] = "rehydrate_planning_cards"
            meta["approved_at"] = "auto"
            write_card(plan_path, meta, f"# [Plan Draft] {work_id}\n\n{plan_body.strip()}\n", dry_run=dry_run)
        else:
            plan_path = create_card_if_missing(
                config,
                "plan-draft",
                work_id,
                f"[Plan Draft] {work_id}",
                {
                    "linked_spec": rel_path(spec_path),
                    "files_allowed": allowed,
                    "branch": f"feat/{work_id}",
                    "approved": True,
                    "approved_by": "rehydrate_planning_cards",
                },
                plan_body,
                dry_run=dry_run,
            )
        changed.append(rel_path(plan_path))

    todo_content = build_todo_content(plan_path, spec_path, allowed)
    if todo_path and is_generic_todo_body(read_card(todo_path)[1]) and todo_content:
        meta, _ = read_card(todo_path)
        write_card(todo_path, meta, f"# [Todo] {work_id}\n\n{todo_content}", dry_run=dry_run)
        changed.append(rel_path(todo_path))
    elif not todo_path and todo_content:
        todo_path = create_card_if_missing(
            config,
            "todo",
            work_id,
            f"[Todo] {work_id}",
            {
                "linked_spec": rel_path(spec_path),
                "linked_plan": rel_path(plan_path) if plan_path else None,
                "files_allowed": allowed,
            },
            todo_content,
            dry_run=dry_run,
        )
        changed.append(rel_path(todo_path))

    return changed


def main() -> None:
    parser = argparse.ArgumentParser(description="Rehydrate generic plan/todo from spec")
    parser.add_argument("work_id", help="e.g. pr-58-exact-keeper-move-2026-06-04")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    changed = rehydrate(args.work_id, dry_run=args.dry_run)
    if not changed:
        print("no changes (cards already populated)")
        return
    print("updated:")
    for path in changed:
        print(f"  - {path}")


if __name__ == "__main__":
    main()
