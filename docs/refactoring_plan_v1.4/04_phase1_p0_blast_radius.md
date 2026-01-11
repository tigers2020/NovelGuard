## 🔄 Phase 1: 폭발 반경 제거 (P0 - 즉시)

> **목표**: 가장 위험한 파일들을 안전하게 분리하여 변경 영향 범위를 최소화

### Phase 1.1: `gui/views/main_window.py` Orchestration 제거 및 Bootstrap 분리

#### 목표
- **`gui/views/main_window.py`의 orchestration 로직 제거** (실제 폭발 반경: 2398줄, 60개 메서드)
- 애플리케이션 초기화 로직을 `bootstrap.py`로 분리
- 워크플로우 로직을 별도 모듈로 추출
- GUI가 domain/infra 직접 import하는 문제 해소

#### Before
```python
# src/gui/views/main_window.py (현재)
from infra.db.file_repository import FileRepository  # ❌ 직접 import
from domain.models.preview_stats import PreviewStats  # ❌ 직접 import
from common.logging import setup_logging  # ❌ 직접 import

class MainWindow(QMainWindow):
    def __init__(self) -> None:
        # 서비스 직접 생성 (❌ orchestration 혼재)
        self.repository = FileRepository(...)
        self.usecase = ScanFilesUseCase(self.repository, ...)
        # ... 2398줄, 60개 메서드, orchestration + 로직 혼재

# src/app/main.py (현재 - 단순하지만 sys.path hack 있음)
src_path = Path(__file__).parent.parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))  # ❌ 경로 hack
```

#### After
```python
# src/app/main.py (목표 - 진짜 Entry Point, 10~30줄)
def main() -> None:
    """애플리케이션 진입점."""
    from app.bootstrap import create_application
    app = create_application()
    sys.exit(app.exec())

# src/app/bootstrap.py (새로 생성)
def create_application() -> QApplication:
    """애플리케이션 및 의존성 주입."""
    app = QApplication(sys.argv)
    app.setApplicationName("NovelGuard")
    
    # 의존성 주입 (Bootstrap에서만 wiring 허용)
    repository = FileRepository(...)
    logger = create_std_logger(...)
    scan_usecase = ScanFilesUseCase(repository, ...)
    
    window = MainWindow(scan_usecase, logger, ...)  # 의존성 주입
    window.show()
    
    return app

# src/gui/views/main_window.py (목표 - orchestration 제거)
from domain.ports.logger import ILogger  # ✅ Port만 import
# ❌ from infra.db.file_repository import FileRepository  # 제거

class MainWindow(QMainWindow):
    def __init__(self, scan_usecase: ScanFilesUseCase, logger: ILogger, ...) -> None:
        # ✅ 의존성 주입받음 (직접 생성 금지)
        self.scan_usecase = scan_usecase
        self.logger = logger
```

#### 작업 체크리스트

##### Step 1.1.1: Bootstrap 모듈 생성
- [ ] `src/app/bootstrap.py` 파일 생성
- [ ] `create_application()` 함수 구현
  - [ ] QApplication 생성 및 기본 설정
  - [ ] **의존성 생성 (Bootstrap에서만 wiring 허용)**:
    - [ ] `FileRepository` 생성
    - [ ] `ILogger` 구현체 생성 (`StdLogger`)
    - [ ] UseCase들 생성 및 주입
  - [ ] MainWindow 생성 시 **의존성 주입** (생성자 파라미터로 전달)
- [ ] `setup_application()` 함수 구현
  - [ ] 로깅 초기화
  - [ ] 설정 로드
  - [ ] 환경 변수 검증
- [ ] 단위 테스트 작성 (`tests/app/test_bootstrap.py`)
- [ ] 기존 동작과 동일 확인 (Golden Tests)

