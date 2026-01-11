## 🔧 Phase 3: 인프라 정리 (P1-P2 - 안정화)

> **목표**: Infrastructure 계층 정리 및 에러 처리/설정 관리 체계화

### Phase 3.1: Logging 계층화

#### 목표
- 전역 logger 제거
- 인터페이스 기반 로깅으로 전환
- Domain 계층이 Infrastructure에 의존하지 않도록

#### Before
```python
# common/logging.py (현재)
def setup_logging(...) -> logging.Logger:
    logger = logging.getLogger("NovelGuard")
    # 전역 설정
    return logger
```

#### After
```python
# domain/ports/logger.py (Ports는 Domain에 정의!)
from typing import Protocol

class ILogger(Protocol):
    """로깅 인터페이스 (Domain Port)."""
    def info(self, message: str) -> None: ...
    def warning(self, message: str) -> None: ...
    def error(self, message: str) -> None: ...
    def debug(self, message: str) -> None: ...

# infra/logging/std_logger.py (Infra에서 구현)
from domain.ports.logger import ILogger

class StdLogger:
    """표준 라이브러리 기반 Logger 구현 (ILogger Protocol 구현)."""
    def info(self, message: str) -> None: ...
    def warning(self, message: str) -> None: ...
    def error(self, message: str) -> None: ...
    def debug(self, message: str) -> None: ...

# domain/services/... (ILogger 주입받아 사용)
from domain.ports.logger import ILogger  # Domain은 Port만 import!

class FileComparisonService:
    def __init__(self, logger: ILogger):
        self.logger = logger
```

#### 작업 체크리스트

##### Step 3.1.1: Logging 인터페이스 정의 (domain/ports에!)
- [ ] `src/domain/ports/logger.py` 생성 (**infra/logging이 아닌 domain/ports에!**)
  - [ ] `ILogger` Protocol 정의 (Python `typing.Protocol`)
  - [ ] `info(message: str) -> None`
  - [ ] `warning(message: str) -> None`
  - [ ] `error(message: str) -> None`
  - [ ] `debug(message: str) -> None`
  - [ ] 컨텍스트 정보 지원 (선택적, 예: `info(message: str, context: dict[str, Any] | None = None)`)
- [ ] 타입 힌팅 명확히
- [ ] `domain/ports/__init__.py`에 export 추가

##### Step 3.1.2: 표준 Logger 구현 (infra에서 Protocol 구현)
- [ ] `src/infra/logging/` 디렉토리 생성
- [ ] `src/infra/logging/__init__.py` 생성 (export)
- [ ] `src/infra/logging/std_logger.py` 생성
  - [ ] `from domain.ports.logger import ILogger` import
  - [ ] `StdLogger` 클래스 정의 (`ILogger` Protocol 구현)
  - [ ] 기존 `setup_logging()` 로직 이동
  - [ ] 파일 핸들러, 콘솔 핸들러 설정
- [ ] Factory 함수 생성
  - [ ] `create_std_logger(...) -> ILogger` 함수 (`domain.ports.logger.ILogger` 반환)
- [ ] 단위 테스트 작성 (`tests/infra/logging/test_std_logger.py`)
  - [ ] `ILogger` Protocol 준수 확인 (`isinstance(logger, ILogger)`)
- [ ] 기존 로깅 동작과 동일한지 확인

##### Step 3.1.3: Domain/UseCase에서 인터페이스 사용 (로깅 선택적 원칙 적용!)
- [ ] **Domain Service 로깅 필요성 평가** (v1.3 규칙)
  - [ ] 각 Domain Service 분석:
    - "의사결정/판정/규칙" Service(예: `VersionSelectionService`, `DuplicateDetectionService`) → **로깅 금지**
    - "I/O가 필요한 Service"(예: 파일 읽기 중 오류) → **로깅 허용**
    - 상태/판정에 필수적인 경우에만 로깅 주입
- [ ] Domain Service에서 `ILogger` **선택적으로** 주입받도록 변경
  - [ ] 로깅이 필요한 Service만 생성자에서 `ILogger` 받기 (Optional[ILogger] 허용)
  - [ ] 로깅이 불필요한 Service는 logger 파라미터 없음
  - [ ] 전역 `logger` 사용 제거
  - [ ] 예시:
    ```python
    # ✅ 로깅 금지: 의사결정 Service
    class VersionSelectionService:
        def __init__(self):  # logger 없음
            ...
        def select_best_version(self, files: list[File]) -> File:
            # 판정 로직만 (로깅 불필요)
            ...
    
    # ✅ 로깅 허용: I/O Service
    class FileComparisonService:
        def __init__(self, logger: ILogger):  # logger 필요
            self.logger = logger
        def are_identical(self, file1: File, file2: File) -> bool:
            try:
                # 파일 읽기 중 오류 발생 가능 → 로깅 필요
                ...
            except Exception as e:
                self.logger.error(f"파일 비교 실패: {e}")
                raise
    ```
