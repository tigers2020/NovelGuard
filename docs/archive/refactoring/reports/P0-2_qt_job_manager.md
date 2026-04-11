# 리팩토링 보고서: qt_job_manager.py

> **우선순위**: P0-2 (최우선)  
> **파일**: `src/gui/services/qt_job_manager.py`  
> **작성일**: 2025-01-11  
> **상태**: 분석 완료, 리팩토링 대기

---

## 1. 파일 개요 및 현황

### 1.1 기본 정보
- **LOC**: 477 lines
- **클래스 수**: 1개 (`QtJobManager`)
- **메서드 수**: 약 15개
- **의존성**: 18개 import (Qt, Application DTOs, Workers)

### 1.2 현재 구조
```python
class QtJobManager(QObject):
    - __init__()
    - set_file_data_store()
    - start_scan()                    # Worker 생성 + 이벤트 발생
    - start_duplicate_detection()     # Worker 생성 + 이벤트 발생
    - cancel()
    - get_status()
    - subscribe()
    - _on_scan_completed()           # 이벤트 핸들러
    - _on_scan_error()               # 이벤트 핸들러
    - _on_scan_progress()            # 이벤트 핸들러
    - _on_duplicate_completed()      # 이벤트 핸들러
    - _on_duplicate_error()          # 이벤트 핸들러
    - _on_duplicate_progress()       # 이벤트 핸들러
    - _emit_event()                  # 이벤트 발생
```

### 1.3 주요 책임 (현재 혼재됨)
1. **Job 수명주기 관리**: 생성, 시작, 취소, 상태 추적
2. **Worker 생성 및 관리**: ScanWorker, DuplicateDetectionWorker 생성
3. **이벤트 오케스트레이션**: Signal/Slot 연결, 이벤트 발생
4. **상태 관리**: Job 상태 추적 (`_job_status`, `_job_types`)
5. **이벤트 리스너 관리**: 구독/발행 패턴

---

## 2. 문제점 분석

### 2.1 Job 오케스트레이션 결합도
**현재 문제**:
- `start_scan()`과 `start_duplicate_detection()` 메서드가 **동일한 패턴 반복**
  - Worker 생성 (lines 113-119, 176-182)
  - 시그널 연결 (lines 122-124, 185-187)
  - Job 저장 (lines 127-129, 190-192)
  - 이벤트 발생 (lines 132-139, 195-202)
  - Worker 시작 (lines 142, 205)
- 각 Job 타입별로 핸들러 메서드가 중복 (`_on_scan_*`, `_on_duplicate_*`)
- 새로운 Job 타입 추가 시 코드 중복 발생

**영향**:
- 코드 중복: 동일 패턴 반복 (DRY 위반)
- 확장성 부족: 새로운 Job 타입 추가 시 여러 메서드 수정 필요
- 테스트 어려움: Worker 생성 로직이 Manager에 결합

### 2.2 Worker 생성 책임 혼재
**현재 구조**:
```
QtJobManager
  ├─ Worker 생성 (ScanWorker, DuplicateDetectionWorker)
  ├─ 의존성 주입 (index_repository, log_sink, file_data_store)
  └─ Worker 실행
```

**문제**:
- Manager가 Worker의 생성자를 직접 알고 있음 (의존성 결합)
- Worker 생성 시 필요한 의존성을 Manager가 직접 전달
- Worker 타입별 생성 로직이 Manager에 하드코딩

### 2.3 이벤트 핸들러 중복
**현재 구조**:
- `_on_scan_completed()` vs `_on_duplicate_completed()` (거의 동일)
- `_on_scan_error()` vs `_on_duplicate_error()` (거의 동일)
- `_on_scan_progress()` vs `_on_duplicate_progress()` (거의 동일)

**문제**:
- 동일한 패턴 반복 (Job 타입만 다름)
- 새로운 Job 타입 추가 시 핸들러 메서드 3개 추가 필요

### 2.4 UI 업데이트 정책 섞임 가능성
**위험**:
- Manager가 Signal을 emit하지만, "어떤 시그널을 얼마나 자주 쏠지" 정책이 Manager 내부에 있을 수 있음
- 배치 업데이트 정책이 Manager에 하드코딩되어 있을 가능성

---

## 3. 리팩토링 목표

### 3.1 핵심 목표
1. **Worker Factory 분리**: Worker 생성 로직을 Factory로 추출
2. **이벤트 핸들러 통합**: Job 타입별 핸들러를 제네릭 핸들러로 통합
3. **Job 오케스트레이션 단순화**: 공통 패턴을 추상화
4. **의존성 주입 개선**: Manager가 Worker 생성자에 직접 의존하지 않도록

