# 리팩토링 보고서: duplicate_detection_worker.py

> **우선순위**: P0-1 (최우선)  
> **파일**: `src/gui/workers/duplicate_detection_worker.py`  
> **작성일**: 2025-01-11  
> **상태**: 분석 완료, 리팩토링 대기

---

## 1. 파일 개요 및 현황

### 1.1 기본 정보
- **LOC**: 574 lines
- **클래스 수**: 2개 (`DuplicateJobStage`, `DuplicateDetectionWorker`)
- **최대 메서드 길이**: `run()` 메서드 약 455 lines (전체의 79%)
- **의존성**: 20개 import (Qt, Domain Services, DTOs)

### 1.2 현재 구조
```python
class DuplicateDetectionWorker(QThread):
    - run()                    # 455 lines - God Function
    - _emit_progress()         # 15 lines
    - _check_cancelled()       # 7 lines
```

### 1.3 주요 책임 (현재 혼재됨)
1. **스레드 관리**: QThread 상속, 취소 처리
2. **진행률 추적**: Signal emit, 단계별 진행률 관리
3. **도메인 로직**: 파일명 파싱, Blocking, 관계 탐지, 그룹 생성
4. **데이터 매핑**: FileEntry ↔ FileDataStore file_id 변환
5. **에러 처리**: 로깅, 에러 시그널 발생

---

## 2. 문제점 분석

### 2.1 God Function: `run()` 메서드
**현재 문제**:
- 단일 메서드에 **5단계 파이프라인 전체**가 구현됨
  - 파일명 파싱 (lines 130-197)
  - FileDataStore 매핑 (lines 198-290)
  - Blocking (lines 291-323)
  - 관계 탐지 (containment/version) (lines 324-472)
  - 그룹 생성 및 정규화 (lines 494-534)
- 각 단계가 **100+ lines**로 구성되어 독립적인 클래스/함수로 분리 가능
- 단계 추가/수정 시 `run()` 전체를 수정해야 함 (리스크↑)

**영향**:
- 테스트 불가능: 각 단계를 독립적으로 테스트할 수 없음
- 재사용 불가: 파이프라인 단계를 다른 곳에서 사용 불가
- 가독성 저하: 455 lines 메서드는 이해하기 어려움

### 2.2 단일 책임 원칙 위반 (SRP Violation)
**현재 구조**:
```
DuplicateDetectionWorker
  ├─ Thread 관리 (QThread)
  ├─ 진행률 관리 (Signal emit)
  ├─ 도메인 로직 (파싱, Blocking, 탐지)
  └─ 데이터 매핑 (FileEntry ↔ FileDataStore)
```

**문제**:
- "스레드 실행"과 "비즈니스 로직"이 한 클래스에 혼재
- 테스트 시 QThread 의존성으로 인해 단위 테스트 어려움
- 도메인 로직이 GUI 레이어에 결합됨

### 2.3 의존성 결합도
**높은 결합도 지표**:
- `FileDataStore` 직접 의존 (GUI 모델을 도메인 로직에서 사용)
- `IIndexRepository`와 `FileDataStore` 간 매핑 로직이 Worker 내부에 구현
- 도메인 서비스 (`FilenameParser`, `BlockingService`, `ContainmentDetector`)가 Worker 내부에서 생성

---

## 3. 리팩토링 목표

### 3.1 핵심 목표
1. **파이프라인 분리**: 도메인 로직을 순수 Python 클래스로 추출
2. **단일 책임**: Worker는 "스레드 실행 + 진행률 emit"만 담당
3. **테스트 가능성**: 각 단계를 독립적으로 단위 테스트 가능
4. **재사용성**: 파이프라인을 다른 컨텍스트에서도 사용 가능

### 3.2 원칙
- **Clean Architecture**: 도메인 로직은 GUI 의존성 제거
- **Dependency Inversion**: Worker는 인터페이스(UseCase)에 의존
- **단일 책임**: 각 클래스는 하나의 책임만 가짐

---

## 4. 구체적인 리팩토링 계획

### 4.1 새로운 파일 구조

```
src/
├── application/
│   └── use_cases/
│       └── duplicate_detection/
│           ├── __init__.py
│           ├── duplicate_detection_pipeline.py       # 새 파일
│           ├── duplicate_detection_use_case.py       # 새 파일 (선택적)
│           └── stages/
│               ├── __init__.py
│               ├── filename_parsing_stage.py         # 새 파일
│               ├── file_mapping_stage.py             # 새 파일
│               ├── blocking_stage.py                 # 새 파일
│               ├── relation_detection_stage.py       # 새 파일
│               └── group_creation_stage.py           # 새 파일
│
└── gui/
    └── workers/
        └── duplicate_detection_worker.py             # 리팩토링 (150 lines 이하로 축소)
```

### 4.2 클래스 설계

#### 4.2.1 `DuplicateDetectionPipeline` (순수 Python, Qt 모름)

