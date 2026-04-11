## 🏛️ 아키텍처 원칙 및 경계 규칙

### 계층 간 경계 규칙 (필수 준수)

다음 규칙은 **절대 위반 금지**이며, 모든 리팩토링 작업의 기준이 됩니다:

#### 1. GUI 계층 (`gui/`)
- ✅ **usecases 인터페이스만 호출** 가능
- ✅ `app/workflows` 호출 가능 (워크플로우 조합)
- ❌ `domain/`, `infra/` 직접 import 금지
- ❌ Infrastructure 객체 직접 생성/호출 금지
- **예외**: Bootstrap에서만 wiring 허용

#### 2. Use Cases 계층 (`usecases/`)
- ✅ **domain + ports(interface)만 의존**
- ✅ `app/workflows`에서 호출됨 (또는 직접 호출)
- ❌ `gui/`, `infra/` import 금지
- ❌ Infrastructure 구현체 직접 import 금지
- **의존 방향**: `workflows → usecases` (단방향)

#### 3. Domain 계층 (`domain/`)
- ✅ **외부 프레임워크 의존 금지** (Pydantic, Qt, logging 등)
- ✅ 순수 Python 클래스만 사용 (`dataclasses` 또는 일반 클래스)
- ✅ Domain Service는 순수 함수/클래스
- ❌ `usecases/`, `infra/`, `gui/` import 금지
- ❌ `common/`에서 infra 관련 모듈 import 금지
- ✅ **Domain Service 로깅 선택적 원칙**: 
  - Domain Service는 **상태/판정에 필수적인 경우에만 ILogger를 주입**
  - "의사결정/판정/규칙" Service(예: `VersionSelectionService`, `DuplicateDetectionService`)에는 로깅 금지
  - "I/O가 필요한 Service"만 로깅 허용 (예: 파일 읽기 중 오류 로깅)
  - 테스트에서 불필요한 mock 확산 방지

#### 4. Infrastructure 계층 (`infra/`)
- ✅ **ports 구현**만 담당
- ✅ Domain/UseCase의 interface(Protocol) 구현
- ❌ Domain Entity/ValueObject 직접 수정 금지
- ❌ UseCase 로직 포함 금지

#### 5. Ports (인터페이스)
- ✅ **`domain/ports/`에 정의** (통일 원칙: Domain Ports는 domain/ports/에만)
- ✅ Python `Protocol` 사용 (타입 힌팅)
- ✅ Domain/UseCase가 정의, Infra가 구현
- ❌ `usecases/ports/`는 사용하지 않음 (혼란 방지)
- ✅ **Port 변경 가드 규칙**:
  - Port 변경 시 **반드시 Decision Log에 기록** (v1.3 규칙)
  - Port는 "UseCase 요구"가 아닌 **"Domain 필요" 기준**으로만 확장
  - 새 기능 추가 시 "Port에 메서드 하나만 더..."는 금지 (Port 비대화 방지)
  - Port 변경은 Phase 1.15 이후 **Phase별 리뷰 시점에만 허용**

### 의존성 방향 다이어그램

```
GUI → UseCases → Domain ← Ports ← Infrastructure
  ↓      ↓         ↓                    ↓
Workflows (조합)  Services          Implementations
```

**규칙**: 외부 계층은 내부 계층을 import할 수 있으나, 반대는 불가능

---

## 🔐 Domain 계층 설계 원칙 (핵심)

### Pydantic 사용 금지

**중요**: `domain/` 계층에서 Pydantic 사용을 **절대 금지**합니다.

#### 이유
- Domain이 특정 라이브러리(Pydantic)에 강하게 결합됨
- Domain은 순수 비즈니스 로직만 포함해야 함
- 테스트 시 Pydantic 의존성이 필요해짐

#### 허용되는 대안
- **`dataclasses`**: Python 표준 라이브러리
- **순수 Python 클래스**: `__init__`, `__eq__`, `__hash__` 직접 구현
- **`typing.NamedTuple`**: 불변 객체의 경우

#### Pydantic 사용 허용 영역
- ✅ **입출력 DTO**: `usecases/` 또는 `infra/`에서 파싱/직렬화 시
- ✅ **설정 모델**: `app/settings/config.py`에서만
- ❌ **Domain Entity/ValueObject**: 절대 금지

#### 예시

