"""중복 파일 정리 탭 ViewModel."""
from typing import Optional

from PySide6.QtCore import QObject, Signal

from application.dto.duplicate_detection_request import DuplicateDetectionRequest
from application.dto.duplicate_group_result import DuplicateGroupResult
from application.dto.job_types import JobProgress, JobType
from application.ports.index_repository import IIndexRepository
from application.ports.job_runner import IJobRunner
from application.ports.log_sink import ILogSink
from application.utils.debug_logger import debug_step
from gui.view_models.base_view_model import BaseViewModel


class DuplicateViewModel(BaseViewModel):
    """중복 파일 정리 탭 ViewModel."""
    
    # 신규 시그널 추가
    results_updated = Signal()  # results 변경 시 발생
    group_selected = Signal(int)  # group_id 선택 시 발생
    duplicate_completed = Signal(list)  # 중복 탐지 완료 시그널 (DuplicateGroupResult 리스트)
    duplicate_error = Signal(str)  # 중복 탐지 오류 시그널
    
    def __init__(
        self,
        parent: Optional[QObject] = None,
        job_manager: Optional[IJobRunner] = None,
        index_repository: Optional[IIndexRepository] = None,
        log_sink: Optional[ILogSink] = None
    ) -> None:
        """중복 ViewModel 초기화.
        
        Args:
            parent: 부모 객체.
            job_manager: Job 관리자 (선택적).
            index_repository: 인덱스 저장소 (선택적).
            log_sink: 로그 싱크 (선택적).
        """
        super().__init__(parent)
        
        # 의존성 저장
        self._job_manager = job_manager
        self._index_repository = index_repository
        self._log_sink = log_sink
        
        # 상태
        self._is_detecting: bool = False
        self._progress_count: int = 0
        self._progress_message: str = ""
        
        # 결과 저장 (메모리 보관)
        self._results: list[DuplicateGroupResult] = []
        self._selected_group_id: Optional[int] = None
        
        # Job ID
        self._current_job_id: Optional[int] = None
        
        # JobManager 시그널 연결 (QtJobManager인 경우)
        if job_manager and hasattr(job_manager, 'job_started'):
            job_manager.job_started.connect(self._on_job_started)
            job_manager.job_progress.connect(self._on_job_progress)
            job_manager.job_completed.connect(self._on_job_completed)
            job_manager.job_failed.connect(self._on_job_failed)
            job_manager.job_cancelled.connect(self._on_job_cancelled)
    
    def load_data(self) -> None:
        """데이터 로드."""
        # 현재는 결과가 메모리에만 있으므로 로드할 데이터 없음
        pass
    
    @property
    def results(self) -> list[DuplicateGroupResult]:
        """중복 그룹 결과 리스트 반환 (읽기 전용)."""
        return self._results.copy()
    
    @property
    def selected_group_id(self) -> Optional[int]:
        """선택된 그룹 ID 반환."""
        return self._selected_group_id
    
    @selected_group_id.setter
    def selected_group_id(self, value: Optional[int]) -> None:
        """선택된 그룹 ID 설정.
        
        Args:
            value: 그룹 ID (None이면 선택 해제).
        """
        if self._selected_group_id != value:
            self._selected_group_id = value
            if value is not None:
                self.group_selected.emit(value)
            self.data_changed.emit()
    
    @property
    def is_detecting(self) -> bool:
        """중복 탐지 중 여부 반환."""
        return self._is_detecting
    
    @property
    def progress_count(self) -> int:
        """진행 파일 수 반환."""
        return self._progress_count
    
    @property
    def progress_message(self) -> str:
        """진행 메시지 반환."""
        return self._progress_message
    
    def get_group_by_id(self, group_id: int) -> Optional[DuplicateGroupResult]:
        """그룹 ID로 결과 찾기.
        
        Args:
            group_id: 그룹 ID.
            
        Returns:
            DuplicateGroupResult. 없으면 None.
        """
        for result in self._results:
            if result.group_id == group_id:
                return result
        return None
    
    def _on_job_started(self, job_id: int, job_type: JobType) -> None:
        """Job 시작 핸들러.
        
        Args:
            job_id: Job ID.
            job_type: Job 타입.
        """
        debug_step(
            self._log_sink,
            "duplicate_view_model_job_started",
            {"job_id": job_id, "job_type": job_type.value}
        )
        
        if job_type != JobType.DUPLICATE:
            return
        
        self._current_job_id = job_id
        self._is_detecting = True
        self._progress_count = 0
        self._progress_message = "중복 탐지 시작 중..."
        self.data_changed.emit()
        self.progress_updated.emit(0, "중복 탐지 시작 중...")
    
    def _on_job_progress(self, job_id: int, progress: JobProgress) -> None:
        """Job 진행률 핸들러.
        
        Args:
            job_id: Job ID.
            progress: 진행률 정보.
        """
        if job_id != self._current_job_id:
            return
        
        self._progress_count = progress.processed
        self._progress_message = progress.message
        self.progress_updated.emit(0, progress.message)  # 0은 indeterminate 의미
    
    def _on_job_completed(self, job_id: int, result: object) -> None:
        """Job 완료 핸들러.
        
        Args:
            job_id: Job ID.
            result: 중복 탐지 결과 (list[DuplicateGroupResult]).
        """
        debug_step(
            self._log_sink,
            "duplicate_view_model_job_completed",
            {
                "job_id": job_id,
                "result_type": type(result).__name__,
                "is_list": isinstance(result, list),
            }
        )
        
        if job_id != self._current_job_id:
            return
        
        # result는 list[DuplicateGroupResult] 타입
        if not isinstance(result, list):
            return
        
        results: list[DuplicateGroupResult] = result
        self._results = results
        self._is_detecting = False
        self._progress_count = len(results)
        self._progress_message = f"중복 탐지 완료: {len(results)}개 그룹"
        self.data_changed.emit()
        self.progress_updated.emit(0, self._progress_message)
        self.results_updated.emit()
        self.duplicate_completed.emit(results)
        
        debug_step(
            self._log_sink,
            "duplicate_view_model_job_completed_final",
            {"results_count": len(results)}
        )
    
    def _on_job_failed(self, job_id: int, error: str) -> None:
        """Job 실패 핸들러.
        
        Args:
            job_id: Job ID.
            error: 에러 메시지.
        """
        debug_step(
            self._log_sink,
            "duplicate_view_model_job_failed",
            {"job_id": job_id, "error": error}
        )
        
        if job_id != self._current_job_id:
            return
        
        self._is_detecting = False
        self._progress_message = f"오류: {error}"
        self.data_changed.emit()
        self.error_occurred.emit(error)
        self.duplicate_error.emit(error)
    
    def _on_job_cancelled(self, job_id: int) -> None:
        """Job 취소 핸들러.
        
        Args:
            job_id: Job ID.
        """
        debug_step(
            self._log_sink,
            "duplicate_view_model_job_cancelled",
            {"job_id": job_id}
        )
        
        if job_id != self._current_job_id:
            return
        
        self._is_detecting = False
        self._progress_message = "중복 탐지 중지됨"
        self.data_changed.emit()
        self.progress_updated.emit(0, "중복 탐지 중지됨")
    
    def start_duplicate_detection(self) -> None:
        """중복 탐지 시작.
        
        최신 run_id를 조회하여 중복 탐지 요청을 생성하고 JobManager에 전달.
        """
        debug_step(
            self._log_sink,
            "duplicate_view_model_start_detection",
            {
                "has_job_manager": self._job_manager is not None,
                "has_index_repository": self._index_repository is not None,
                "is_detecting": self._is_detecting,
            }
        )
        
        if not self._job_manager:
            self.duplicate_error.emit("Job Manager가 설정되지 않았습니다")
            return
        
        if not self._index_repository:
            self.duplicate_error.emit("Index Repository가 설정되지 않았습니다")
            return
        
        if self._is_detecting:
            # 이미 탐지 중이면 무시
            return
        
        try:
            # 최신 run_id 조회
            latest_run_id = self._index_repository.get_latest_run_id()
            if not latest_run_id:
                self.duplicate_error.emit("스캔 결과가 없습니다. 먼저 스캔을 실행하세요")
                return
            
            debug_step(
                self._log_sink,
                "duplicate_view_model_latest_run_id",
                {"latest_run_id": latest_run_id}
            )
            
            # 중복 탐지 요청 생성
            request = DuplicateDetectionRequest(
                run_id=latest_run_id,
                enable_exact=True,
                enable_near=False  # Phase A에서는 near는 비활성화
            )
            
            # JobManager에 전달 (start_duplicate_detection 메서드 필요)
            if hasattr(self._job_manager, 'start_duplicate_detection'):
                job_id = self._job_manager.start_duplicate_detection(request)
                debug_step(
                    self._log_sink,
                    "duplicate_view_model_detection_started",
                    {"job_id": job_id}
                )
                # job_id는 _on_job_started에서 처리됨
            else:
                self.duplicate_error.emit("Job Manager가 중복 탐지를 지원하지 않습니다")
        except Exception as e:
            debug_step(
                self._log_sink,
                "duplicate_view_model_detection_error",
                {"error": str(e), "error_type": type(e).__name__}
            )
            self.duplicate_error.emit(f"중복 탐지 시작 실패: {e}")