- [ ] UseCase에서 `ILogger` 주입받도록 변경 (UseCase는 모두 로깅 허용)
- [ ] Bootstrap에서 Logger 생성 및 **선택적으로** 주입 (필요한 Service만)
- [ ] 단위 테스트 작성
  - [ ] 로깅이 없는 Service는 Mock Logger 불필요 (테스트 단순화)
  - [ ] 로깅이 있는 Service만 Mock Logger 사용
- [ ] 통합 테스트로 동작 확인

##### Step 3.1.4: GUI/Workers에서 인터페이스 사용
- [ ] GUI 컴포넌트에서 `ILogger` 사용하도록 변경
- [ ] Worker에서 `ILogger` 사용하도록 변경
- [ ] 전역 `logger` import 제거
- [ ] 단위 테스트 작성
- [ ] 통합 테스트로 동작 확인

##### Step 3.1.5: 레거시 정리
- [ ] `common/logging.py`에 Deprecation 경고 추가
- [ ] 사용처 점진적으로 변경
- [ ] 모든 전환 완료 후 `common/logging.py` 삭제 또는 최소화
- [ ] 문서 업데이트

#### 리스크 관리
- **리스크**: 로깅 누락 가능성
  - **완화책**: 통합 테스트로 모든 로그 레벨 확인

#### 예상 소요 시간
- Step 3.1.1: 1시간
- Step 3.1.2: 2시간
- Step 3.1.3: 3시간
- Step 3.1.4: 2시간
- Step 3.1.5: 1시간
- **총계**: 9시간

---

### Phase 3.2: Error 계층화

#### 목표
- 에러 타입을 도메인/인프라로 명확히 구분
- 의미적 계층 구조 확립
- 에러 핸들링 일관성 향상

#### Before
```python
# common/errors.py (현재)
class NovelGuardError(Exception): ...
class FileEncodingError(NovelGuardError): ...
class DuplicateAnalysisError(NovelGuardError): ...
# 기술/도메인 혼합, 계층 없음
```

#### After
```python
# common/errors.py (목표)
class NovelGuardError(Exception): ...

# Domain Errors
class DomainError(NovelGuardError): ...
class ValidationError(DomainError): ...
class DuplicateDetectionError(DomainError): ...
class IntegrityCheckError(DomainError): ...

# Infrastructure Errors
class InfraError(NovelGuardError): ...
class FileSystemError(InfraError): ...
class DatabaseError(InfraError): ...
class EncodingDetectionError(InfraError): ...
```

#### 작업 체크리스트

##### Step 3.2.1: 에러 계층 구조 설계
- [ ] 현재 `common/errors.py`의 모든 에러 클래스 목록 작성
- [ ] 각 에러의 책임 분석
  - [ ] Domain 에러인가? (비즈니스 규칙 위반)
  - [ ] Infrastructure 에러인가? (기술적 실패)
- [ ] 계층 구조 설계 문서 작성

##### Step 3.2.2: Domain Errors 정의
- [ ] `common/errors.py` 업데이트
  - [ ] `DomainError` 베이스 클래스 추가
  - [ ] `ValidationError(DomainError)` 추가
  - [ ] `DuplicateDetectionError(DomainError)` 추가
  - [ ] `IntegrityCheckError(DomainError)` 추가
  - [ ] 기존 도메인 관련 에러를 새 계층으로 이동
- [ ] 각 에러에 적절한 메시지 포맷 추가
- [ ] Docstring 작성

##### Step 3.2.3: Infrastructure Errors 정의
- [ ] `common/errors.py` 업데이트
  - [ ] `InfraError` 베이스 클래스 추가
  - [ ] `FileSystemError(InfraError)` 추가
  - [ ] `DatabaseError(InfraError)` 추가
  - [ ] `EncodingDetectionError(InfraError)` 추가
  - [ ] 기존 인프라 관련 에러를 새 계층으로 이동
- [ ] 각 에러에 적절한 메시지 포맷 추가
- [ ] Docstring 작성

##### Step 3.2.4: 에러 사용처 업데이트 및 변환 패턴 정의
- [ ] 전체 코드베이스에서 에러 사용처 검색
- [ ] Domain 계층에서 `InfraError` 사용 금지 확인
- [ ] Infrastructure 계층에서 `DomainError` 직접 발생 금지 확인
- [ ] **표준 에러 변환 패턴 정의** (Exception Mapping Table)
  - [ ] `common/errors/exception_mapping.py` 생성 (또는 `usecases/error_mapper.py`)
  - [ ] 표준 변환 테이블 작성:
    ```python
    # infra → domain 에러 변환 매핑
    EXCEPTION_MAPPING: dict[type[InfraError], type[DomainError]] = {
        FileSystemError: IntegrityCheckError,
        EncodingDetectionError: IntegrityCheckError,
        DatabaseError: ValidationError,
        # ...
    }
    
    def map_infra_error(error: InfraError) -> DomainError:
        """Infra 에러를 Domain 에러로 변환."""
        error_type = EXCEPTION_MAPPING.get(type(error), DomainError)
        return error_type(str(error)) from error
    ```
  - [ ] UseCase에서 표준 변환 함수 사용
    ```python
    # usecases/scan_files.py
    def execute(self, root_path: Path) -> list[File]:
        try:
            return self.repository.find_all()
        except InfraError as e:
            raise map_infra_error(e)  # 표준 변환 패턴
    ```
