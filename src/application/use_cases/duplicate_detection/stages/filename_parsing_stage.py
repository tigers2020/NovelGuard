"""파일명 파싱 단계."""
from datetime import datetime
from typing import Optional

from application.dto.log_entry import LogEntry
from application.ports.index_repository import IIndexRepository
from application.ports.log_sink import ILogSink
from application.use_cases.duplicate_detection.stages.base_stage import (
    PipelineContext,
    PipelineStage
)
from application.utils.debug_logger import debug_step
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
        log_sink: Optional[ILogSink] = None
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
        debug_step(
            self._log_sink,
            "duplicate_detection_stage",
            {"stage": self.name}
        )
        
        # 페이지네이션으로 파일 목록 가져오기
        from domain.entities.file_entry import FileEntry
        
        all_files: list[FileEntry] = []
        offset = 0
        limit = 200
        parse_results: dict[int, FilenameParseResult] = {}
        
        while True:
            files_batch = self._index_repository.list_files(
                run_id=context.request.run_id,
                offset=offset,
                limit=limit
            )
            
            if not files_batch:
                break
            
            all_files.extend(files_batch)
            
            # 각 파일에 대해 파일명 파싱
            for file_entry in files_batch:
                try:
                    parse_result = self._filename_parser.parse(file_entry.path)
                    if file_entry.file_id is not None:
                        parse_results[file_entry.file_id] = parse_result
                    else:
                        # file_id가 없으면 path 기반 해시 사용 (임시)
                        file_id = hash(str(file_entry.path))
                        parse_results[file_id] = parse_result
                except (ValueError, Exception) as e:
                    # 파싱 중 검증 오류 발생 시 해당 파일 스킵
                    # (예: 잘못된 범위 "275-99" 같은 경우)
                    if self._log_sink:
                        self._log_sink.write(LogEntry(
                            timestamp=datetime.now(),
                            level="WARN",
                            message=f"파일명 파싱 실패 (스킵): {file_entry.path} - {e}",
                            context={
                                "file_path": str(file_entry.path),
                                "error_type": type(e).__name__,
                                "error": str(e)
                            }
                        ))
                    # 파싱 실패한 파일은 parse_results에 포함하지 않음
                    continue
            
            offset += limit
        
        # 컨텍스트 업데이트
        context.files = all_files
        context.parse_results = parse_results
        
        debug_step(
            self._log_sink,
            "duplicate_detection_files_loaded",
            {
                "total_files": len(all_files),
                "parsed_files": len(parse_results)
            }
        )
        
        # 파일이 없으면 에러 설정하지 않고 빈 상태로 반환
        # (다음 단계에서 처리)
        
        return context