```python
# application/use_cases/duplicate_detection/duplicate_detection_pipeline.py

class DuplicateDetectionPipeline:
    """중복 탐지 파이프라인.
    
    순수 Python 클래스로 도메인 로직만 담당.
    Qt/QThread 의존성 없음.
    """
    
    def __init__(
        self,
        filename_parser: FilenameParser,
        blocking_service: BlockingService,
        containment_detector: ContainmentDetector,
        index_repository: IIndexRepository,
        file_data_store: Optional[FileDataStore] = None,
        log_sink: Optional[ILogSink] = None
    ):
        self._filename_parser = filename_parser
        self._blocking_service = blocking_service
        self._containment_detector = containment_detector
        self._index_repository = index_repository
        self._file_data_store = file_data_store
        self._log_sink = log_sink
        
        # 단계 초기화
        self._stages = [
            FilenameParsingStage(filename_parser, index_repository, log_sink),
            FileMappingStage(file_data_store, log_sink),
            BlockingStage(blocking_service, log_sink),
            RelationDetectionStage(containment_detector, log_sink),
            GroupCreationStage(log_sink)
        ]
    
    def execute(
        self,
        request: DuplicateDetectionRequest,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> list[DuplicateGroupResult]:
        """파이프라인 실행.
        
        Args:
            request: 중복 탐지 요청.
            progress_callback: 진행률 콜백 (processed, total, message).
        
        Returns:
            중복 그룹 결과 리스트.
        """
        context = PipelineContext(request)
        
        for stage_idx, stage in enumerate(self._stages):
            if progress_callback:
                progress_callback(
                    stage_idx,
                    len(self._stages),
                    f"{stage.name} 시작..."
                )
            
            context = stage.execute(context)
            
            if context.error:
                raise PipelineError(context.error)
        
        return context.results
```

#### 4.2.2 단계별 클래스 (`PipelineStage` 인터페이스)

```python
# application/use_cases/duplicate_detection/stages/base_stage.py

class PipelineContext:
    """파이프라인 컨텍스트."""
    request: DuplicateDetectionRequest
    files: list[FileEntry]
    parse_results: dict[int, FilenameParseResult]
    file_mapping: dict[int, int]  # IndexRepository file_id -> FileDataStore file_id
    blocking_groups: list[BlockingGroup]
    results: list[DuplicateGroupResult]
    error: Optional[str] = None


class PipelineStage(ABC):
    """파이프라인 단계 인터페이스."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """단계 이름."""
        pass
    
    @abstractmethod
    def execute(self, context: PipelineContext) -> PipelineContext:
        """단계 실행.
        
        Args:
            context: 파이프라인 컨텍스트.
        
        Returns:
            업데이트된 컨텍스트.
        """
        pass


# application/use_cases/duplicate_detection/stages/filename_parsing_stage.py

class FilenameParsingStage(PipelineStage):
    """파일명 파싱 단계."""
    
    @property
    def name(self) -> str:
        return "파일명 파싱"
    
    def execute(self, context: PipelineContext) -> PipelineContext:
        # 기존 run()의 lines 130-197 로직
        # ...
        return context


# application/use_cases/duplicate_detection/stages/file_mapping_stage.py

class FileMappingStage(PipelineStage):
    """FileDataStore 매핑 단계."""
    
    @property
    def name(self) -> str:
        return "FileDataStore 매핑"
    
    def execute(self, context: PipelineContext) -> PipelineContext:
        # 기존 run()의 lines 198-290 로직
        # ...
        return context


# application/use_cases/duplicate_detection/stages/blocking_stage.py

class BlockingStage(PipelineStage):
    """Blocking 단계."""
    
    @property
    def name(self) -> str:
        return "Blocking"
    
    def execute(self, context: PipelineContext) -> PipelineContext:
        # 기존 run()의 lines 291-323 로직
        # ...
        return context


# application/use_cases/duplicate_detection/stages/relation_detection_stage.py

class RelationDetectionStage(PipelineStage):
    """관계 탐지 단계 (containment/version)."""
    
    @property
    def name(self) -> str:
        return "관계 탐지"
    
    def execute(self, context: PipelineContext) -> PipelineContext:
        # 기존 run()의 lines 324-472 로직
        # ...
        return context


# application/use_cases/duplicate_detection/stages/group_creation_stage.py

class GroupCreationStage(PipelineStage):
    """그룹 생성 및 정규화 단계."""
    
    @property
    def name(self) -> str:
        return "그룹 생성"
    
    def execute(self, context: PipelineContext) -> PipelineContext:
        # 기존 run()의 lines 494-534 로직
        # ...
        return context
```

#### 4.2.3 리팩토링된 `DuplicateDetectionWorker`