### 3.2 원칙
- **Factory Pattern**: Worker 생성을 Factory로 위임
- **Strategy Pattern**: Job 타입별 전략 분리
- **Template Method**: 공통 패턴을 템플릿 메서드로 추상화

---

## 4. 구체적인 리팩토링 계획

### 4.1 새로운 파일 구조

```
src/
├── gui/
│   ├── services/
│   │   ├── qt_job_manager.py              # 리팩토링 (200 lines 이하로 축소)
│   │   └── factories/
│   │       ├── __init__.py
│   │       ├── worker_factory.py          # 새 파일
│   │       └── scan_worker_factory.py     # 새 파일
│   │       └── duplicate_worker_factory.py # 새 파일
│   │
│   └── workers/
│       ├── base_worker.py                 # 새 파일 (공통 인터페이스)
│       ├── scan_worker.py
│       └── duplicate_detection_worker.py
```

### 4.2 클래스 설계

#### 4.2.1 `IWorker` 인터페이스 (공통 인터페이스)

```python
# gui/workers/base_worker.py

from abc import ABC, abstractmethod
from typing import Protocol

class IWorker(Protocol):
    """Worker 인터페이스."""
    
    def cancel(self) -> None:
        """작업 취소."""
        ...
    
    def isRunning(self) -> bool:
        """실행 중 여부."""
        ...
    
    def start(self) -> None:
        """작업 시작."""
        ...
    
    def wait(self, timeout: int = 0) -> bool:
        """작업 완료 대기."""
        ...


class WorkerSignals(QObject):
    """Worker 시그널 공통 인터페이스."""
    
    completed = Signal(object)  # result
    error = Signal(str)
    progress = Signal(object)  # JobProgress 또는 (int, str)
```

#### 4.2.2 `IWorkerFactory` 인터페이스 (Worker Factory)

```python
# gui/services/factories/worker_factory.py

from abc import ABC, abstractmethod
from typing import Protocol

class IWorkerFactory(Protocol):
    """Worker Factory 인터페이스."""
    
    @abstractmethod
    def create_worker(
        self,
        request: object,
        **kwargs
    ) -> IWorker:
        """Worker 생성.
        
        Args:
            request: Job 요청 DTO.
            **kwargs: 추가 파라미터.
        
        Returns:
            생성된 Worker.
        """
        ...


class ScanWorkerFactory:
    """Scan Worker Factory."""
    
    def __init__(
        self,
        scanner: FileScanner,
        index_repository: Optional[IIndexRepository] = None,
        log_sink: Optional[ILogSink] = None
    ):
        self._scanner = scanner
        self._index_repository = index_repository
        self._log_sink = log_sink
    
    def create_worker(
        self,
        request: ScanRequest,
        parent: Optional[QObject] = None
    ) -> ScanWorker:
        """Scan Worker 생성."""
        return ScanWorker(
            self._scanner,
            request,
            index_repository=self._index_repository,
            log_sink=self._log_sink,
            parent=parent
        )


class DuplicateWorkerFactory:
    """Duplicate Detection Worker Factory."""
    
    def __init__(
        self,
        index_repository: Optional[IIndexRepository] = None,
        log_sink: Optional[ILogSink] = None,
        file_data_store: Optional[FileDataStore] = None
    ):
        self._index_repository = index_repository
        self._log_sink = log_sink
        self._file_data_store = file_data_store
    
    def create_worker(
        self,
        request: DuplicateDetectionRequest,
        parent: Optional[QObject] = None
    ) -> DuplicateDetectionWorker:
        """Duplicate Detection Worker 생성."""
        return DuplicateDetectionWorker(
            request,
            index_repository=self._index_repository,
            log_sink=self._log_sink,
            file_data_store=self._file_data_store,
            parent=parent
        )
```

#### 4.2.3 리팩토링된 `QtJobManager`

