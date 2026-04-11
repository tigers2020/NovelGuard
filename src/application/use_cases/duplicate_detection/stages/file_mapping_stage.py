"""FileDataStore 매핑 단계."""

from datetime import datetime
from typing import Optional

from application.dto.log_entry import LogEntry
from application.ports.file_data_store import IFileDataStore
from application.ports.log_sink import ILogSink
from application.use_cases.duplicate_detection.stages.base_stage import (
    PipelineContext,
    PipelineStage,
)
from application.utils.debug_logger import debug_step
from domain.entities.file_entry import FileEntry
from domain.value_objects.filename_parse_result import FilenameParseResult


class FileMappingStage(PipelineStage):
    """FileDataStore 매핑 단계.

    IndexRepository의 file_id를 FileDataStore의 file_id로 매핑합니다.
    """

    def __init__(
        self, file_data_store: Optional[IFileDataStore] = None, log_sink: Optional[ILogSink] = None
    ) -> None:
        """FileDataStore 매핑 단계 초기화.

        Args:
            file_data_store: 파일 데이터 저장소.
            log_sink: 로그 싱크 (선택적).
        """
        self._file_data_store = file_data_store
        self._log_sink = log_sink

    @property
    def name(self) -> str:
        return "FileDataStore 매핑"

    def _log_error(self, message: str, *, context_data: Optional[dict] = None) -> None:
        if not self._log_sink:
            return
        self._log_sink.write(
            LogEntry(
                timestamp=datetime.now(),
                level="ERROR",
                message=message,
                context=context_data or {},
            )
        )

    def _collect_file_mappings(
        self, context: PipelineContext
    ) -> tuple[
        int,
        int,
        list[tuple[FileEntry, FilenameParseResult]],
        dict[int, FileEntry],
        dict[int, int],
    ]:
        assert self._file_data_store is not None

        file_parse_pairs: list[tuple[FileEntry, FilenameParseResult]] = []
        file_entries_map: dict[int, FileEntry] = {}
        file_id_mapping: dict[int, int] = {}
        mapped_count = 0
        skipped_count = 0

        for file_entry in context.files:
            store_file_id = self._file_data_store.get_file_id_by_path(file_entry.path)

            if store_file_id is None:
                skipped_count += 1
                continue

            mapped_count += 1
            file_entries_map[store_file_id] = file_entry

            original_id = (
                file_entry.file_id if file_entry.file_id is not None else hash(str(file_entry.path))
            )
            if original_id not in context.parse_results:
                continue

            file_parse_pairs.append((file_entry, context.parse_results[original_id]))
            file_id_mapping[original_id] = store_file_id

        return mapped_count, skipped_count, file_parse_pairs, file_entries_map, file_id_mapping

    def _abort_if_mapping_ratio_too_low(
        self,
        context: PipelineContext,
        *,
        fetched_files_count: int,
        mapped_count: int,
        skipped_count: int,
    ) -> bool:
        """매핑률이 너무 낮으면 context.error를 설정하고 True를 반환."""
        if fetched_files_count <= 0:
            return False

        mapped_ratio = mapped_count / fetched_files_count
        if mapped_ratio >= 0.5:
            return False

        error_msg = (
            f"FileDataStore 동기화 실패: "
            f"조회된 파일 {fetched_files_count}개 중 {mapped_count}개만 매핑됨 "
            f"(매핑률: {mapped_ratio:.1%}). "
            f"먼저 스캔을 실행하여 FileDataStore를 채우세요."
        )
        self._log_error(
            error_msg,
            context_data={
                "fetched_files_count": fetched_files_count,
                "mapped_files_count": mapped_count,
                "skipped_files_count": skipped_count,
            },
        )
        context.error = error_msg
        return True

    def execute(self, context: PipelineContext) -> PipelineContext:
        """FileDataStore 매핑 단계 실행.

        Args:
            context: 파이프라인 컨텍스트.

        Returns:
            업데이트된 컨텍스트.

        Raises:
            PipelineError: FileDataStore가 없거나 매핑 실패율이 너무 높을 때.
        """
        debug_step(self._log_sink, "duplicate_detection_stage", {"stage": self.name})

        if not self._file_data_store:
            error_msg = "FileDataStore is required for duplicate detection"
            self._log_error(error_msg)
            context.error = error_msg
            return context

        if len(context.files) == 0:
            return context

        fetched_files_count = len(context.files)

        mapped_count, skipped_count, file_parse_pairs, file_entries_map, file_id_mapping = (
            self._collect_file_mappings(context)
        )

        debug_step(
            self._log_sink,
            "duplicate_detection_file_mapping_stats",
            {
                "fetched_files_count": fetched_files_count,
                "mapped_files_count": mapped_count,
                "skipped_files_count": skipped_count,
                "mapped_ratio": mapped_count / fetched_files_count
                if fetched_files_count > 0
                else 0.0,
                "file_parse_pairs_count": len(file_parse_pairs),
            },
        )

        if self._abort_if_mapping_ratio_too_low(
            context,
            fetched_files_count=fetched_files_count,
            mapped_count=mapped_count,
            skipped_count=skipped_count,
        ):
            return context

        context.file_id_mapping = file_id_mapping
        context.file_entries_map = file_entries_map
        context.file_parse_pairs = file_parse_pairs

        return context
