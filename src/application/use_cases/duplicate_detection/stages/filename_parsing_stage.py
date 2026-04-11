"""파일명 파싱 단계."""

from datetime import datetime
from typing import Optional

from application.dto.log_entry import LogEntry
from application.ports.index_repository import IIndexRepository
from application.ports.log_sink import ILogSink
from application.use_cases.duplicate_detection.stages.base_stage import (
    PipelineContext,
    PipelineStage,
)
from application.utils.debug_logger import debug_step
from domain.entities.file_entry import FileEntry
from domain.services.filename_parser import FilenameParser
from domain.value_objects.filename_parse_result import FilenameParseResult


class FilenameParsingStage(PipelineStage):
    """파일명 파싱 단계.

    IndexRepository에서 파일 목록을 가져와 각 파일의 파일명을 파싱합니다.
    """

    def __init__(
        self,
        filename_parser: FilenameParser,
        index_repository: IIndexRepository,
        log_sink: Optional[ILogSink] = None,
    ) -> None:
        """파일명 파싱 단계 초기화.

        Args:
            filename_parser: 파일명 파서.
            index_repository: 인덱스 저장소.
            log_sink: 로그 싱크 (선택적).
        """
        self._filename_parser = filename_parser
        self._index_repository = index_repository
        self._log_sink = log_sink

    def _log_parse_failure(self, file_entry: FileEntry, error: Exception) -> None:
        if self._log_sink is None:
            return
        self._log_sink.write(
            LogEntry(
                timestamp=datetime.now(),
                level="WARN",
                message=f"파일명 파싱 실패 (스킵): {file_entry.path} - {error}",
                context={
                    "file_path": str(file_entry.path),
                    "error_type": type(error).__name__,
                    "error": str(error),
                },
            )
        )

    def _store_parse_result(
        self,
        file_entry: FileEntry,
        parse_result: FilenameParseResult,
        parse_results: dict[int, FilenameParseResult],
    ) -> None:
        if file_entry.file_id is not None:
            parse_results[file_entry.file_id] = parse_result
            return
        file_id = hash(str(file_entry.path))
        parse_results[file_id] = parse_result

    def _parse_one_file(
        self,
        file_entry: FileEntry,
        parse_results: dict[int, FilenameParseResult],
    ) -> None:
        try:
            parse_result = self._filename_parser.parse(file_entry.path)
        except Exception as e:
            self._log_parse_failure(file_entry, e)
            return
        self._store_parse_result(file_entry, parse_result, parse_results)

    @property
    def name(self) -> str:
        return "파일명 파싱"

    def execute(self, context: PipelineContext) -> PipelineContext:
        """파일명 파싱 단계 실행.

        Args:
            context: 파이프라인 컨텍스트.

        Returns:
            업데이트된 컨텍스트.
        """
        debug_step(self._log_sink, "duplicate_detection_stage", {"stage": self.name})

        # 페이지네이션으로 파일 목록 가져오기
        all_files: list[FileEntry] = []
        offset = 0
        limit = 200
        parse_results: dict[int, FilenameParseResult] = {}

        while True:
            files_batch = self._index_repository.list_files(
                run_id=context.request.run_id, offset=offset, limit=limit
            )

            if not files_batch:
                break

            all_files.extend(files_batch)

            # 각 파일에 대해 파일명 파싱
            for file_entry in files_batch:
                self._parse_one_file(file_entry, parse_results)

            offset += limit

        # 컨텍스트 업데이트
        context.files = all_files
        context.parse_results = parse_results

        debug_step(
            self._log_sink,
            "duplicate_detection_files_loaded",
            {"total_files": len(all_files), "parsed_files": len(parse_results)},
        )

        # 파일이 없으면 에러 설정하지 않고 빈 상태로 반환
        # (다음 단계에서 처리)

        return context