- [ ] 단위 테스트 작성 (에러 변환 테스트 포함)
- [ ] 통합 테스트로 동작 확인

##### Step 3.2.5: 에러 핸들링 가이드 문서화
- [ ] 에러 계층 구조 다이어그램 작성
- [ ] 각 계층에서 사용 가능한 에러 명시
- [ ] **표준 에러 변환 규칙 문서화** (Exception Mapping Table 포함)
  - [ ] 변환 매핑 테이블 문서화
  - [ ] UseCase에서의 사용 예시 문서화
  - [ ] 변환 패턴 원칙 명시 (일관성 유지)
- [ ] `protocols/development_protocol.md` 업데이트

#### 예상 소요 시간
- Step 3.2.1: 1시간
- Step 3.2.2: 2시간
- Step 3.2.3: 2시간
- Step 3.2.4: 3시간
- Step 3.2.5: 1시간
- **총계**: 9시간

---

### Phase 3.3: Settings 분리

#### 목표
- 런타임 설정과 불변 상수 분리
- 테스트/배포 환경 분리 지원
- 타입 안전성 향상

#### Before
```python
# app/settings.py (현재)
# 환경 설정 + 고정 상수 혼합
```

#### After
```python
# app/settings/config.py (런타임 설정)
class AppConfig(BaseModel):
    log_level: str
    db_path: Path
    max_workers: int
    ...

# app/settings/constants.py (불변 상수)
class Constants:
    MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
    DEFAULT_ENCODING = "utf-8"
    ...
```

#### 작업 체크리스트

##### Step 3.3.1: 설정 분석 및 분류
- [ ] `app/settings.py`의 모든 설정 항목 목록 작성
- [ ] 각 항목의 특성 분석
  - [ ] 런타임에 변경 가능한가? → `config.py`
  - [ ] 불변 상수인가? → `constants.py`
  - [ ] 환경별로 다른가? → 환경 변수 지원
- [ ] 분류 계획 문서 작성

##### Step 3.3.2: Constants 모듈 생성
- [ ] `src/app/settings/` 디렉토리 생성
- [ ] `src/app/settings/__init__.py` 생성
- [ ] `src/app/settings/constants.py` 생성
  - [ ] `Constants` 클래스 정의 (모든 속성 대문자)
  - [ ] 파일 크기 제한
  - [ ] 기본 인코딩
  - [ ] 해시 알고리즘
  - [ ] 기타 불변 값
- [ ] 타입 힌팅 명확히
- [ ] Docstring 작성

##### Step 3.3.3: Config 모듈 생성
- [ ] `src/app/settings/config.py` 생성
  - [ ] `AppConfig` Pydantic 모델 정의
  - [ ] 런타임 설정 필드 정의
  - [ ] 환경 변수에서 로드하는 로직
  - [ ] 기본값 설정
- [ ] `load_config()` 함수 구현
  - [ ] 환경 변수 읽기
  - [ ] 설정 파일 읽기 (선택적)
  - [ ] 검증 및 기본값 적용
- [ ] 단위 테스트 작성 (`tests/app/settings/test_config.py`)
- [ ] 통합 테스트로 동작 확인

##### Step 3.3.4: 사용처 업데이트
- [ ] 전체 코드베이스에서 `app.settings` import 검색
- [ ] Constants 사용처는 `constants.py`로 변경
- [ ] Config 사용처는 `config.py`로 변경
- [ ] Bootstrap에서 Config 로드 및 주입
- [ ] 단위 테스트 작성
- [ ] 통합 테스트로 동작 확인

##### Step 3.3.5: 환경별 설정 지원 (선택적)
- [ ] `.env` 파일 지원 (python-dotenv)
- [ ] `config.dev.toml`, `config.prod.toml` 파일 지원
- [ ] 환경 변수로 설정 오버라이드
- [ ] 문서 업데이트

#### 예상 소요 시간
- Step 3.3.1: 1시간
- Step 3.3.2: 2시간
- Step 3.3.3: 3시간
- Step 3.3.4: 2시간
- Step 3.3.5: 2시간 (선택적)
- **총계**: 10시간 (선택적 포함 시)

---

### Phase 3.4: Phase 3 통합 테스트 및 검증

#### 작업 체크리스트

- [ ] 전체 단위 테스트 실행 및 통과 확인
- [ ] 통합 테스트 실행
- [ ] 수동 테스트 수행
  - [ ] 로깅 동작 확인
  - [ ] 에러 핸들링 확인
  - [ ] 설정 로드 확인
- [ ] 성능 벤치마크 실행
- [ ] 코드 커버리지 확인
- [ ] 린터/포매터 실행
- [ ] 타입 체크 실행
- [ ] 문서 리뷰
- [ ] Git 커밋 및 태그 생성 (`refactor/phase3-complete`)

#### 예상 소요 시간
- **총계**: 3시간

---