```python
# gui/services/qt_job_manager.py (리팩토링 후)

class QtJobManager(QObject):
    """Qt Job Manager - IJobRunner 구현."""
    
    job_started = Signal(int, JobType)
    job_progress = Signal(int, JobProgress)
    job_completed = Signal(int, object)
    job_failed = Signal(int, str)
    job_cancelled = Signal(int)
    
    def __init__(
        self,
        worker_factories: dict[JobType, IWorkerFactory],
        parent: Optional[QObject] = None
    ) -> None:
        """Qt Job Manager 초기화.
        
        Args:
            worker_factories: Job 타입별 Worker Factory 맵.
            parent: 부모 객체.
        """
        super().__init__(parent)
        self._worker_factories = worker_factories
        
        # Job 관리
        self._next_job_id = 1
        self._jobs: dict[int, IWorker] = {}
        self._job_types: dict[int, JobType] = {}
        self._job_status: dict[int, JobStatus] = {}
        self._listeners: list[Callable[[JobEvent], None]] = []
    
    def start_scan(self, request: ScanRequest) -> int:
        """스캔 작업 시작."""
        return self._start_job(JobType.SCAN, request)
    
    def start_duplicate_detection(self, request: DuplicateDetectionRequest) -> int:
        """중복 탐지 작업 시작."""
        return self._start_job(JobType.DUPLICATE, request)
    
    def _start_job(self, job_type: JobType, request: object) -> int:
        """Job 시작 (공통 패턴).
        
        Args:
            job_type: Job 타입.
            request: Job 요청 DTO.
        
        Returns:
            Job ID.
        """
        job_id = self._next_job_id
        self._next_job_id += 1
        
        # Factory에서 Worker 생성
        factory = self._worker_factories.get(job_type)
        if not factory:
            raise ValueError(f"Worker factory not found for job type: {job_type}")
        
        worker = factory.create_worker(request, parent=self)
        
        # 시그널 연결 (공통 핸들러 사용)
        self._connect_worker_signals(job_id, job_type, worker)
        
        # Job 저장
        self._jobs[job_id] = worker
        self._job_types[job_id] = job_type
        self._job_status[job_id] = JobStatus.RUNNING
        
        # 이벤트 발생
        self._emit_job_event(
            job_id,
            job_type,
            "started",
            {"request": request}
        )
        self.job_started.emit(job_id, job_type)
        
        # Worker 시작
        worker.start()
        
        return job_id
    
    def _connect_worker_signals(
        self,
        job_id: int,
        job_type: JobType,
        worker: IWorker
    ) -> None:
        """Worker 시그널 연결 (공통 핸들러).
        
        Args:
            job_id: Job ID.
            job_type: Job 타입.
            worker: Worker 인스턴스.
        """
        # completed 시그널 연결 (타입별 처리)
        if hasattr(worker, 'scan_completed'):
            worker.scan_completed.connect(
                lambda result: self._on_job_completed(job_id, job_type, result)
            )
        elif hasattr(worker, 'duplicate_completed'):
            worker.duplicate_completed.connect(
                lambda result: self._on_job_completed(job_id, job_type, result)
            )
        
        # error 시그널 연결
        if hasattr(worker, 'scan_error'):
            worker.scan_error.connect(
                lambda error: self._on_job_error(job_id, job_type, error)
            )
        elif hasattr(worker, 'duplicate_error'):
            worker.duplicate_error.connect(
                lambda error: self._on_job_error(job_id, job_type, error)
            )
        
        # progress 시그널 연결
        if hasattr(worker, 'scan_progress'):
            worker.scan_progress.connect(
                lambda count, msg: self._on_job_progress(job_id, job_type, count, msg)
            )
        elif hasattr(worker, 'duplicate_progress'):
            worker.duplicate_progress.connect(
                lambda progress: self._on_job_progress(job_id, job_type, progress)
            )
    
    def _on_job_completed(
        self,
        job_id: int,
        job_type: JobType,
        result: object
    ) -> None:
        """Job 완료 핸들러 (공통).
        
        Args:
            job_id: Job ID.
            job_type: Job 타입.
            result: Job 결과.
        """
        if job_id not in self._jobs:
            return
        
        self._job_status[job_id] = JobStatus.COMPLETED
        
        self._emit_job_event(
            job_id,
            job_type,
            "completed",
            {"result": result}
        )
        self.job_completed.emit(job_id, result)
    
    def _on_job_error(
        self,
        job_id: int,
        job_type: JobType,
        error: str
    ) -> None:
        """Job 에러 핸들러 (공통).
        
        Args:
            job_id: Job ID.
            job_type: Job 타입.
            error: 에러 메시지.
        """
        if job_id not in self._jobs:
            return
        
        self._job_status[job_id] = JobStatus.FAILED
        
        self._emit_job_event(
            job_id,
            job_type,
            "failed",
            {"error": error}
        )
        self.job_failed.emit(job_id, error)
    
    def _on_job_progress(
        self,
        job_id: int,
        job_type: JobType,
        progress: Union[JobProgress, tuple]
    ) -> None:
        """Job 진행률 핸들러 (공통).
        
        Args:
            job_id: Job ID.
            job_type: Job 타입.
            progress: 진행률 정보 (JobProgress 또는 (int, str)).
        """
        # 타입별 JobProgress 변환
        if isinstance(progress, tuple):
            count, message = progress
            job_progress = JobProgress(
                processed=count,
                total=None,
                message=message
            )
        else:
            job_progress = progress
        
        self._emit_job_event(
            job_id,
            job_type,
            "progress",
            {"progress": job_progress}
        )
        self.job_progress.emit(job_id, job_progress)
    
    def _emit_job_event(
        self,
        job_id: int,
        job_type: JobType,
        event_type: str,
        data: dict
    ) -> None:
        """Job 이벤트 발생.
        
        Args:
            job_id: Job ID.
            job_type: Job 타입.
            event_type: 이벤트 타입.
            data: 이벤트 데이터.
        """
        event = JobEvent(
            job_id=job_id,
            job_type=job_type,
            event_type=event_type,
            data=data
        )
        self._emit_event(event)
    
    # 기존 메서드들 유지 (cancel, get_status, subscribe, _emit_event)
    ...
```

