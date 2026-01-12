"""중복 탐지 워커 스레드."""
from collections import defaultdict
from datetime import datetime
from enum import Enum
from typing import Optional, TYPE_CHECKING

from PySide6.QtCore import QObject, QThread, Signal

from application.dto.duplicate_detection_request import DuplicateDetectionRequest
from application.dto.duplicate_group_result import DuplicateGroupResult
from application.dto.job_types import JobProgress
from application.dto.log_entry import LogEntry
from application.ports.index_repository import IIndexRepository
from application.ports.log_sink import ILogSink
from application.utils.debug_logger import debug_step
from domain.entities.file_entry import FileEntry
from domain.services.blocking_service import BlockingService
from domain.services.containment_detector import ContainmentDetector
from domain.services.filename_parser import FilenameParser
from domain.value_objects.blocking_group import BlockingGroup
from domain.value_objects.filename_parse_result import FilenameParseResult

if TYPE_CHECKING:
    from gui.models.file_data_store import FileDataStore


class DuplicateJobStage(str, Enum):
    """중복 탐지 Job 단계."""
    
    PARSE_FILENAMES = "parse_filenames"
    """파일명 파싱 단계."""
    
    BLOCKING = "blocking"
    """Blocking (그룹화) 단계."""
    
    RELATION_DETECTION = "relation_detection"
    """포함/버전 관계 판정 단계."""
    
    CONTENT_ANALYSIS = "content_analysis"
    """내용 기반 판정 단계 (해시/유사도)."""
    
    GROUPING = "grouping"
    """중복 그룹 생성 단계."""