##### Step 1.1.2: 워크플로우 모듈 분리 (usecases 조합만! 로직 금지!)
- [ ] `src/app/workflows/` 디렉토리 생성
- [ ] `src/app/workflows/__init__.py` 생성
- [ ] `src/app/workflows/scan_flow.py` 생성
  - [ ] **워크플로우는 UseCase 조합만 수행** (로직 추가 금지!)
  - [ ] **로직 금지 정의**:
    - ❌ 조건문/필터링 같은 판단 로직 금지 → UseCase/Service로 내려야 함
    - ❌ 계산/변환 로직 금지 → UseCase/Service로 내려야 함
    - ❌ 에러 핸들링 로직 금지 → UseCase에서 처리
    - ✅ UseCase 호출 순서 정의만 허용
    - ✅ UseCase 결과를 다음 UseCase 입력으로 전달만 허용
  - [ ] 예시 (올바른 조합):
    ```python
    class ScanFlow:
        def __init__(self, scan_usecase: ScanFilesUseCase, 
                     duplicate_usecase: FindDuplicatesUseCase):
            self.scan_usecase = scan_usecase
            self.duplicate_usecase = duplicate_usecase
        
        def execute(self, root_path: Path) -> ScanResult:
            # UseCase들을 순차적으로 호출만 함 (조합만!)
            files = self.scan_usecase.execute(root_path)
            groups = self.duplicate_usecase.execute(files)
            return ScanResult(files, groups)
    ```
  - [ ] 예시 (잘못된 로직 포함 - 금지!):
    ```python
    class ScanFlow:
        def execute(self, root_path: Path) -> ScanResult:
            files = self.scan_usecase.execute(root_path)
            # ❌ 금지: 조건문/필터링 로직
            filtered = [f for f in files if f.size > 1000]  # UseCase로 내려야!
            # ❌ 금지: 계산 로직
            total_size = sum(f.size for f in files)  # Service로 내려야!
            groups = self.duplicate_usecase.execute(filtered)
            return ScanResult(filtered, groups)
    ```
  - [ ] MainWindow에서 분리
  - [ ] 의존성 명시적 주입 (UseCase들)
- [ ] `src/app/workflows/analyze_flow.py` 생성 (향후 확장용)
  - [ ] 동일한 원칙 적용 (UseCase 조합만, 로직 금지)
- [ ] MainWindow에서 워크플로우 모듈 사용하도록 변경
- [ ] 통합 테스트 작성 (`tests/app/test_workflows.py`)
  - [ ] UseCase Mock을 주입하여 조합 동작만 테스트
  - [ ] **구조 테스트 작성 (필수! v1.3 규칙 - AST 기반 검증)**:
    ```python
    import ast
    import inspect
    
    def test_workflow_contains_no_branching_logic():
        """워크플로우에 조건문/반복문이 없는지 AST 기반 검증."""
        src = inspect.getsource(ScanFlow.execute)
        tree = ast.parse(src)
        
        # 금지된 노드 타입 목록
        forbidden_nodes = (
            ast.If, ast.For, ast.While, ast.ListComp, ast.DictComp,
            ast.SetComp, ast.GeneratorExp, ast.Lambda
        )
        
        # AST 트리에서 금지된 노드 검색
        for node in ast.walk(tree):
            if isinstance(node, forbidden_nodes):
                node_type = type(node).__name__
                raise AssertionError(
                    f"Workflow에 금지된 {node_type} 노드 발견: "
                    f"{ast.get_source_segment(src, node) or 'N/A'}"
                )
        
        # 문자열 검사로는 부족하므로 AST 기반 검증 필수
        # 주석/문자열/포맷팅에 의한 오탐 방지
    
    def test_workflow_only_calls_usecases():
        """워크플로우가 UseCase 호출만 수행하는지 AST 기반 검증."""
        src = inspect.getsource(ScanFlow.execute)
        tree = ast.parse(src)
        
        # 허용된 노드 타입 (할당, 반환, 속성 접근, 함수 호출만)
        allowed_patterns = [
            ast.Assign,  # 변수 할당
            ast.Return,  # 반환
            ast.Expr,    # 표현식 (UseCase 호출)
        ]
        
        # 함수 정의 내부의 모든 문(statement) 검사
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "execute":
                for stmt in node.body:
                    # 허용된 패턴이 아니면 경고
                    if not isinstance(stmt, tuple(allowed_patterns) + (ast.Pass,)):
                        # 함수 호출인 경우 UseCase 호출 패턴 확인
                        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
                            # self.xxx_usecase.execute() 패턴 확인
                            if not (isinstance(stmt.value.func, ast.Attribute) and
                                   isinstance(stmt.value.func.value, ast.Attribute) and
                                   stmt.value.func.value.attr.endswith("_usecase")):
                                raise AssertionError(
                                    f"Workflow에 허용되지 않은 호출: "
                                    f"{ast.get_source_segment(src, stmt)}"
                                )
    ```
  - [ ] 조건문/필터링 로직이 없는지 검증 (자동화된 구조 테스트로)
