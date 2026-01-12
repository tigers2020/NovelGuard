"""FileDataStore 매핑 단계."""
from datetime import datetime
from typing import Optional, TYPE_CHECKING

from application.dto.log_entry import LogEntry
from application.ports.log_sink import ILogSink
from application.use_cases.duplicate_detection.stages.base_stage import (
    PipelineContext,
    PipelineError,
    PipelineStage
)
from application.utils.debug_logger import debug_step

if TYPE_CHECKING:
    from gui.models.file_data_store import FileDataStore


class FileMappingStage(PipelineStage):
    """FileDataStore 매핑 단계.
    
    IndexRepository의 file_id를 FileDataStore의 file_id로 매핑합니다.
    """
    
    def __init__(
        self,
        file_data_store: "FileDataStore",
        log_sink: Optional[ILogSink] = None
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
    
    def execute(self, context: PipelineContext) -> PipelineContext:
        """FileDataStore 매핑 단계 실행.
        
        Args:
            context: 파이프라인 컨텍스트.
        
        Returns:
            업데이트된 컨텍스트.
        
        Raises:
            PipelineError: FileDataStore가 없거나 매핑 실패율이 너무 높을 때.
        """
        debug_step(
            self._log_sink,
            "duplicate_detection_stage",
            {"stage": self.name}
        )
        
        if not self._file_data_store:
            error_msg = "FileDataStore is required for duplicate detection"
            if self._log_sink:
                self._log_sink.write(LogEntry(
                    timestamp=datetime.now(),
                    level="ERROR",
                    message=error_msg,
                    context={}
                ))
            context.error = error_msg
            return context
        
        if len(context.files) == 0:
            # 파일이 없으면 빈 상태로 반환 (에러 아님)
            return context
        
        fetched_files_count = len(context.files)
        
        # (FileEntry, FilenameParseResult) 튜플 리스트 생성
        from domain.entities.file_entry import FileEntry
        from domain.value_objects.filename_parse_result import FilenameParseResult
        
        file_parse_pairs: list[tuple[FileEntry, FilenameParseResult]] = []
        file_entries_map: dict[int, FileEntry] = {}  # FileDataStore file_id -> FileEntry
        file_id_mapping: dict[int, int] = {}  # IndexRepository file_id (또는 hash) -> FileDataStore file_id
        mapped_count = 0
        skipped_count = 0
        
        for file_entry in context.files:
            # FileDataStore에서 file_id 조회
            store_file_id = self._file_data_store.get_file_id_by_path(file_entry.path)
            
            if store_file_id is None:
                # FileDataStore에 없는 파일 (동기화 깨짐)
                skipped_count += 1
                continue
            
            mapped_count += 1
            # FileDataStore file_id를 사용
            file_entries_map[store_file_id] = file_entry
            
            # 파싱 결과 매핑 (원래 file_id 또는 hash 기반)
            original_id = file_entry.file_id if file_entry.file_id is not None else hash(str(file_entry.path))
            if original_id in context.parse_results:
                file_parse_pairs.append((file_entry, context.parse_results[original_id]))
                file_id_mapping[original_id] = store_file_id
        
        # 매핑 통계 로그
        debug_step(
            self._log_sink,
            "duplicate_detection_file_mapping_stats",
            {
                "fetched_files_count": fetched_files_count,
                "mapped_files_count": mapped_count,
                "skipped_files_count": skipped_count,
                "mapped_ratio": mapped_count / fetched_files_count if fetched_files_count > 0 else 0.0,
                "file_parse_pairs_count": len(file_parse_pairs)
            }
        )
        
        # 매핑 실패율이 너무 높으면 에러 (50% 이상 실패 시)
        if fetched_files_count > 0:
            mapped_ratio = mapped_count / fetched_files_count
            if mapped_ratio < 0.5:
                error_msg = (
                    f"FileDataStore 동기화 실패: "
                    f"조회된 파일 {fetched_files_count}개 중 {mapped_count}개만 매핑됨 "
                    f"(매핑률: {mapped_ratio:.1%}). "
                    f"먼저 스캔을 실행하여 FileDataStore를 채우세요."
                )
                if self._log_sink:
                    self._log_sink.write(LogEntry(
                        timestamp=datetime.now(),
                        level="ERROR",
                        message=error_msg,
                        context={
                            "fetched_files_count": fetched_files_count,
                            "mapped_files_count": mapped_count,
                            "skipped_files_count": skipped_count
                        }
                    ))
                context.error = error_msg
                return context
        
        if len(file_parse_pairs) == 0:
            # 매핑된 파일이 없으면 에러 설정하지 않고 빈 상태로 반환
            # (다음 단계에서 처리)
            pass
        
        # 컨텍스트 업데이트
        context.file_id_mapping = file_id_mapping
        context.file_entries_map = file_entries_map
        context.file_parse_pairs = file_parse_pairs
        
        return context
