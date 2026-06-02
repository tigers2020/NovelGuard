from __future__ import annotations

from typing import Any

from application.file_row_page_memory import query_file_rows_page_memory
from application.file_row_query import NormalizedFileRowsQuery
from application.ports.review_state import LoadedReviewState
from domain.duplicate_near import NearDuplicateResult
from domain.models import FileRecord
from domain.quality import QualityIssue


class MemoryLibraryIndex:
    def __init__(self) -> None:
        self._current_folder: str | None = None
        self._files: list[FileRecord] = []
        self._quality_issues: list[QualityIssue] = []
        self._review_groups: dict[str, dict[str, tuple[str | None, str | None]]] = {}
        self._review_members: dict[str, dict[str, str]] = {}
        self._near_results: dict[str, NearDuplicateResult] = {}
        self._file_review_projection: dict[str, tuple[str | None, bool]] = {}

    def clear(self) -> None:
        self._current_folder = None
        self._files = []
        self._quality_issues = []
        self._review_groups = {}
        self._review_members = {}
        self._near_results = {}
        self._file_review_projection = {}

    def replace_files(self, folder_path: str, files: list[FileRecord]) -> None:
        self._current_folder = folder_path
        self._files = list(files)

    @property
    def folder_path(self) -> str | None:
        return self._current_folder

    def files(self) -> list[FileRecord]:
        if self._current_folder is None:
            return []
        return list(self._files)

    def file_count(self) -> int:
        return len(self._files)

    def total_bytes(self) -> int:
        return sum(f.size_bytes for f in self._files)

    def replace_quality_issues(self, folder_path: str, issues: list[QualityIssue]) -> None:
        self._current_folder = folder_path
        self._quality_issues = list(issues)

    def quality_issues(self) -> list[QualityIssue]:
        if self._current_folder is None:
            return []
        return list(self._quality_issues)

    def load_review_state(self, folder_path: str) -> LoadedReviewState:
        return LoadedReviewState(
            groups=dict(self._review_groups.get(folder_path, {})),
            members=dict(self._review_members.get(folder_path, {})),
        )

    def upsert_review_group(
        self,
        folder_path: str,
        group_id: str,
        *,
        keeper_file_id: str | None = None,
        group_status: str | None = None,
        clear_keeper: bool = False,
        clear_status: bool = False,
    ) -> None:
        bucket = self._review_groups.setdefault(folder_path, {})
        prev = bucket.get(group_id, (None, None))
        new_keeper = (
            None if clear_keeper else (keeper_file_id if keeper_file_id is not None else prev[0])
        )
        new_status = (
            None if clear_status else (group_status if group_status is not None else prev[1])
        )
        bucket[group_id] = (new_keeper, new_status)

    def delete_review_group(self, folder_path: str, group_id: str) -> bool:
        bucket = self._review_groups.get(folder_path, {})
        if group_id in bucket:
            del bucket[group_id]
            return True
        return False

    def upsert_review_member(self, folder_path: str, file_id: str, member_status: str) -> None:
        self._review_members.setdefault(folder_path, {})[file_id] = member_status

    def delete_review_member(self, folder_path: str, file_id: str) -> bool:
        bucket = self._review_members.get(folder_path, {})
        if file_id in bucket:
            del bucket[file_id]
            return True
        return False

    def clear_review_state(self, folder_path: str) -> None:
        self._review_groups.pop(folder_path, None)
        self._review_members.pop(folder_path, None)

    def prune_review_state(
        self,
        folder_path: str,
        valid_group_ids: set[str],
        valid_file_ids: set[str],
    ) -> None:
        groups = self._review_groups.get(folder_path, {})
        self._review_groups[folder_path] = {
            gid: state for gid, state in groups.items() if gid in valid_group_ids
        }
        members = self._review_members.get(folder_path, {})
        self._review_members[folder_path] = {
            fid: status for fid, status in members.items() if fid in valid_file_ids
        }

    def replace_near_duplicate_results(self, folder_path: str, result: NearDuplicateResult) -> None:
        self._near_results[folder_path] = result

    def load_near_duplicate_result(self, folder_path: str) -> NearDuplicateResult | None:
        return self._near_results.get(folder_path)

    def clear_near_duplicate_results(self, folder_path: str) -> None:
        self._near_results.pop(folder_path, None)

    def replace_file_review_projection(
        self,
        folder_path: str,
        rows: list[tuple[str, str | None, bool, str | None]],
    ) -> None:
        _ = folder_path
        self._file_review_projection = {
            file_id: (duplicate_group_id, is_keeper)
            for file_id, duplicate_group_id, is_keeper, _group_key in rows
        }

    def query_file_rows_page(self, normalized: NormalizedFileRowsQuery) -> dict[str, Any]:
        return query_file_rows_page_memory(
            self._files,
            normalized,
            projection_by_file_id=self._file_review_projection,
        )