class DuplicateDetectionWorker(QThread):
    """중복 탐지 워커 스레드.
    
    QThread를 상속하여 별도 스레드에서 중복 탐지 작업을 수행.
    단계별 진행률 추적 및 취소 지원.
    """
    
    duplicate_completed = Signal(list)
    """중복 탐지 완료 시그널 (DuplicateGroupResult 리스트)."""
    
    duplicate_error = Signal(str)
    """중복 탐지 오류 시그널."""
    
    duplicate_progress = Signal(JobProgress)
    """중복 탐지 진행률 시그널 (JobProgress)."""
    
    def __init__(
        self,
        request: DuplicateDetectionRequest,
        index_repository: Optional[IIndexRepository] = None,
        log_sink: Optional[ILogSink] = None,
        file_data_store: Optional["FileDataStore"] = None,
        parent: Optional[QObject] = None
    ) -> None:
        """중복 탐지 워커 초기화.
        
        Args:
            request: 중복 탐지 요청 DTO.
            index_repository: 인덱스 저장소 (선택적).
            log_sink: 로그 싱크 (선택적).
            file_data_store: 파일 데이터 저장소 (선택적).
            parent: 부모 객체.
        """
        super().__init__(parent)
        self._request = request
        self._index_repository = index_repository
        self._log_sink = log_sink
        self._file_data_store = file_data_store
        self._cancelled = False
        self._current_stage: Optional[DuplicateJobStage] = None
        
        # 도메인 서비스 초기화
        self._filename_parser = FilenameParser(log_sink=log_sink)
        self._blocking_service = BlockingService(filename_parser=self._filename_parser, log_sink=log_sink)
        self._containment_detector = ContainmentDetector(log_sink=log_sink)
    
    def cancel(self) -> None:
        """중복 탐지 취소."""
        debug_step(
            self._log_sink,
            "duplicate_detection_worker_cancel",
            {
                "current_stage": self._current_stage.value if self._current_stage else None
            }
        )
        self._cancelled = True
    
    def run(self) -> None:
        """워커 실행."""
        debug_step(
            self._log_sink,
            "duplicate_detection_worker_run_start",
            {
                "run_id": self._request.run_id,
                "enable_exact": self._request.enable_exact,
                "enable_version": self._request.enable_version,
                "enable_containment": self._request.enable_containment,
                "enable_near": self._request.enable_near,
            }
        )
        
        if not self._index_repository:
            error_msg = "IndexRepository is required for duplicate detection"
            if self._log_sink:
                self._log_sink.write(LogEntry(
                    timestamp=datetime.now(),
                    level="ERROR",
                    message=error_msg,
                    context={}
                ))
            self.duplicate_error.emit(error_msg)
            return
        
        try:
            # 1. 파일명 파싱 단계
            self._current_stage = DuplicateJobStage.PARSE_FILENAMES
            debug_step(
                self._log_sink,
                "duplicate_detection_stage",
                {"stage": self._current_stage.value}
            )
            self._emit_progress(0, None, "파일명 파싱 시작...")
            
            # 페이지네이션으로 파일 목록 가져오기
            all_files: list[FileEntry] = []
            offset = 0
            limit = 200
            parse_results: dict[int, FilenameParseResult] = {}
            
            while True:
                if self._check_cancelled():
                    return
                
                files_batch = self._index_repository.list_files(
                    run_id=self._request.run_id,
                    offset=offset,
                    limit=limit
                )
                
                if not files_batch:
                    break
                
                all_files.extend(files_batch)
                
                # 각 파일에 대해 파일명 파싱
                for file_entry in files_batch:
                    if self._check_cancelled():
                        return
                    
                    parse_result = self._filename_parser.parse(file_entry.path)
                    if file_entry.file_id is not None:
                        parse_results[file_entry.file_id] = parse_result
                    else:
                        # file_id가 없으면 path 기반 해시 사용 (임시)
                        file_id = hash(str(file_entry.path))
                        parse_results[file_id] = parse_result
                
                offset += limit
                self._emit_progress(len(all_files), None, f"파일 로드 및 파싱 중... ({len(all_files)}개)")
            
            if self._check_cancelled():
                return
            
            debug_step(
                self._log_sink,
                "duplicate_detection_files_loaded",
                {
                    "total_files": len(all_files),
                    "parsed_files": len(parse_results)
                }
            )
            
            if len(all_files) == 0:
                # 파일이 없으면 빈 결과 반환
                debug_step(
                    self._log_sink,
                    "duplicate_detection_worker_completed",
                    {"results_count": 0, "reason": "no_files"}
                )
                self.duplicate_completed.emit([])
                return
            
            # FileDataStore file_id로 매핑
            if not self._file_data_store:
                error_msg = "FileDataStore is required for duplicate detection"
                if self._log_sink:
                    self._log_sink.write(LogEntry(
                        timestamp=datetime.now(),
                        level="ERROR",
                        message=error_msg,
                        context={}
                    ))
                self.duplicate_error.emit(error_msg)
                return
            
            fetched_files_count = len(all_files)
            
            # (FileEntry, FilenameParseResult, FileDataStore file_id) 튜플 리스트 생성
            file_parse_pairs: list[tuple[FileEntry, FilenameParseResult]] = []
            file_entries_map: dict[int, FileEntry] = {}  # FileDataStore file_id -> FileEntry
            file_id_mapping: dict[int, int] = {}  # IndexRepository file_id (또는 hash) -> FileDataStore file_id
            mapped_count = 0
            skipped_count = 0
            
            for file_entry in all_files:
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
                if original_id in parse_results:
                    file_parse_pairs.append((file_entry, parse_results[original_id]))
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
                    self.duplicate_error.emit(error_msg)
                    return
            
            if len(file_parse_pairs) == 0:
                # 매핑된 파일이 없으면 빈 결과 반환
                debug_step(
                    self._log_sink,
                    "duplicate_detection_worker_completed",
                    {
                        "results_count": 0,
                        "reason": "no_mapped_files",
                        "fetched_files_count": fetched_files_count,
                        "mapped_files_count": mapped_count
                    }
                )
                self.duplicate_completed.emit([])
                return
            
            # 2. Blocking 단계
            self._current_stage = DuplicateJobStage.BLOCKING
            debug_step(
                self._log_sink,
                "duplicate_detection_stage",
                {"stage": self._current_stage.value}
            )
            self._emit_progress(0, None, "Blocking (그룹화) 시작...")
            
            blocking_groups = self._blocking_service.create_blocking_groups(file_parse_pairs)
            
            if self._check_cancelled():
                return
            
            debug_step(
                self._log_sink,
                "duplicate_detection_blocking_complete",
                {
                    "blocking_groups_count": len(blocking_groups),
                    "total_files": len(file_parse_pairs)
                }
            )
            
            if len(blocking_groups) == 0:
                # Blocking 그룹이 없으면 중복 없음
                debug_step(
                    self._log_sink,
                    "duplicate_detection_worker_completed",
                    {"results_count": 0, "reason": "no_blocking_groups"}
                )
                self.duplicate_completed.emit([])
                return
            
            # 3. 관계 탐지 단계
            self._current_stage = DuplicateJobStage.RELATION_DETECTION
            debug_step(
                self._log_sink,
                "duplicate_detection_stage",
                {"stage": self._current_stage.value}
            )
            self._emit_progress(0, len(blocking_groups), "포함/버전 관계 탐지 시작...")
            
            # 각 BlockingGroup 내에서 containment/version 관계 탐지
            group_results: list[DuplicateGroupResult] = []
            group_id = 0
            
            for idx, blocking_group in enumerate(blocking_groups):
                if self._check_cancelled():
                    return
                
                self._emit_progress(idx, len(blocking_groups), f"관계 탐지 중... ({idx+1}/{len(blocking_groups)})")
                
                # BlockingGroup 내의 파일 ID를 FileDataStore file_id로 변환
                # blocking_group.file_ids는 원래 file_id (IndexRepository 또는 hash)
                # 이를 FileDataStore file_id로 변환해야 함
                store_file_ids: list[int] = []
                group_file_entries: dict[int, FileEntry] = {}  # FileDataStore file_id -> FileEntry
                group_parse_results: dict[int, FilenameParseResult] = {}  # FileDataStore file_id -> ParseResult
                
                for original_id in blocking_group.file_ids:
                    # FileDataStore file_id로 변환
                    store_file_id = file_id_mapping.get(original_id)
                    if store_file_id is None:
                        continue
                    
                    store_file_ids.append(store_file_id)
                    if store_file_id in file_entries_map:
                        group_file_entries[store_file_id] = file_entries_map[store_file_id]
                    if original_id in parse_results:
                        group_parse_results[store_file_id] = parse_results[original_id]
                
                if len(store_file_ids) < 2:
                    # 그룹에 파일이 2개 미만이면 스킵
                    continue
                
                # 이후 로직은 store_file_ids 사용
                file_ids_list = store_file_ids
                
                # Containment 관계 추적용 (version 탐지 시 중복 방지)
                containment_relations: dict[int, list[int]] = defaultdict(list)  # container_id -> [contained_ids]
                
                # Containment 관계 탐지
                if self._request.enable_containment:
                    for i, file_id_a in enumerate(file_ids_list):
                        if file_id_a not in group_file_entries or file_id_a not in group_parse_results:
                            continue
                        
                        for j, file_id_b in enumerate(file_ids_list):
                            if i >= j or file_id_b not in group_file_entries or file_id_b not in group_parse_results:
                                continue
                            
                            file_a = group_file_entries[file_id_a]
                            parse_a = group_parse_results[file_id_a]
                            file_b = group_file_entries[file_id_b]
                            parse_b = group_parse_results[file_id_b]
                            
                            # Containment 관계 탐지
                            containment_relation = self._containment_detector.detect_containment(
                                file_a, parse_a, file_b, parse_b
                            )
                            
                            if containment_relation:
                                # containment_relation의 file_id는 file_a.file_id와 file_b.file_id이므로
                                # file_id_mapping을 통해 FileDataStore file_id로 변환
                                container_store_id = file_id_mapping.get(containment_relation.container_file_id)
                                contained_store_id = file_id_mapping.get(containment_relation.contained_file_id)
                                
                                if container_store_id is None or contained_store_id is None:
                                    continue
                                
                                containment_relations[container_store_id].append(contained_store_id)
                
                # Containment 그룹 생성 (container 기준으로 묶기)
                # 동일 container에 대해 여러 contained를 하나의 그룹으로 묶어 결과 폭증 방지
                if self._request.enable_containment:
                    for container_store_id, contained_store_ids in containment_relations.items():
                        if not contained_store_ids:
                            continue
                        
                        # container와 모든 contained를 하나의 그룹으로 묶기
                        group_id += 1
                        containment_group = [container_store_id] + contained_store_ids
                        group_result = DuplicateGroupResult(
                            group_id=group_id,
                            duplicate_type="containment",
                            file_ids=containment_group,
                            recommended_keeper_id=container_store_id,
                            evidence={"contained_count": len(contained_store_ids)},
                            confidence=0.9  # containment는 높은 신뢰도
                        )
                        group_results.append(group_result)
                
                # Version 관계 탐지
                if self._request.enable_version:
                    for i, file_id_a in enumerate(file_ids_list):
                        if file_id_a not in group_file_entries or file_id_a not in group_parse_results:
                            continue
                        
                        for j, file_id_b in enumerate(file_ids_list):
                            if i >= j or file_id_b not in group_file_entries or file_id_b not in group_parse_results:
                                continue
                            
                            # 이미 containment 관계가 있으면 스킵
                            if file_id_a in containment_relations.get(file_id_b, []):
                                continue
                            if file_id_b in containment_relations.get(file_id_a, []):
                                continue
                            
                            file_a = group_file_entries[file_id_a]
                            parse_a = group_parse_results[file_id_a]
                            file_b = group_file_entries[file_id_b]
                            parse_b = group_parse_results[file_id_b]
                            
                            # Version 관계 탐지
                            version_relation = self._containment_detector.detect_version(
                                file_a, parse_a, file_b, parse_b
                            )
                            
                            if version_relation:
                                # version_relation의 file_id는 원래 file_id이므로 FileDataStore file_id로 변환
                                newer_store_id = file_id_mapping.get(version_relation.newer_file_id)
                                older_store_id = file_id_mapping.get(version_relation.older_file_id)
                                
                                if newer_store_id is None or older_store_id is None:
                                    continue
                                
                                # Version 그룹 생성 (FileDataStore file_id 사용)
                                group_id += 1
                                version_group = [newer_store_id, older_store_id]
                                group_result = DuplicateGroupResult(
                                    group_id=group_id,
                                    duplicate_type="version",
                                    file_ids=version_group,
                                    recommended_keeper_id=newer_store_id,
                                    evidence=version_relation.evidence,
                                    confidence=version_relation.confidence
                                )
                                group_results.append(group_result)
                
                # Exact/Near는 v2 기능이므로 지금은 스킵
                # TODO: enable_exact/enable_near 플래그 처리 (IHashService 필요)
            
            if self._check_cancelled():
                return
            
            # 4. 내용 기반 판정 단계 (Exact/Near - v2 기능, 현재는 스킵)
            if self._request.enable_exact or self._request.enable_near:
                self._current_stage = DuplicateJobStage.CONTENT_ANALYSIS
                debug_step(
                    self._log_sink,
                    "duplicate_detection_stage",
                    {"stage": self._current_stage.value}
                )
                self._emit_progress(0, None, "내용 기반 판정 시작...")
                
                # TODO: ExactDuplicateDetector/NearDuplicateDetector 구현
                # IHashService 필요
                debug_step(
                    self._log_sink,
                    "duplicate_detection_content_analysis_skipped",
                    {"reason": "not_implemented_yet"}
                )
            
            # 5. 그룹 생성 단계 (완료)
            self._current_stage = DuplicateJobStage.GROUPING
            debug_step(
                self._log_sink,
                "duplicate_detection_stage",
                {"stage": self._current_stage.value}
            )
            self._emit_progress(0, None, "중복 그룹 생성 완료...")
            
            if not self._cancelled:
                debug_step(
                    self._log_sink,
                    "duplicate_detection_worker_completed",
                    {
                        "results_count": len(group_results),
                        "blocking_groups_count": len(blocking_groups),
                        "fetched_files_count": fetched_files_count,
                        "mapped_files_count": mapped_count,
                        "file_parse_pairs_count": len(file_parse_pairs)
                    }
                )
                self.duplicate_completed.emit(group_results)
        except Exception as e:
            if not self._cancelled:
                # 로그 기록
                if self._log_sink:
                    self._log_sink.write(LogEntry(
                        timestamp=datetime.now(),
                        level="ERROR",
                        message=f"Duplicate detection failed: {e}",
                        context={
                            "error_type": type(e).__name__,
                            "stage": self._current_stage.value if self._current_stage else None
                        }
                    ))
                    debug_step(
                        self._log_sink,
                        "duplicate_detection_worker_error",
                        {
                            "error": str(e),
                            "error_type": type(e).__name__,
                            "stage": self._current_stage.value if self._current_stage else None,
                        }
                    )
                self.duplicate_error.emit(str(e))
    
    def _emit_progress(self, processed: int, total: Optional[int], message: str) -> None:
        """진행률 시그널 발생.
        
        Args:
            processed: 처리된 항목 수.
            total: 총 항목 수 (None이면 미정).
            message: 진행 메시지.
        """
        if not self._cancelled:
            progress = JobProgress(
                processed=processed,
                total=total,
                message=message
            )
            self.duplicate_progress.emit(progress)
    
    def _check_cancelled(self) -> bool:
        """취소 여부 확인.
        
        Returns:
            취소되었으면 True.
        """
        return self._cancelled