- [ ] 기존 기능 동작 확인

##### Step 1.1.3: MainWindow 의존성 명시화 및 직접 import 제거
- [ ] MainWindow 생성자에서 의존성 받도록 변경
  - [ ] `ResultStore` 주입
  - [ ] UseCase들 주입 (`ScanFilesUseCase`, `FindDuplicatesUseCase` 등)
  - [ ] `ILogger` 주입 (Port 인터페이스)
  - [ ] **`FileRepository` 직접 생성 제거** (UseCase를 통해 간접 접근)
- [ ] **GUI에서 domain/infra 직접 import 제거**:
  - [ ] `from infra.db.file_repository import FileRepository` 제거
  - [ ] `from domain.models.*` 직접 import 제거 (필요 시 UseCase 결과만 사용)
  - [ ] `from common.logging import setup_logging` 제거 → `ILogger` Port 사용
- [ ] Factory 패턴 도입 (선택적)
  - [ ] `create_main_window()` 함수 생성 (Bootstrap에서 사용)
- [ ] 단위 테스트 작성 (의존성 Mock)
- [ ] GUI 테스트로 수동 확인
- [ ] **의존성 방향 검증**: `grep -r "from infra\|from domain" gui/views/main_window.py` 결과 없음 확인

##### Step 1.1.4: 단일 엔트리포인트 원칙 적용 및 sys.path hack 제거
- [ ] `src/app/main.py`에서 **sys.path hack 제거**
  - [ ] 올바른 import 경로 사용 (상대 import 또는 패키지 구조 개선)
  - [ ] `src/`를 패키지로 구성하여 경로 hack 불필요하게
- [ ] `src/main.py`가 `app/main.py`를 호출하도록 수정 (기존 호환성)
  - [ ] 단순히 `from app.main import main; main()` 호출
  - [ ] sys.path hack 없이 동작하도록
- [ ] 모든 다른 진입점 제거 또는 `app/main.py`로 리다이렉트
- [ ] 진입점 문서화 (`docs/entry_points.md`)
- [ ] 실행 스크립트(`run.bat`, `run.ps1`) 업데이트 확인
- [ ] 문서 업데이트 (`README.md`, `protocols/development_protocol.md`)

#### 리스크 관리
- **리스크**: GUI 파이프라인 조립 로직 분리 시 연결 오류 가능
- **완화책**: 
  - 단계별 리팩토링 (한 번에 하나씩)
  - 각 단계마다 테스트 및 수동 확인
  - Git 브랜치 활용 (`refactor/bootstrap-separation`)

#### 예상 소요 시간
- Step 1.1.1: 2시간
- Step 1.1.2: 3시간
- Step 1.1.3: 2시간
- Step 1.1.4: 1시간
- **총계**: 8시간

---

### Phase 1.15: Ports 정의 및 Infrastructure 마스킹 (중요!)

> **목표**: Domain/UseCase가 Infrastructure에 의존하지 않도록 Ports(인터페이스) 정의 및 기존 infra를 포트 뒤로 숨기기

#### 목표
- Domain Ports 정의 (인터페이스)
- 기존 Infrastructure를 Ports 구현으로 마스킹
- Domain/UseCase에서 Ports만 import하도록 전환

#### 작업 체크리스트

##### Step 1.15.1: Domain Ports 정의 (기존 구현체 API를 스캔하여 추출! + 변경 가드!)
- [ ] `src/domain/ports/` 디렉토리 생성
- [ ] `src/domain/ports/__init__.py` 생성 (export)
- [ ] **기존 Infrastructure 구현체의 public API 스캔** (포트 정의 전 필수!)
  - [ ] `infra/db/file_repository.py`의 `FileRepository` 클래스 메서드 목록 작성
  - [ ] `infra/hashing/hash_calculator.py`의 `HashCalculator` 클래스 메서드 목록 작성
  - [ ] `infra/encoding/encoding_detector.py`의 `EncodingDetector` 클래스 메서드 목록 작성
  - [ ] 실제 사용되는 메서드만 Protocol에 포함 (불필요한 메서드 제외)
