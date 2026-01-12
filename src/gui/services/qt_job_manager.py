"""Qt Job Manager 구현."""
from typing import Callable, Optional, TYPE_CHECKING

from PySide6.QtCore import QObject, Signal

from application.dto.duplicate_detection_request import DuplicateDetectionRequest
from application.dto.duplicate_group_result import DuplicateGroupResult
from application.dto.job_types import JobEvent, JobProgress, JobStatus, JobType
from application.dto.scan_request import ScanRequest
from application.dto.scan_result import ScanResult
from application.ports.file_scanner import FileScanner
from application.ports.index_repository import IIndexRepository
from application.ports.job_runner import IJobRunner
from application.ports.log_sink import ILogSink
from application.utils.debug_logger import debug_step
from application.use_cases.scan_folder import ScanFolderUseCase
from gui.workers.duplicate_detection_worker import DuplicateDetectionWorker
from gui.workers.scan_worker import ScanWorker

if TYPE_CHECKING:
    from gui.models.file_data_store import FileDataStore


class QtJobManager(QObject):
    """Qt Job Manager - IJobRunner 구현.
    
    GUI 레이어의 Job 관리자. QObject를 상속하여 Qt Signal 사용.
    Application 레이어는 IJobRunner Protocol만 알고 QtJobManager는 모름.
    
    IJobRunner Protocol을 구현 (구조적 서브타이핑, 상속 불필요).
    """
    
    # Qt Signals (GUI용)
    job_started = Signal(int, JobType)
    """Job 시작 시그널 (job_id, job_type)."""
    
    job_progress = Signal(int, JobProgress)
    """Job 진행률 시그널 (job_id, progress)."""
    
    job_completed = Signal(int, object)
    """Job 완료 시그널 (job_id, result_ref)."""
    
    job_failed = Signal(int, str)
    """Job 실패 시그널 (job_id, error)."""
    
    job_cancelled = Signal(int)
    """Job 취소 시그널 (job_id)."""
    
    def __init__(
        self,
        scanner: FileScanner,
        index_repository: Optional[IIndexRepository] = None,
        log_sink: Optional[ILogSink] = None,
        file_data_store: Optional["FileDataStore"] = None,
        parent: Optional[QObject] = None
    ) -> None:
        """Qt Job Manager 초기화.
        
        Args:
            scanner: 파일 스캐너 (Port 인터페이스).
            index_repository: 인덱스 저장소 (선택적).
            log_sink: 로그 싱크 (선택적).
            file_data_store: 파일 데이터 저장소 (선택적).
            parent: 부모 객체.
        """
        super().__init__(parent)
        
        self._scanner = scanner
        self._index_repository = index_repository
        self._log_sink = log_sink
        self._file_data_store = file_data_store
        
        # Job 관리
        self._next_job_id = 1
        self._jobs: dict[int, object] = {}  # ScanWorker 또는 DuplicateDetectionWorker
        self._job_types: dict[int, JobType] = {}  # Job 타입 추적
        self._job_status: dict[int, JobStatus] = {}
        
        # 이벤트 리스너
        self._listeners: list[Callable[[JobEvent], None]] = []
    
    def set_file_data_store(self, file_data_store: Optional["FileDataStore"]) -> None:
        """파일 데이터 저장소 설정.
        
        Args:
            file_data_store: 파일 데이터 저장소.
        """
        self._file_data_store = file_data_store
    
    def start_scan(self, request: ScanRequest) -> int:
        """스캔 작업 시작.
        
        Args:
            request: 스캔 요청 DTO.
        
        Returns:
            Job ID.
        """
        job_id = self._next_job_id
        self._next_job_id += 1
        
        debug_step(
            self._log_sink,
            "start_scan",
            {
                "job_id": job_id,
                "root_folder": str(request.root_folder),
                "extensions": request.extensions,
            }
        )
        
        # Worker 생성
        worker = ScanWorker(
            self._scanner,
            request,
            index_repository=self._index_repository,
            log_sink=self._log_sink,
            parent=self
        )
        
        # 시그널 연결
        worker.scan_completed.connect(lambda result: self._on_scan_completed(job_id, result))
        worker.scan_error.connect(lambda error: self._on_scan_error(job_id, error))
        worker.scan_progress.connect(lambda count, msg: self._on_scan_progress(job_id, count, msg))
        
        # Job 저장
        self._jobs[job_id] = worker
        self._job_types[job_id] = JobType.SCAN
        self._job_status[job_id] = JobStatus.RUNNING
        
        # 이벤트 발생
        event = JobEvent(
            job_id=job_id,
            job_type=JobType.SCAN,
            event_type="started",
            data={"request": request}
        )
        self._emit_event(event)
        self.job_started.emit(job_id, JobType.SCAN)
        
        # Worker 시작
        worker.start()
        
        debug_step(
            self._log_sink,
            "start_scan_worker_started",
            {"job_id": job_id}
        )
        
        return job_id
    
    def start_duplicate_detection(self, request: DuplicateDetectionRequest) -> int:
        """중복 탐지 작업 시작.
        
        Args:
            request: 중복 탐지 요청 DTO.
        
        Returns:
            Job ID.
        """
        job_id = self._next_job_id
        self._next_job_id += 1
        
        debug_step(
            self._log_sink,
            "start_duplicate_detection",
            {
                "job_id": job_id,
                "run_id": request.run_id,
                "enable_exact": request.enable_exact,
                "enable_near": request.enable_near,
            }
        )
        
        # Worker 생성
        worker = DuplicateDetectionWorker(
            request,
            index_repository=self._index_repository,
            log_sink=self._log_sink,
            file_data_store=self._file_data_store,
            parent=self
        )
        
        # 시그널 연결
        worker.duplicate_completed.connect(lambda result: self._on_duplicate_completed(job_id, result))
        worker.duplicate_error.connect(lambda error: self._on_duplicate_error(job_id, error))
        worker.duplicate_progress.connect(lambda progress: self._on_duplicate_progress(job_id, progress))
        
        # Job 저장
        self._jobs[job_id] = worker
        self._job_types[job_id] = JobType.DUPLICATE
        self._job_status[job_id] = JobStatus.RUNNING
        
        # 이벤트 발생
        event = JobEvent(
            job_id=job_id,
            job_type=JobType.DUPLICATE,
            event_type="started",
            data={"request": request}
        )
        self._emit_event(event)
        self.job_started.emit(job_id, JobType.DUPLICATE)
        
        # Worker 시작
        worker.start()
        
        debug_step(
            self._log_sink,
            "start_duplicate_detection_worker_started",
            {"job_id": job_id}
        )
        
        return job_id
    
    def cancel(self, job_id: int) -> None:
        """작업 취소.
        
        Args:
            job_id: Job ID.
        """
        debug_step(
            self._log_sink,
            "cancel_job",
            {"job_id": job_id}
        )
        
        if job_id not in self._jobs:
            debug_step(
                self._log_sink,
                "cancel_job_not_found",
                {"job_id": job_id}
            )
            return
        
        worker = self._jobs[job_id]
        job_type = self._job_types.get(job_id, JobType.SCAN)
        
        if worker.isRunning():
            worker.cancel()
            worker.wait(200)  # 최대 200ms 대기
        
        self._job_status[job_id] = JobStatus.CANCELLED
        
        # 이벤트 발생
        event = JobEvent(
            job_id=job_id,
            job_type=job_type,
            event_type="cancelled",
            data={}
        )
        self._emit_event(event)
        self.job_cancelled.emit(job_id)
        
        debug_step(
            self._log_sink,
            "cancel_job_complete",
            {"job_id": job_id, "job_type": job_type.value}
        )
    
    def get_status(self, job_id: int) -> Optional[JobStatus]:
        """작업 상태 조회.
        
        Args:
            job_id: Job ID.
        
        Returns:
            Job 상태. 없으면 None.
        """
        return self._job_status.get(job_id)
    
    def subscribe(self, listener: Callable[[JobEvent], None]) -> None:
        """이벤트 리스너 등록.
        
        Args:
            listener: 이벤트 리스너 함수.
        """
        self._listeners.append(listener)
    
    def _on_scan_completed(self, job_id: int, result: ScanResult) -> None:
        """스캔 완료 핸들러.
        
        Args:
            job_id: Job ID.
            result: 스캔 결과.
        """
        debug_step(
            self._log_sink,
            "on_scan_completed",
            {
                "job_id": job_id,
                "total_files": result.total_files,
                "total_bytes": result.total_bytes,
                "elapsed_ms": result.elapsed_ms,
            }
        )
        
        if job_id not in self._jobs:
            return
        
        self._job_status[job_id] = JobStatus.COMPLETED
        
        # 이벤트 발생
        event = JobEvent(
            job_id=job_id,
            job_type=JobType.SCAN,
            event_type="completed",
            data={"result": result}
        )
        self._emit_event(event)
        self.job_completed.emit(job_id, result)
    
    def _on_scan_error(self, job_id: int, error: str) -> None:
        """스캔 에러 핸들러.
        
        Args:
            job_id: Job ID.
            error: 에러 메시지.
        """
        debug_step(
            self._log_sink,
            "on_scan_error",
            {
                "job_id": job_id,
                "error": error,
            }
        )
        
        if job_id not in self._jobs:
            return
        
        self._job_status[job_id] = JobStatus.FAILED
        
        # 이벤트 발생
        event = JobEvent(
            job_id=job_id,
            job_type=JobType.SCAN,
            event_type="failed",
            data={"error": error}
        )
        self._emit_event(event)
        self.job_failed.emit(job_id, error)
    
    def _on_scan_progress(self, job_id: int, count: int, message: str) -> None:
        """스캔 진행률 핸들러.
        
        Args:
            job_id: Job ID.
            count: 처리된 파일 수.
            message: 진행 메시지.
        """
        # 이벤트 발생
        progress = JobProgress(
            processed=count,
            total=None,  # 스캔은 총량을 미리 알 수 없음
            message=message
        )
        
        event = JobEvent(
            job_id=job_id,
            job_type=JobType.SCAN,
            event_type="progress",
            data={"progress": progress}
        )
        self._emit_event(event)
        self.job_progress.emit(job_id, progress)
    
    def _on_duplicate_completed(self, job_id: int, result: list) -> None:
        """중복 탐지 완료 핸들러.
        
        Args:
            job_id: Job ID.
            result: 중복 탐지 결과 (list[DuplicateGroupResult]).
        """
        debug_step(
            self._log_sink,
            "on_duplicate_completed",
            {
                "job_id": job_id,
                "result_count": len(result),
            }
        )
        
        if job_id not in self._jobs:
            return
        
        self._job_status[job_id] = JobStatus.COMPLETED
        
        # 이벤트 발생
        event = JobEvent(
            job_id=job_id,
            job_type=JobType.DUPLICATE,
            event_type="completed",
            data={"result": result}
        )
        self._emit_event(event)
        self.job_completed.emit(job_id, result)
    
    def _on_duplicate_error(self, job_id: int, error: str) -> None:
        """중복 탐지 에러 핸들러.
        
        Args:
            job_id: Job ID.
            error: 에러 메시지.
        """
        debug_step(
            self._log_sink,
            "on_duplicate_error",
            {
                "job_id": job_id,
                "error": error,
            }
        )
        
        if job_id not in self._jobs:
            return
        
        self._job_status[job_id] = JobStatus.FAILED
        
        # 이벤트 발생
        event = JobEvent(
            job_id=job_id,
            job_type=JobType.DUPLICATE,
            event_type="failed",
            data={"error": error}
        )
        self._emit_event(event)
        self.job_failed.emit(job_id, error)
    
    def _on_duplicate_progress(self, job_id: int, progress: JobProgress) -> None:
        """중복 탐지 진행률 핸들러.
        
        Args:
            job_id: Job ID.
            progress: 진행률 정보.
        """
        # 이벤트 발생
        event = JobEvent(
            job_id=job_id,
            job_type=JobType.DUPLICATE,
            event_type="progress",
            data={"progress": progress}
        )
        self._emit_event(event)
        self.job_progress.emit(job_id, progress)
    
    def _emit_event(self, event: JobEvent) -> None:
        """이벤트 발생 (리스너에게 전달).
        
        Args:
            event: Job 이벤트.
        """
        debug_step(
            self._log_sink,
            "emit_event",
            {
                "job_id": event.job_id,
                "job_type": event.job_type.value,
                "event_type": event.event_type,
                "listeners_count": len(self._listeners),
            }
        )
        
        for listener in self._listeners:
            try:
                listener(event)
            except Exception as e:
                # 리스너 에러는 무시 (로그만 기록)
                if self._log_sink:
                    from application.dto.log_entry import LogEntry
                    from datetime import datetime
                    self._log_sink.write(LogEntry(
                        timestamp=datetime.now(),
                        level="ERROR",
                        message=f"Job event listener error: {e}",
                        context={"error_type": type(e).__name__}
                    ))
