# 아키텍처 위반 수정 가이드

## 📋 개요

**목표**: Phase 4.2에서 발견된 3건의 아키텍처 위반을 0건으로 수정  
**우선순위**: 낮음 (기능 동작에는 영향 없음, 선택적)  
**예상 소요 시간**: 3-4시간

---

## 🔍 발견된 위반 사항

### 위반 1: UseCase → Infra 직접 import

**위치**: `src/usecases/scan_files.py:22`

```python
from infra.fs.file_scanner import FileScanner
```

**문제점**:
- UseCase가 Infrastructure 구현체를 직접 import
- Clean Architecture 원칙 위반
- 테스트 시 Infrastructure Mock 어려움

**현재 사용 방식**:
```python
# usecases/scan_files.py
class ScanFilesUseCase:
    def __init__(self, ...):
        self.scanner = FileScanner()  # 직접 생성
```

---

### 위반 2: GUI → Infra 직접 import

**위치 1**: `src/gui/workers/enrich_worker.py:12`

```python
from infra.db.file_repository import FileRepository
```

**위치 2**: `src/gui/views/main_window.py:32`

```python
if TYPE_CHECKING:
    from infra.db.file_repository import FileRepository
```

**문제점**:
- GUI가 Infrastructure 구현체를 직접 import
- Clean Architecture 원칙 위반
- Bootstrap을 통한 의존성 주입 패턴 위반

---

## 🔧 수정 방법

### 수정 1: FileScanner Port 정의

#### Step 1.1: `IFileScanner` Protocol 정의

**파일**: `src/domain/ports/file_scanner.py` (신규 생성)

```python
"""IFileScanner Protocol.

파일 시스템 스캔을 위한 인터페이스.
"""

from typing import Protocol, Iterator, Tuple
from pathlib import Path
from os import stat_result


class IFileScanner(Protocol):
    """파일 시스템 스캔 인터페이스.
    
    디렉토리를 재귀적으로 스캔하여 파일 경로와 stat 정보를 반환.
    """
    
    def scan_directory(
        self,
        root_path: Path
    ) -> Iterator[Tuple[str, stat_result]]:
        """디렉토리를 스캔하여 (경로, stat) 튜플을 yield.
        
        Args:
            root_path: 스캔 대상 루트 경로
        
        Yields:
            (경로 문자열, stat_result) 튜플
        """
        ...
```

#### Step 1.2: `FileScanner`가 Protocol 구현 확인

**파일**: `src/infra/fs/file_scanner.py`

**작업**:
- [ ] `IFileScanner` Protocol을 구현하는지 확인
- [ ] 메서드 시그니처 일치 확인
- [ ] 타입 힌트 추가 (선택적)

**확인**:
```python
# infra/fs/file_scanner.py가 이미 Protocol을 만족하는지 확인
# 만족하면 추가 작업 없음
```

#### Step 1.3: `ScanFilesUseCase`에서 Port만 import

**파일**: `src/usecases/scan_files.py`

**변경 전**:
```python
from infra.fs.file_scanner import FileScanner

class ScanFilesUseCase:
    def __init__(self, ...):
        self.scanner = FileScanner()  # 직접 생성
```

**변경 후**:
```python
from domain.ports.file_scanner import IFileScanner

class ScanFilesUseCase:
    def __init__(
        self,
        repository: IFileRepository,
        hash_service: IHashService,
        encoding_detector: IEncodingDetector,
        logger: ILogger,
        scanner: IFileScanner  # 주입받기
    ):
        self.repository = repository
        self.hash_service = hash_service
        self.encoding_detector = encoding_detector
        self.logger = logger
        self.scanner = scanner  # 주입받기
```

#### Step 1.4: Bootstrap에서 Scanner 주입

**파일**: `src/app/bootstrap.py`

**작업**:
- [ ] `FileScanner` 인스턴스 생성
- [ ] `ScanFilesUseCase` 생성 시 주입

**예시**:
```python
from infra.fs.file_scanner import FileScanner

def create_application() -> ...:
    # ... 기존 코드 ...
    
    # FileScanner 생성 (Infra)
    scanner = FileScanner()
    
    # ScanFilesUseCase 생성 (Scanner 주입)
    scan_usecase = ScanFilesUseCase(
        repository=repository,
        hash_service=hash_service,
        encoding_detector=encoding_detector,
        logger=logger,
        scanner=scanner  # 주입
    )
    
    # ... 나머지 코드 ...
```

**예상 소요 시간**: 1-2시간

---

### 수정 2: GUI → Infra 직접 import 제거

#### Step 2.1: `EnrichWorker`에서 FileRepository 주입으로 변경

**파일**: `src/gui/workers/enrich_worker.py`

**변경 전**:
```python
from infra.db.file_repository import FileRepository

class EnrichWorker(QRunnable):
    def run(self) -> None:
        repository = FileRepository()  # 직접 생성
```

**변경 후**:
```python
from domain.ports.file_repository import IFileRepository

class EnrichWorker(QRunnable):
    def __init__(
        self,
        scan_usecase: ScanFilesUseCase,
        repository: IFileRepository,  # 주입받기
        signals: ResultSignals,
        logger: ILogger,
        parent=None
    ):
        super().__init__(parent)
        self.scan_usecase = scan_usecase
        self.repository = repository  # 주입받기
        self.signals = signals
        self.logger = logger
```

#### Step 2.2: `MainWindow`에서 EnrichWorker 생성 시 Repository 주입

**파일**: `src/gui/views/main_window.py`