- [ ] `src/domain/ports/file_repository.py` 생성
  - [ ] `IFileRepository` Protocol 정의 (Python `typing.Protocol`)
  - [ ] **`@runtime_checkable` 데코레이터 추가 (필수!)**:
    ```python
    from typing import Protocol, runtime_checkable
    
    @runtime_checkable
    class IFileRepository(Protocol):
        """파일 저장소 인터페이스."""
        def save_meta(self, file_meta: FileMeta) -> None: ...
        def find_by_id(self, file_id: int) -> Optional[File]: ...
        # ...
    ```
  - [ ] **기존 구현체의 실제 시그니처를 그대로 반영** (초기 포트 정의는 현재 infra API를 투영)
  - [ ] 예시: `save_meta(file_meta: FileMeta) -> None` (실제 메서드 시그니처 확인 후 수정)
  - [ ] 예시: `find_by_id(file_id: int) -> Optional[File]` (실제 메서드 시그니처 확인 후 수정)
  - [ ] 예시: `find_all() -> list[File]` (실제 메서드 존재 시에만 포함)
  - [ ] 타입 힌팅 명확히
- [ ] `src/domain/ports/hash_service.py` 생성
  - [ ] `IHashService` Protocol 정의
  - [ ] **`@runtime_checkable` 데코레이터 추가 (필수!)**:
    ```python
    from typing import Protocol, runtime_checkable
    
    @runtime_checkable
    class IHashService(Protocol):
        """해시 서비스 인터페이스."""
        def calculate_md5(self, file_path: Path) -> str: ...
        # ...
    ```
  - [ ] **기존 구현체의 실제 시그니처를 그대로 반영**
  - [ ] 예시: `calculate_md5(file_path: Path) -> str` (실제 메서드 시그니처 확인 후 수정)
  - [ ] 예시: `calculate_sha256(file_path: Path) -> str` (실제 메서드 존재 시에만 포함)
  - [ ] 예시: `calculate_fingerprint(file_path: Path) -> str` (실제 메서드 존재 시에만 포함)
- [ ] `src/domain/ports/encoding_detector.py` 생성
  - [ ] `IEncodingDetector` Protocol 정의
  - [ ] **`@runtime_checkable` 데코레이터 추가 (필수!)**:
    ```python
    from typing import Protocol, runtime_checkable
    
    @runtime_checkable
    class IEncodingDetector(Protocol):
        """인코딩 감지 인터페이스."""
        def detect_encoding(self, file_path: Path) -> EncodingResult: ...
        # ...
    ```
  - [ ] **기존 구현체의 실제 시그니처를 그대로 반영**
  - [ ] 예시: `detect_encoding(file_path: Path) -> EncodingResult` (실제 메서드 시그니처 확인 후 수정)
  - [ ] `EncodingResult` ValueObject 정의 (`domain/value_objects/encoding_result.py`, dataclass)
- [ ] 단위 테스트 작성 (`tests/domain/ports/test_*.py`)
  - [ ] Protocol 정의가 올바른지 확인
  - [ ] **`@runtime_checkable` 적용 후 실제 구현체가 Protocol을 구현하는지 확인**:
    ```python
    def test_file_repository_implements_protocol():
        """FileRepository가 IFileRepository Protocol을 구현하는지 확인."""
        from infra.db.file_repository import FileRepository
        from domain.ports.file_repository import IFileRepository
        
        repo = FileRepository(...)
        # @runtime_checkable이 없으면 False 반환 (주의!)
        assert isinstance(repo, IFileRepository), "FileRepository는 IFileRepository를 구현해야 함"
    ```

**중요**: 
- Ports 시그니처는 문서에 확정값으로 박지 말고, "초기 포트 정의는 현재 infra API를 그대로 투영"이라고 명시. 실제 구현 시 기존 구현체를 먼저 분석하여 필요한 메서드만 포함.
- **`@runtime_checkable` 데코레이터 필수**: Protocol을 런타임에서 `isinstance(impl, IPort)`로 검사하려면 `from typing import runtime_checkable` 및 `@runtime_checkable` 데코레이터가 반드시 필요합니다. 이 규칙이 없으면 계획서의 테스트 예시가 동작하지 않습니다.