```python
# gui/workers/duplicate_detection_worker.py (리팩토링 후)

class DuplicateDetectionWorker(QThread):
    """중복 탐지 워커 스레드.
    
    QThread 상속하여 별도 스레드에서 중복 탐지 작업을 수행.
    단계별 진행률 추적 및 취소 지원.
    """
    
    duplicate_completed = Signal(list)
    duplicate_error = Signal(str)
    duplicate_progress = Signal(JobProgress)
    
    def __init__(
        self,
        request: DuplicateDetectionRequest,
        pipeline: DuplicateDetectionPipeline,  # UseCase 주입
        parent: Optional[QObject] = None
    ) -> None:
        super().__init__(parent)
        self._request = request
        self._pipeline = pipeline
        self._cancelled = False
    
    def cancel(self) -> None:
        """중복 탐지 취소."""
        self._cancelled = True
    
    def run(self) -> None:
        """워커 실행."""
        try:
            # 파이프라인 실행 (진행률 콜백 제공)
            results = self._pipeline.execute(
                self._request,
                progress_callback=self._on_progress
            )
            
            if not self._cancelled:
                self.duplicate_completed.emit(results)
        
        except Exception as e:
            if not self._cancelled:
                self.duplicate_error.emit(str(e))
    
    def _on_progress(self, processed: int, total: int, message: str) -> None:
        """진행률 콜백."""
        if not self._cancelled:
            progress = JobProgress(
                processed=processed,
                total=total,
                message=message
            )
            self.duplicate_progress.emit(progress)
```

---

## 5. 단계별 작업 계획

### Phase 1: Pipeline 구조 설계 및 기본 클래스 생성
- [ ] `PipelineContext` 클래스 생성
- [ ] `PipelineStage` 추상 클래스 생성
- [ ] `DuplicateDetectionPipeline` 기본 구조 생성
- [ ] 단위 테스트 작성 (빈 파이프라인 실행)

### Phase 2: 각 단계별 클래스 생성 (순차적)
- [ ] `FilenameParsingStage` 생성 및 기존 로직 이동
- [ ] `FileMappingStage` 생성 및 기존 로직 이동
- [ ] `BlockingStage` 생성 및 기존 로직 이동
- [ ] `RelationDetectionStage` 생성 및 기존 로직 이동
- [ ] `GroupCreationStage` 생성 및 기존 로직 이동

### Phase 3: Worker 리팩토링
- [ ] `DuplicateDetectionWorker`를 Pipeline 사용하도록 변경
- [ ] 기존 `run()` 메서드를 간소화
- [ ] 진행률 콜백 연결

### Phase 4: 통합 테스트 및 검증
- [ ] 기존 통합 테스트 실행하여 동작 확인
- [ ] 성능 테스트 (기존 대비 성능 유지 확인)
- [ ] 코드 리뷰 및 정리

### Phase 5: 정리 및 문서화
- [ ] 사용하지 않는 코드 제거
- [ ] 문서 업데이트
- [ ] 커밋 및 PR 생성

---

## 6. 예상 효과

### 6.1 코드 품질
- **가독성**: `run()` 메서드 455 lines → 50 lines 이하로 축소
- **유지보수성**: 각 단계를 독립적으로 수정 가능
- **테스트 가능성**: 각 단계를 독립적으로 단위 테스트 가능

### 6.2 아키텍처 개선
- **의존성 방향**: GUI 레이어 → Application 레이어 (Clean Architecture 준수)
- **재사용성**: Pipeline을 CLI 또는 다른 GUI에서도 사용 가능
- **확장성**: 새로운 단계 추가 시 Pipeline만 수정

### 6.3 성능
- **성능 영향**: 거의 없음 (로직은 동일, 구조만 변경)
- **메모리**: 약간의 오버헤드 (PipelineContext 객체)

---

## 7. 리스크 및 주의사항

### 7.1 주요 리스크
1. **기존 통합 테스트 실패 가능성**: Worker 동작 변경 시 테스트 수정 필요
2. **진행률 콜백 타이밍**: 단계별 진행률이 기존과 다를 수 있음
3. **에러 처리**: Pipeline 내부 에러 전파 방식 확인 필요

### 7.2 완화 방안
- 단계별로 순차적으로 리팩토링하여 각 단계마다 테스트
- 기존 통합 테스트를 유지하며 점진적 전환
- 에러 처리 로직을 명확히 문서화

---

## 8. 체크리스트

### 8.1 코드 작성
- [ ] `PipelineContext` 클래스 작성
- [ ] `PipelineStage` 추상 클래스 작성
- [ ] 각 단계별 클래스 작성 (5개)
- [ ] `DuplicateDetectionPipeline` 작성
- [ ] `DuplicateDetectionWorker` 리팩토링

### 8.2 테스트
- [ ] 각 단계별 단위 테스트 작성
- [ ] Pipeline 통합 테스트 작성
- [ ] Worker 통합 테스트 작성
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
- `application/use_cases/scan_folder.py`: 유사한 UseCase 패턴 참고
- `gui/workers/scan_worker.py`: Worker 패턴 참고

### 9.2 설계 패턴
- **Pipeline Pattern**: 단계별 처리 파이프라인
- **Strategy Pattern**: 각 단계를 전략으로 분리
- **Template Method Pattern**: Pipeline이 단계 실행 순서 정의

---

**작성자**: NovelGuard 개발팀  
**검토 상태**: 대기 중  
**다음 단계**: Phase 1 시작
