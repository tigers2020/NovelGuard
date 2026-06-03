from __future__ import annotations

from typing import Any, Protocol

from application.file_row_query import NormalizedFileRowsQuery
from application.ports.review_state import LoadedReviewState
from domain.duplicate_near import NearDuplicateResult
from domain.models import FileRecord
from domain.quality import QualityIssue


class LibraryIndexPort(Protocol):
    def clear(self) -> None: ...

    def replace_files(self, folder_path: str, files: list[FileRecord]) -> None: ...

    def append_files_batch(
        self,
        folder_path: str,
        files: list[FileRecord],
        *,
        reset: bool = False,
    ) -> None: ...

    def activate_library_folder(self, folder_path: str) -> None: ...

    @property
    def folder_path(self) -> str | None: ...

    def files(self) -> list[FileRecord]: ...

    def file_count(self) -> int: ...

    def total_bytes(self) -> int: ...

    def replace_quality_issues(self, folder_path: str, issues: list[QualityIssue]) -> None: ...

    def quality_issues(self) -> list[QualityIssue]: ...

    def load_review_state(self, folder_path: str) -> LoadedReviewState: ...

    def upsert_review_group(
        self,
        folder_path: str,
        group_id: str,
        *,
        keeper_file_id: str | None = None,
        group_status: str | None = None,
        clear_keeper: bool = False,
        clear_status: bool = False,
    ) -> None: ...

    def delete_review_group(self, folder_path: str, group_id: str) -> bool: ...

    def upsert_review_member(self, folder_path: str, file_id: str, member_status: str) -> None: ...

    def delete_review_member(self, folder_path: str, file_id: str) -> bool: ...

    def clear_review_state(self, folder_path: str) -> None: ...

    def prune_review_state(
        self,
        folder_path: str,
        valid_group_ids: set[str],
        valid_file_ids: set[str],
    ) -> None: ...

    def replace_near_duplicate_results(
        self, folder_path: str, result: NearDuplicateResult
    ) -> None: ...

    def load_near_duplicate_result(self, folder_path: str) -> NearDuplicateResult | None: ...

    def clear_near_duplicate_results(self, folder_path: str) -> None: ...

    def replace_file_review_projection(
        self,
        folder_path: str,
        rows: list[tuple[str, str | None, bool, str | None]],
    ) -> None: ...

    def query_file_rows_page(self, normalized: NormalizedFileRowsQuery) -> dict[str, Any]: ...