**Ports 변경 가드 (v1.3 규칙)**:
- Port 변경 시 **반드시 Decision Log에 기록** (필수!)
- Port는 "UseCase 요구"가 아닌 **"Domain 필요" 기준**으로만 확장
- 새 기능 추가 시 "Port에 메서드 하나만 더..."는 금지 (Port 비대화 방지)
- Port 변경은 Phase 1.15 이후 **Phase별 리뷰 시점에만 허용**
- Port 변경 시 체크리스트:
  - [ ] Decision Log에 변경 이유 기록
  - [ ] Domain 계층에서 실제로 필요한가? 검증
  - [ ] 기존 Port로 대체 불가능한가? 검토
  - [ ] Port 변경이 Domain 순수성을 해치지 않는가? 확인

##### Step 1.15.2: 기존 Infrastructure를 Ports 구현으로 전환
- [ ] `infra/db/file_repository.py` 수정
  - [ ] `FileRepository` 클래스가 `IFileRepository` 구현하도록 변경
  - [ ] 기존 로직 유지 (변경 없음, 단 Protocol 구현만)
- [ ] `infra/hashing/hash_calculator.py` 수정
  - [ ] `HashCalculator` 클래스가 `IHashService` 구현하도록 변경
- [ ] `infra/encoding/encoding_detector.py` 수정
  - [ ] `EncodingDetector` 클래스가 `IEncodingDetector` 구현하도록 변경
- [ ] 각 구현체에 단위 테스트 작성 (Protocol 준수 확인)

##### Step 1.15.3: UseCase에서 Ports만 import하도록 변경
- [ ] `usecases/scan_files.py` 수정
  - [ ] `from infra.db.file_repository import FileRepository` 제거
  - [ ] `from domain.ports.file_repository import IFileRepository` 추가
  - [ ] 생성자에서 `IFileRepository` 받도록 변경
  - [ ] Bootstrap에서 구현체 주입
- [ ] 다른 UseCase들도 동일하게 변경
- [ ] Domain Service에서도 Ports만 import하도록 변경
- [ ] 단위 테스트 작성 (Mock Port 사용)
- [ ] 통합 테스트로 동작 확인

##### Step 1.15.4: 정리 및 검증
- [ ] Domain/UseCase에서 `infra/` 직접 import 검색 (`grep -r "from infra"`)
- [ ] 발견된 모든 직접 import 제거
- [ ] Bootstrap에서 모든 의존성 주입 (DI 컨테이너 도입 검토)
- [ ] 의존성 방향 검증 (의존성 그래프 생성)
- [ ] 문서 업데이트

#### 리스크 관리
- **리스크**: 기존 코드와의 호환성 깨짐
  - **완화책**: 점진적 전환, 어댑터 패턴 활용
- **리스크**: Ports 정의가 불완전할 수 있음
  - **완화책**: 기존 구현체를 먼저 분석하여 필요한 메서드 모두 포함

#### 예상 소요 시간
- Step 1.15.1: 3시간
- Step 1.15.2: 2시간
- Step 1.15.3: 4시간
- Step 1.15.4: 2시간
- **총계**: 11시간

---

### Phase 1.2: `domain/models/file_record.py` Pydantic 제거 및 구조 정리

#### 목표
- **FileRecord의 Pydantic 의존성 제거** (Domain Pydantic 금지 원칙)
- Entity, ValueObject, Service로 책임 분리
- 상태 관리와 비즈니스 로직 분리
- 테스트 가능한 순수 함수/클래스로 전환

#### Before (문제점)
```python
# domain/models/file_record.py (현재 - 약 70줄)
from pydantic import BaseModel, Field  # ❌ Domain에서 Pydantic 금지!

class FileRecord(BaseModel):
    """파일 1개를 대표하는 정규화된 레코드."""
    file_id: int = Field(...)
    path: Path = Field(...)
    # ... 15개 필드
    # 비즈니스 로직은 거의 없으나, Pydantic 의존성 존재
    # Phase 2에서 다른 Domain 모델들(duplicate_group, candidate_edge 등)과 함께 대량 마이그레이션 필요

**참고**: 실제 코드 분석 결과 `file_record.py`는 약 70줄로 작고 메서드도 거의 없어 "God Model"이라기보다는 **Pydantic 의존성 제거**가 주요 목표입니다.
```

