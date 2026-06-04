"""Apply review decision commands (PR-17)."""

from __future__ import annotations

from typing import Any

from app.selection_resolve import resolve_selection_rows
from application.library_session import LibrarySession
from application.ports.library_index import LibraryIndexPort
from application.review_errors import ReviewDecisionError
from application.review_state_merge import _file_id_from_row_id, group_id_from_row
from domain.duplicate_groups import find_duplicate_groups

MAX_REVIEW_MUTATIONS = 500

_COMMAND_STATUS = {
    "approve": "approved",
    "exclude": "excluded",
    "markConflict": "conflict",
}


def _review_group_scope(
    row: dict[str, Any],
    group_id: str | None,
    members_by_group: dict[str, set[str]],
) -> str | None:
    if not group_id:
        return None
    if group_id in members_by_group:
        return "exact"
    if group_id.startswith("near:") or row.get("type") == "near":
        return "near"
    if group_id.startswith("relation:") or row.get("type") == "relation":
        return "relation"
    return None


class UpdateReviewDecisionsUseCase:
    def __init__(self, session: LibrarySession, index: LibraryIndexPort) -> None:
        self._session = session
        self._index = index

    def execute(
        self,
        selection: dict[str, Any],
        command: str,
        *,
        keeper_file_id: str | None = None,
    ) -> int:
        folder = self._index.folder_path
        if not folder:
            return 0

        valid_commands = {"approve", "exclude", "setKeeper", "markConflict", "reset"}
        if command not in valid_commands:
            raise ReviewDecisionError("INVALID_REVIEW_COMMAND", f"Unknown command: {command}")

        rows = resolve_selection_rows(self._session.review_rows_snapshot(), selection)
        if len(rows) > MAX_REVIEW_MUTATIONS:
            raise ReviewDecisionError(
                "INVALID_REVIEW_COMMAND",
                f"Selection resolves to more than {MAX_REVIEW_MUTATIONS} rows",
            )

        files = self._index.files()
        from pathlib import Path

        groups = find_duplicate_groups(files, library_root=Path(folder))
        members_by_group = {g.group_id: set(g.member_ids) for g in groups}

        updated = 0
        for row in rows:
            raw_group_id = group_id_from_row(row)
            scope = _review_group_scope(row, raw_group_id, members_by_group)
            if scope is None or raw_group_id is None:
                continue
            group_id = raw_group_id

            if command == "reset":
                updated += self._apply_reset(folder, row, group_id)
                continue

            if command == "setKeeper":
                if scope not in ("exact", "near", "relation"):
                    continue
                if scope == "exact":
                    group_members = members_by_group[group_id]
                else:
                    from application.review_state_merge import _file_id_from_row_id

                    group_members = set()
                    for member_row in self._session.review_rows_snapshot():
                        if member_row.get("groupId") != group_id:
                            continue
                        if member_row.get("rowKind") != "file":
                            continue
                        file_id = _file_id_from_row_id(str(member_row.get("id", "")))
                        if file_id:
                            group_members.add(file_id)
                updated += self._apply_set_keeper(
                    folder,
                    row,
                    group_id,
                    group_members,
                    keeper_file_id=keeper_file_id,
                )
                continue

            status = _COMMAND_STATUS.get(command)
            if status is None:
                continue
            updated += self._apply_status(folder, row, group_id, status)

        return updated

    def _apply_status(self, folder: str, row: dict[str, Any], group_id: str, status: str) -> int:
        if row.get("rowKind") == "group":
            self._index.upsert_review_group(
                folder,
                group_id,
                group_status=status,
            )
            return 1

        file_id = _require_file_id(row)
        self._index.upsert_review_member(folder, file_id, status)
        return 1

    def _apply_reset(self, folder: str, row: dict[str, Any], group_id: str) -> int:
        if row.get("rowKind") == "group":
            if self._index.delete_review_group(folder, group_id):
                return 1
            return 0

        file_id = _require_file_id(row)
        if self._index.delete_review_member(folder, file_id):
            return 1
        return 0

    def _apply_set_keeper(
        self,
        folder: str,
        row: dict[str, Any],
        group_id: str,
        member_ids: set[str],
        *,
        keeper_file_id: str | None,
    ) -> int:
        if row.get("rowKind") == "file":
            resolved_keeper = _require_file_id(row)
        else:
            if not keeper_file_id:
                raise ReviewDecisionError(
                    "INVALID_REVIEW_COMMAND",
                    "setKeeper on group row requires keeperFileId",
                )
            resolved_keeper = keeper_file_id

        if resolved_keeper not in member_ids:
            raise ReviewDecisionError(
                "INVALID_REVIEW_COMMAND", "keeperFileId is not a group member"
            )

        self._downgrade_approved_only(folder, group_id, member_ids)
        self._index.upsert_review_group(
            folder,
            group_id,
            keeper_file_id=resolved_keeper,
        )
        return 1

    def _downgrade_approved_only(
        self,
        folder: str,
        group_id: str,
        member_ids: set[str],
    ) -> None:
        stored = self._index.load_review_state(folder)
        group_entry = stored.groups.get(group_id)
        if group_entry and group_entry[1] == "approved":
            self._index.upsert_review_group(folder, group_id, clear_status=True)

        for file_id in member_ids:
            if stored.members.get(file_id) == "approved":
                self._index.delete_review_member(folder, file_id)


def _require_file_id(row: dict[str, Any]) -> str:
    row_id = str(row.get("id", ""))
    file_id = _file_id_from_row_id(row_id)
    if file_id:
        return file_id
    raise ReviewDecisionError(
        "INVALID_REVIEW_COMMAND", "setKeeper requires a file row or keeperFileId"
    )