---

## 5. 단계별 작업 계획

### Phase 1: Worker Factory 구조 설계
- [ ] `IWorker` Protocol 정의
- [ ] `IWorkerFactory` Protocol 정의
- [ ] `ScanWorkerFactory` 생성
- [ ] `DuplicateWorkerFactory` 생성
- [ ] 단위 테스트 작성

### Phase 2: Manager 리팩토링
- [ ] `_start_job()` 공통 메서드 추출
- [ ] `_connect_worker_signals()` 공통 메서드 추출
- [ ] `_on_job_*()` 공통 핸들러 생성
- [ ] 기존 `start_scan()`, `start_duplicate_detection()` 간소화

### Phase 3: 통합 테스트 및 검증
- [ ] 기존 통합 테스트 실행하여 동작 확인
- [ ] Factory 주입 테스트
- [ ] 코드 리뷰 및 정리

### Phase 4: 정리 및 문서화
- [ ] 사용하지 않는 코드 제거
- [ ] 문서 업데이트
- [ ] 커밋 및 PR 생성

---

## 6. 예상 효과

### 6.1 코드 품질
- **중복 제거**: `start_scan()`과 `start_duplicate_detection()` 공통 패턴 추출
- **확장성**: 새로운 Job 타입 추가 시 Factory만 추가하면 됨
- **테스트 가능성**: Worker 생성 로직을 독립적으로 테스트 가능

### 6.2 아키텍처 개선
- **의존성 역전**: Manager가 Worker 생성자에 직접 의존하지 않음
- **단일 책임**: Manager는 Job 오케스트레이션만 담당
- **재사용성**: Factory를 다른 컨텍스트에서도 사용 가능

### 6.3 유지보수성
- **코드 길이**: 477 lines → 약 300 lines로 축소
- **복잡도**: 공통 패턴 추출로 복잡도 감소
- **가독성**: 중복 제거로 가독성 향상

---

## 7. 리스크 및 주의사항

### 7.1 주요 리스크
1. **Signal 연결 타입 안전성**: `hasattr()` 기반 동적 연결은 타입 안전하지 않음
2. **기존 통합 테스트 실패 가능성**: Manager 생성자 변경 시 테스트 수정 필요
3. **Factory 주입 복잡도**: 초기화 시 Factory 생성 필요

### 7.2 완화 방안
- Signal 연결은 Protocol 또는 ABC로 타입 안전하게 처리
- 기존 통합 테스트를 유지하며 점진적 전환
- Factory 생성 헬퍼 함수 제공

---

## 8. 체크리스트

### 8.1 코드 작성
- [ ] `IWorker` Protocol 작성
- [ ] `IWorkerFactory` Protocol 작성
- [ ] `ScanWorkerFactory` 작성
- [ ] `DuplicateWorkerFactory` 작성
- [ ] `QtJobManager` 리팩토링

### 8.2 테스트
- [ ] Factory 단위 테스트 작성
- [ ] Manager 통합 테스트 작성
- [ ] 기존 통합 테스트 통과 확인

### 8.3 문서화
- [ ] 클래스 docstring 작성
- [ ] 메서드 docstring 작성
- [ ] 아키텍처 문서 업데이트

### 8.4 코드 품질
- [ ] 타입 힌팅 적용
- [ ] Linter 통과
- [ ] 코드 리뷰 완료

---

## 9. 참고 사항

### 9.1 관련 파일
- `application/ports/job_runner.py`: IJobRunner Protocol 참고
- `gui/workers/scan_worker.py`: Worker 패턴 참고
- `gui/workers/duplicate_detection_worker.py`: Worker 패턴 참고

### 9.2 설계 패턴
- **Factory Pattern**: Worker 생성 위임
- **Strategy Pattern**: Job 타입별 전략 분리
- **Template Method Pattern**: 공통 패턴 추상화

---

**작성자**: NovelGuard 개발팀  
**검토 상태**: 대기 중  
**다음 단계**: Phase 1 시작