#### After (목표 구조)
```python
# domain/entities/file.py
class File(Entity):
    """파일 엔티티 (식별자 + 상태)."""
    file_id: FileId
    path: FilePath  # ValueObject
    metadata: FileMetadata  # ValueObject
    hash_info: FileHashInfo  # ValueObject

# domain/value_objects/file_hash.py
class FileHashInfo(ValueObject):
    """해시 정보 값 객체 (불변)."""
    strong_hash: Optional[str]
    fast_fingerprint: Optional[str]
    normalized_fingerprint: Optional[str]
    simhash64: Optional[int]

# domain/services/file_compare.py
class FileComparisonService:
    """파일 비교 도메인 서비스."""
    def are_identical(self, file1: File, file2: File) -> bool
    def are_similar(self, file1: File, file2: File, threshold: float) -> bool
```

#### 작업 체크리스트

##### Step 1.2.1: Value Objects 분리 (Pydantic 금지!)
- [ ] `src/domain/value_objects/` 디렉토리 생성
- [ ] `src/domain/value_objects/__init__.py` 생성 (export)
- [ ] `src/domain/value_objects/file_hash.py` 생성
  - [ ] `FileHashInfo` 클래스 정의 (**dataclass 사용, Pydantic 금지!**)
  - [ ] `@dataclass(frozen=True)` 데코레이터 사용 (불변)
  - [ ] `hash_strong`, `fingerprint_fast`, `fingerprint_norm`, `simhash64` 포함
  - [ ] 검증 로직은 생성자 또는 클래스 메서드로 구현 (순수 함수)
- [ ] `src/domain/value_objects/file_path.py` 생성
  - [ ] `FilePath` 클래스 정의 (**dataclass 사용**)
  - [ ] `@dataclass(frozen=True)` 데코레이터 사용
  - [ ] `path`, `name`, `ext`, `size`, `mtime` 포함
  - [ ] 경로 검증 로직은 클래스 메서드로 구현
- [ ] `src/domain/value_objects/file_metadata.py` 생성
  - [ ] `FileMetadata` 클래스 정의 (**dataclass 사용**)
  - [ ] `@dataclass(frozen=True)` 데코레이터 사용
  - [ ] `encoding_detected`, `encoding_confidence`, `newline`, `is_text` 포함
  - [ ] 메타데이터 검증 로직은 클래스 메서드로 구현
- [ ] 기존 `FileRecord`에서 ValueObject로 마이그레이션하는 헬퍼 함수 작성
  - [ ] 헬퍼 함수는 `usecases/` 또는 `infra/`에 배치 (Domain이 아닌 곳)
- [ ] 단위 테스트 작성 (`tests/domain/value_objects/test_file_hash.py` 등)
- [ ] Pydantic import가 없는지 확인 (`grep -r "from pydantic" domain/`)
- [ ] 기존 코드와 호환성 확인

##### Step 1.2.2: Entity 분리
- [ ] `src/domain/entities/` 디렉토리 생성
- [ ] `src/domain/entities/__init__.py` 생성
- [ ] `src/domain/entities/base.py` 생성
  - [ ] `Entity` 베이스 클래스 정의 (식별자 기반)
  - [ ] `__eq__`, `__hash__` 구현
- [ ] `src/domain/value_objects/file_id.py` 생성 (FileId 타입 정의, domain/value_objects에!)
  - [ ] `FileId` 타입 정의 (`NewType` 또는 `TypeAlias` 사용)
    ```python
    from typing import NewType
    FileId = NewType("FileId", int)  # 또는 int를 직접 사용 (간단한 경우)
    ```
  - [ ] 타입 안전성을 위한 래퍼 (선택적, 복잡도 vs 안전성 트레이드오프)