```python
# ✅ 올바른 예: Domain ValueObject (dataclass 사용)
from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class FileHashInfo:
    """해시 정보 값 객체 (불변)."""
    strong_hash: Optional[str]
    fast_fingerprint: Optional[str]
    normalized_fingerprint: Optional[str]
    simhash64: Optional[int]

# ❌ 잘못된 예: Pydantic 사용 (금지)
from pydantic import BaseModel

class FileHashInfo(BaseModel):  # Domain에서 Pydantic 금지!
    ...

# ✅ 올바른 예: UseCase에서 Pydantic 사용 (입출력 DTO)
from pydantic import BaseModel

class ScanFilesRequest(BaseModel):  # UseCase 레벨 DTO는 허용
    root_path: str
    extensions: list[str]
```

---

## 📐 타겟 아키텍처 (After)

```
src/
├── app/                          # Application Layer
│   ├── main.py                   # 진짜 Entry Point (10~30줄)
│   ├── bootstrap.py              # DI / Wiring
│   ├── workflows/                # 워크플로우 조합
│   │   ├── __init__.py
│   │   ├── scan_flow.py          # 스캔 워크플로우
│   │   └── analyze_flow.py       # 분석 워크플로우
│   └── settings/                 # 애플리케이션 설정
│       ├── __init__.py
│       ├── config.py             # 런타임 설정
│       └── constants.py          # 불변 상수
│
├── domain/                       # Domain Layer
│   ├── entities/                 # 엔티티 (식별자를 가진 객체)
│   │   ├── __init__.py
│   │   └── file.py               # File 엔티티 (순수 상태, dataclass)
│   ├── value_objects/            # 값 객체 (불변, dataclass)
│   │   ├── __init__.py
│   │   ├── file_hash.py          # 해시 값 객체
│   │   ├── file_path.py          # 경로 값 객체
│   │   ├── file_metadata.py      # 메타데이터 값 객체
│   │   ├── candidate_edge.py     # 후보 엣지 (FileId만 참조)
│   │   └── evidence.py           # 증거 (불변)
│   ├── aggregates/               # 집계 (불변)
│   │   ├── __init__.py
│   │   └── duplicate_group.py    # 중복 그룹 (file_ids: list[int]만 포함, File 객체 참조 금지)
│   ├── services/                 # Domain Services (순수 함수/클래스)
│   │   ├── __init__.py
│   │   ├── file_compare.py       # 파일 비교 로직
│   │   ├── duplicate_detector.py # 중복 탐지 로직
│   │   ├── version_selector.py   # 버전 선택 로직 (Service)
│   │   ├── integrity_checker.py  # 무결성 검사 로직
│   │   └── evidence_builder.py   # 증거 생성 로직
│   ├── policies/                 # 도메인 정책 (순수 규칙 함수)
│   │   ├── __init__.py
│   │   └── version_selection.py  # 버전 선택 규칙 (Service에서 사용)
│   └── ports/                    # Domain Ports (인터페이스)
│       ├── __init__.py
│       ├── file_repository.py    # IFileRepository Protocol
│       ├── hash_service.py       # IHashService Protocol
│       ├── encoding_detector.py  # IEncodingDetector Protocol
│       └── logger.py             # ILogger Protocol
│
├── usecases/                     # Use Cases (단일 유스케이스, 원자적)
│   ├── __init__.py
│   ├── scan_files.py             # 파일 스캔 유스케이스
│   ├── find_duplicates.py        # 중복 탐지 유스케이스
│   └── check_integrity.py        # 무결성 검사 유스케이스
│
├── infra/                        # Infrastructure Layer (Ports 구현)
│   ├── db/                       # IFileRepository 구현
│   │   ├── __init__.py
│   │   └── file_repository.py    # FileRepository (IFileRepository 구현)
│   ├── fs/                       # 파일 시스템 구현
│   ├── encoding/                 # IEncodingDetector 구현
│   │   └── encoding_detector.py  # EncodingDetector (IEncodingDetector 구현)
│   ├── hashing/                  # IHashService 구현
│   │   └── hash_calculator.py    # HashCalculator (IHashService 구현)
│   └── logging/                  # ILogger 구현
│       ├── __init__.py
│       └── std_logger.py         # StdLogger (ILogger 구현, domain/ports/logger.py의 Protocol 구현)
│
├── common/                       # 공통 유틸리티
│   ├── __init__.py
│   ├── errors.py                 # (개선: 계층화)
│   └── types.py                  # (유지)
│
└── gui/                          # GUI Layer (기존 구조 유지, 개선)
    ├── views/
    ├── workers/
    ├── models/
    └── ...
```

---

## 🔑 핵심 설계 원칙 (요약)