**작업**:
- [ ] `MainWindow.__init__`에서 `IFileRepository` 주입받기 (선택적)
- [ ] 또는 Bootstrap에서 `EnrichWorker` 생성 시 Repository 주입

**방법 A**: MainWindow에서 주입받기
```python
class MainWindow(QMainWindow):
    def __init__(
        self,
        ...,
        file_repository: IFileRepository,  # 주입받기
        ...
    ):
        self.file_repository = file_repository
        
    def _create_enrich_worker(self) -> EnrichWorker:
        return EnrichWorker(
            scan_usecase=self.scan_usecase,
            repository=self.file_repository,  # 주입
            signals=self.result_signals,
            logger=self.logger
        )
```

**방법 B**: Bootstrap에서 직접 생성 (권장)
```python
# app/bootstrap.py
def create_application() -> ...:
    # ... 기존 코드 ...
    
    # MainWindow 생성
    main_window = MainWindow(
        ...,
        enrich_worker_factory=lambda: EnrichWorker(
            scan_usecase=scan_usecase,
            repository=repository,  # Bootstrap에서 주입
            signals=result_signals,
            logger=logger
        )
    )
```

**예상 소요 시간**: 1시간

---

#### Step 2.3: `MainWindow`의 TYPE_CHECKING import 정리

**파일**: `src/gui/views/main_window.py:32`

**현재 상태**:
```python
if TYPE_CHECKING:
    from infra.db.file_repository import FileRepository
```

**확인**:
- 실제로 `FileRepository` 타입이 사용되는지 확인
- 사용되지 않으면 삭제
- 사용된다면 `IFileRepository`로 변경

**작업**:
- [ ] `FileRepository` 타입 사용처 확인
- [ ] 사용되지 않으면 삭제
- [ ] 사용된다면 `IFileRepository`로 변경

**예상 소요 시간**: 15분

---

## ✅ 수정 검증

### 검증 기준

1. **Import 확인**:
   ```bash
   # UseCase에서 Infra 직접 import 확인
   grep -r "from infra" src/usecases/
   # 결과: 없음 (또는 file_scanner.py만, Port로 변경 후 없음)
   
   # GUI에서 Infra 직접 import 확인
   grep -r "from infra" src/gui/
   # 결과: 없음 (또는 TYPE_CHECKING만)
   ```

2. **테스트 통과 확인**:
   ```bash
   python -m pytest tests/ --tb=no -q
   # 결과: 모든 테스트 통과 (326 passed)
   ```

3. **프로그램 실행 확인**:
   - [ ] GUI 정상 실행
   - [ ] 스캔 기능 정상 동작
   - [ ] Enrich 기능 정상 동작

---

## 📊 수정 우선순위

| 위반 | 우선순위 | 복잡도 | 예상 시간 | 위험도 |
|------|---------|--------|----------|--------|
| FileScanner Port 정의 | 중간 | 낮음 | 1-2시간 | 낮음 |
| EnrichWorker Repository 주입 | 중간 | 낮음 | 1시간 | 낮음 |
| MainWindow TYPE_CHECKING 정리 | 낮음 | 낮음 | 15분 | 낮음 |

**총 예상 시간**: 3-4시간

---

## 🎯 실행 순서

1. **Step 1**: FileScanner Port 정의 및 적용
   - Protocol 정의
   - UseCase 수정
   - Bootstrap 수정
   - 테스트 검증

2. **Step 2**: EnrichWorker Repository 주입
   - EnrichWorker 수정
   - MainWindow/Bootstrap 수정
   - 테스트 검증

3. **Step 3**: MainWindow TYPE_CHECKING 정리
   - 사용처 확인
   - 불필요하면 삭제
   - 테스트 검증

---

## ⚠️ 주의사항

### 1. FileScanner Protocol 정의 시

**고려사항**:
- `scan_directory` 메서드 시그니처 확인
- 반환 타입: `Iterator[Tuple[str, stat_result]]`
- 기존 `FileScanner`와 호환성 확인

### 2. Repository 주입 시

**고려사항**:
- Bootstrap에서 Repository 인스턴스 생성
- EnrichWorker 생성 시점에 Repository 전달
- 스레드 안전성 확인 (필요시)

### 3. 테스트 업데이트

**작업**:
- [ ] Mock 객체 업데이트
- [ ] Bootstrap 테스트 업데이트
- [ ] EnrichWorker 테스트 업데이트

---

## ✅ 체크리스트

### 수정 1: FileScanner Port
- [ ] `domain/ports/file_scanner.py` 생성
- [ ] `IFileScanner` Protocol 정의
- [ ] `infra/fs/file_scanner.py` Protocol 구현 확인
- [ ] `usecases/scan_files.py` 수정 (Port만 import)
- [ ] `app/bootstrap.py` 수정 (Scanner 주입)
- [ ] 테스트 실행 및 검증

### 수정 2: EnrichWorker Repository 주입
- [ ] `gui/workers/enrich_worker.py` 수정 (Repository 주입)
- [ ] `gui/views/main_window.py` 또는 `app/bootstrap.py` 수정
- [ ] 테스트 실행 및 검증

### 수정 3: MainWindow TYPE_CHECKING 정리
- [ ] `FileRepository` 타입 사용처 확인
- [ ] 불필요하면 삭제 또는 `IFileRepository`로 변경
- [ ] 테스트 실행 및 검증

### 최종 검증
- [ ] 모든 아키텍처 위반 0건 확인
- [ ] 전체 테스트 통과 확인 (326 passed)
- [ ] 프로그램 정상 실행 확인

---

**작성일**: 2025-01-09  
**다음 단계**: 순차적으로 진행 (선택적)