- [ ] `src/domain/entities/file.py` 생성
  - [ ] `File` 엔티티 클래스 정의
  - [ ] `file_id: FileId` (domain/value_objects/file_id.py에서 import)
  - [ ] `path: FilePath` (ValueObject, 불변)
  - [ ] `metadata: FileMetadata` (ValueObject, 불변)
  - [ ] `hash_info: FileHashInfo` (ValueObject, 불변)
  - [ ] `flags: set[str]` (상태 플래그, 변경 가능)
  - [ ] `errors: list[int]` (무결성 이슈 참조, 변경 가능)
  - [ ] **Entity 변경 가능성 규칙 (v1.3 규칙)**:
    - ✅ **허용되는 변경**:
      - `flags` 추가/제거 (`add_flag()`, `remove_flag()` 메서드)
      - `errors` 리스트에 issue_id 추가/제거 (`add_error()`, `remove_error()` 메서드)
      - 메타데이터 교체 (`update_metadata(new_metadata: FileMetadata)` - 새 ValueObject로 교체)
    - ❌ **금지되는 변경**:
      - `file_id` 변경 (식별자는 불변)
      - `path` 직접 수정 (ValueObject는 불변, 교체만 가능)
      - 계산/판정 로직 (`is_xxx()`, `compute_xxx()` 등) → Service로 이동
      - 다른 Entity 참조 추가 → ID만 사용
    - 예시 코드:
      ```python
      class File(Entity):
          def add_flag(self, flag: str) -> None:
              """플래그 추가 (허용)."""
              self.flags.add(flag)
          
          def add_error(self, issue_id: int) -> None:
              """에러 참조 추가 (허용)."""
              if issue_id not in self.errors:
                  self.errors.append(issue_id)
          
          def update_metadata(self, new_metadata: FileMetadata) -> None:
              """메타데이터 교체 (허용)."""
              self.metadata = new_metadata  # 새 ValueObject로 교체
          
          # ❌ 금지: 계산 로직
          # def is_duplicate(self, other: File) -> bool:  # Service로 이동!
          #     ...
      ```
- [ ] `FileRecord` → `File` 변환 어댑터 작성 (호환성 유지)
- [ ] 단위 테스트 작성 (`tests/domain/entities/test_file.py`)
  - [ ] 허용된 변경 메서드 테스트
  - [ ] 금지된 변경이 없는지 검증 (코드 리뷰 또는 정적 분석)
- [ ] 기존 UseCase와 호환성 확인

##### Step 1.2.3: Domain Services 분리
- [ ] `src/domain/services/file_compare.py` 생성
  - [ ] `FileComparisonService` 클래스 정의
  - [ ] `are_identical(file1: File, file2: File) -> bool` 메서드
  - [ ] `are_similar(file1: File, file2: File, threshold: float) -> bool` 메서드
  - [ ] `compare_hashes(hash1: FileHashInfo, hash2: FileHashInfo) -> ComparisonResult` 메서드
- [ ] `src/domain/services/duplicate_detector.py` 생성
  - [ ] `DuplicateDetectionService` 클래스 정의
  - [ ] 중복 탐지 로직 이동 (기존 FileRecord에서)
  - [ ] 단계적 탐지 로직 (raw hash → normalized → similarity)
- [ ] `src/domain/services/__init__.py` 업데이트 (export)
- [ ] 기존 `FileRecord`의 `is_xxx()`, `has_xxx()` 메서드를 Service로 변환
- [ ] 단위 테스트 작성 (`tests/domain/services/test_file_compare.py`)
- [ ] 통합 테스트로 기존 동작 확인

##### Step 1.2.4: 마이그레이션 어댑터 및 점진적 전환
- [ ] `src/domain/models/file_record.py`에 어댑터 클래스 추가
  - [ ] `FileRecordAdapter` 클래스 정의 (새로운 `File` 엔티티 래핑)
  - [ ] 기존 코드와의 호환성 유지
- [ ] UseCase에서 점진적으로 새 구조 사용
  - [ ] `scan_files.py`부터 시작
  - [ ] 하나씩 마이그레이션하며 테스트
- [ ] 레거시 `FileRecord`를 사용하는 코드 식별 및 문서화
- [ ] Deprecation 경고 추가 (향후 제거 예정 표시)
  ```python
  import warnings
  
  class FileRecordAdapter:
      def __init__(self, ...):
          warnings.warn(
              "FileRecordAdapter is deprecated. Use File entity instead.",
              DeprecationWarning,
              stacklevel=2
          )
  ```