### 1. ID 기반 참조 원칙 (강제)

**규칙**: Domain 객체 간 참조는 **반드시 ID만 사용**하며, 객체 참조는 금지합니다.

#### 예시

```python
# ✅ 올바른 예: ID만 저장
@dataclass(frozen=True)
class CandidateEdge:
    """후보 엣지 (불변 ValueObject)."""
    file_id_1: int  # File 객체가 아닌 ID
    file_id_2: int  # File 객체가 아닌 ID
    similarity: float

@dataclass(frozen=True)
class IntegrityIssue:
    """무결성 이슈 Entity."""
    issue_id: int
    file_id: int  # File 객체가 아닌 ID
    issue_type: str
    severity: str

# ❌ 잘못된 예: 객체 참조 (금지)
class CandidateEdge:
    file_1: File  # File 객체 직접 참조 금지!
    file_2: File  # 순환 의존성 위험

# ✅ 필요 시 Repository/Service로 Lookup
class DuplicateGroupService:
    def get_files(self, group: DuplicateGroup, repo: IFileRepository) -> list[File]:
        """Aggregate 내부에서 File 객체가 필요할 때만 lookup."""
        return [repo.find_by_id(file_id) for file_id in group.file_ids]
```

#### 이유
- 순환 의존성 방지
- 불변성 보장 (ValueObject가 Entity 참조 시 불변성 깨짐)
- 테스트 용이성 (ID만으로 Mock 가능)

### 2. UseCases vs Workflows 역할 구분

#### `usecases/` (단일 유스케이스, 원자적)
- **역할**: 하나의 비즈니스 액션을 수행하는 단일 책임 클래스
- **예시**: 
  - `ScanFilesUseCase`: 파일 스캔만 수행
  - `FindDuplicatesUseCase`: 중복 탐지만 수행
  - `CheckIntegrityUseCase`: 무결성 검사만 수행
- **의존성**: Domain + Ports(interface)만
- **호출자**: `app/workflows` 또는 GUI

#### `app/workflows/` (워크플로우 조합)
- **역할**: 여러 UseCase를 조합하여 복잡한 시나리오 수행
- **예시**:
  - `ScanFlow`: ScanFilesUseCase → FindDuplicatesUseCase → CheckIntegrityUseCase
  - `AnalyzeFlow`: 중복 분석 전체 흐름 조합
- **의존성**: `usecases/` (단방향, workflows → usecases)
- **호출자**: GUI 또는 Bootstrap

#### 규칙 (강제)
- ✅ Workflows는 UseCases를 조합만 함 (로직 추가 금지)
  - ❌ 조건문/필터링 같은 판단 로직 금지 → UseCase/Service로 내려야 함
  - ❌ 계산/변환 로직 금지 → UseCase/Service로 내려야 함
  - ❌ 에러 핸들링 로직 금지 → UseCase에서 처리
  - ✅ UseCase 호출 순서 정의만 허용
  - ✅ UseCase 결과를 다음 UseCase 입력으로 전달만 허용
- ✅ UseCases는 다른 UseCase를 호출하지 않음 (독립적)
- ✅ 단방향 의존: `workflows → usecases → domain`

### 3. Policy vs Service 역할 구분

#### `domain/policies/` (순수 규칙, 함수)
- **역할**: 비즈니스 규칙을 표현하는 순수 함수 (상태 없음)
- **예시**:
  - `version_selection.py`: 버전 선택 규칙 함수들
    ```python
    def select_by_filename(files: list[File]) -> Optional[File]: ...
    def select_by_mtime(files: list[File]) -> Optional[File]: ...
    ```
- **특징**: 입력 → 출력만 수행, 부작용 없음

#### `domain/services/` (도메인 서비스, 클래스)
- **역할**: Policy를 조합하고, I/O를 처리하는 서비스
- **예시**:
  - `VersionSelectionService`: 여러 Policy를 조합하여 최종 판정
    ```python
    class VersionSelectionService:
        def select_best_version(self, files: list[File]) -> File:
            # Policy 함수들을 순차적으로 호출
            if result := select_by_filename(files):
                return result
            if result := select_by_mtime(files):
                return result
            ...
    ```
- **특징**: Policy를 조합하고, 복잡한 로직 처리

#### 규칙
- ✅ Policy는 순수 함수 (stateless)
- ✅ Service는 Policy를 사용하며, 복잡한 조합 담당
- ✅ UseCase에서 Service 호출, Service에서 Policy 호출

---