- [ ] 전체 테스트 통과 확인
- [ ] 성능 영향 측정 (변화 없어야 함)

##### Step 1.2.5: Adapter 제거 기준 및 시점 명시 (v1.3 규칙)
- [ ] **Adapter 제거 조건 정의**:
  - [ ] 모든 UseCase가 새 `File` 엔티티 사용 (100% 마이그레이션 완료)
  - [ ] `FileRecordAdapter`를 사용하는 코드가 0개 (`grep -r "FileRecordAdapter"` 결과 없음)
  - [ ] 모든 테스트가 새 구조 사용 (Adapter 경로 제거)
  - [ ] Golden Tests 통과 (새 구조 기준)
- [ ] **제거 시점**: Phase 2.3 (Phase 2 통합 테스트) 완료 시점
  - [ ] Phase 2.3 완료 후 `domain/models/file_record.py` 삭제 검토
  - [ ] Deprecation 경고 제거
  - [ ] 관련 문서 업데이트
- [ ] Adapter 제거 후 전체 테스트 재실행 및 검증

##### Step 1.2.6: 정리 및 문서화
- [ ] 마이그레이션 가이드 문서 작성 (`docs/refactoring/file_record_migration.md`)
- [ ] 아키텍처 다이어그램 업데이트
- [ ] API 문서 업데이트 (Docstring)
- [ ] `protocols/development_protocol.md` 업데이트 (새로운 구조 반영)

#### 리스크 관리
- **리스크 1**: 기존 코드와의 호환성 깨짐
  - **완화책**: 어댑터 패턴 사용, 점진적 마이그레이션
- **리스크 2**: 성능 저하 (추가 객체 생성)
  - **완화책**: 프로파일링으로 측정, 필요한 경우 최적화
- **리스크 3**: 테스트 코드 대량 변경
  - **완화책**: 테스트 헬퍼 함수 리팩토링, 점진적 변경

#### 예상 소요 시간
- Step 1.2.1: 4시간
- Step 1.2.2: 3시간
- Step 1.2.3: 4시간
- Step 1.2.4: 5시간
- Step 1.2.5: 1시간 (Adapter 제거 기준 정의)
- Step 1.2.6: 1시간 (정리 및 문서화)
- **총계**: 18시간

---

### Phase 1.3: Phase 1 통합 테스트 및 검증

#### 목표
- Phase 1의 모든 변경사항이 정상 동작하는지 확인
- 성능 회귀 없음 확인
- 문서 일관성 확인

#### 작업 체크리스트

- [ ] 전체 단위 테스트 실행 및 통과 확인
- [ ] 통합 테스트 실행 (GUI 포함)
- [ ] 수동 테스트 수행
  - [ ] 애플리케이션 정상 시작 확인
  - [ ] 파일 스캔 기능 확인
  - [ ] 중복 탐지 기능 확인
  - [ ] GUI 반응성 확인
- [ ] 성능 벤치마크 실행 (구체적 측정)
  - [ ] 스캔 처리량: `files/sec` (1000개 파일 기준)
  - [ ] 중복 탐지 처리량: `groups/sec` (100개 그룹 기준)
  - [ ] 메모리 사용량: peak RSS (MB)
  - [ ] CPU 시간: process time (초)
  - [ ] 기준선(`benchmark_baseline.json`) 대비 ±5% 이내 확인
- [ ] 코드 커버리지 확인 (목표: 80% 이상 유지)
- [ ] 린터/포매터 실행 (`ruff check`, `ruff format`)
- [ ] 타입 체크 실행 (`mypy src/`)
- [ ] 문서 리뷰
  - [ ] README.md 업데이트 확인
  - [ ] 프로토콜 문서 업데이트 확인
  - [ ] 주석/Docstring 업데이트 확인
- [ ] Git 커밋 및 태그 생성
  - [ ] 의미 있는 커밋 메시지 작성
  - [ ] `refactor/phase1-complete` 태그 생성

#### 예상 소요 시간
- **총계**: 3시간

---

