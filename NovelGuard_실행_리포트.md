# NovelGuard 프로젝트 실행 리포트

> **프로젝트명**: NovelGuard  
> **목적**: 텍스트 소설 파일 정리 도구  
> **기술 스택**: Python 3.10+, PySide6, Pydantic  
> 
> **문서 버전**: 1.1  
> **작성일**: 2025-01-09  
> **최종 수정일**: 2025-01-09  
> **App 버전**: 개발 중 (SemVer 미정)  
> **커밋 해시**: 95093f799bfee922274cde35bfb5da9a978d2a40  
> **빌드 타입**: debug  
> 
> **측정 환경** (현재 문서 기준):
> - OS: Windows 10.0.26200
> - Python: 3.14.0
> - 저장장치: [측정 시 명시 필요]
> - 테스트 데이터셋: [측정 시 명시 필요: 파일 수, 평균 크기, 확장자 분포]

---

## 문서 구조

이 리포트는 다음 두 가지 관점으로 구성됩니다:

- **Intended Design** (섹션 1-5, 7-10): 설계 의도, 아키텍처, 계획된 동작
- **Observed Results** (섹션 6, 11): 실제 구현 상태, 성능 측정, 알려진 이슈

각 섹션에 **Status** 표기가 있을 경우:
- **Implemented**: 구현 완료 및 검증됨
- **Planned**: 설계 단계, 아직 구현 전
- **Observed**: 실제 측정/관측 결과

---

## 1. 실행 양식 및 시작 과정

**Status**: Implemented

### 1.1 실행 방법

#### Windows 환경
```bash
# 배치 스크립트 실행 (UTF-8 인코딩 설정 포함)
run.bat

# 또는 PowerShell 스크립트
run.ps1

# 또는 직접 Python 실행
python src/main.py
```

#### 실행 스크립트 특징
- **run.bat**: CMD 환경용, UTF-8 코드 페이지 자동 설정 (`chcp 65001`)
- **run.ps1**: PowerShell 환경용, UTF-8 인코딩 강제 설정
- 한글 인코딩 문제를 사전에 해결하여 파일명/경로 처리 오류 방지

### 1.2 애플리케이션 초기화 순서

```
1. src/main.py 실행
   ↓
2. QApplication 생성 및 설정
   - Application Name: "NovelGuard"
   - Organization Name: "NovelGuard"
   ↓
3. MainWindow 인스턴스 생성
   ↓
4. UI 파이프라인 조립 (_assemble_pipeline)
   ↓
5. GUI 구성 요소 생성
   - Header (통계 표시)
   - Sidebar (네비게이션)
   - StackedWidget (탭 페이지)
   ↓
6. QSettings에서 이전 설정 복원
   - 마지막 선택 폴더
   - 확장자 필터
   - 스캔 옵션
   ↓
7. UI 표시 (window.show())
   ↓
8. 자동 Preview 스캔 시작 (QTimer.singleShot 100ms)
   - 마지막 폴더가 있으면 자동 실행
```

---

## 2. 핵심 실행 흐름 및 행동 방식

**Status**: Implemented

### 2.1 전체 애플리케이션 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│                        MainWindow                            │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │   Header    │  │   Sidebar    │  │  StackedWidget   │   │
│  │ (통계 표시)  │  │ (네비게이션)  │  │  (탭 페이지들)   │   │
│  └─────────────┘  └──────────────┘  └──────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ 이벤트/시그널
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    결과 처리 파이프라인                       │
│                                                              │
│  Signals → Batcher → Router → Store → Index → Model → View │
│                                                              │
│  1. ResultSignals (Qt Signals)                              │
│  2. UIBatcher (배치 처리, 60fps)                            │
│  3. ResultEventRouter (이벤트 라우팅)                        │
│  4. ResultStore (Single Source of Truth, 스레드 안전)       │
│  5. ResultIndexManager (인덱싱)                             │
│  6. ResultTableModel (테이블 모델)                          │
│  7. ResultSortFilterProxyModel (필터/정렬)                  │
│  8. QTableView (UI 표시)                                    │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ 비즈니스 로직 호출
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                      Worker 스레드들                         │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │PreviewWorker │  │ ScanWorker   │  │EnrichWorker  │     │
│  │ (집계만)     │  │ (메타데이터)  │  │ (인코딩/지문) │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ UseCase 호출
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    비즈니스 로직 레이어                      │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ScanFiles     │  │FindDuplicates│  │CheckIntegrity│     │
│  │UseCase       │  │UseCase       │  │UseCase       │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ 인프라 레이어 호출
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                     인프라스트럭처 레이어                    │
│                                                              │
│  FileScanner  │  HashCalculator  │  EncodingDetector       │
│  FileRepository│  FingerprintGenerator                      │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 3단계 스캔 프로세스

#### Phase 1: Preview Scan (자동 실행)
**Status**: Implemented

**목적**: 폴더 선택 직후 빠른 미리보기 정보 제공

**실행 조건**:
- 프로그램 시작 시 (마지막 폴더가 있을 때)
- 폴더 선택 후

**처리 내용**:
- `os.scandir()`만 사용 (stat 직접 호출 없음)
- 파일 수 카운트
- 확장자 분포 집계
- 최대한 빠른 처리 (수 초 이내)

**구현 위치**: `src/gui/workers/preview_worker.py`

```python
# PreviewWorker.run()
1. os.scandir()로 디렉토리 순회
2. entry.is_file(follow_symlinks=False) 호출 (내부적으로 minimal stat 가능)
3. entry.is_dir(follow_symlinks=False) 호출
4. 파일 수 카운트 (_total_files)
5. 확장자별 카운트 (_extension_counts)
6. PreviewStats 객체 생성
7. preview_completed 시그널 emit
```

**stat 호출 여부 명확화**:
- `entry.stat()` 직접 호출: ❌ 없음
- `entry.is_file(follow_symlinks=False)`: ✅ 호출 (내부적으로 minimal stat 가능하나, `follow_symlinks=False`로 최소화)
- 정확한 파일 크기/수정일 정보 없음 (추정치만 제공)
- 속도 최우선 설계

**결과 표시**:
- 예상 파일 수
- 주요 확장자 상위 5개
- 헤더 통계 업데이트

---

#### Phase 2: Main Scan (사용자 클릭)
**Status**: Implemented

**목적**: 실제 파일 메타데이터 수집

**실행 조건**:
- "스캔 시작" 버튼 클릭
- Preview 완료 후

**처리 내용**:
- `FileScanner.scan_directory()` 호출
- 각 파일에 대해 `stat()` 호출 (크기, 수정일)
- `FileMeta` 객체 생성 (경량, 인코딩/지문 제외)
- `FileRepository.save_meta()` 저장
- 배치 단위로 UI 업데이트 (2000개씩)

**구현 위치**: `src/gui/workers/scan_worker.py`, `src/usecases/scan_files.py`

```python
# ScanWorker.run()
1. FileScanner로 디렉토리 스캔 (generator)
2. 각 파일마다:
   - stat_info는 이미 FileScanner에서 제공 (entry.stat())
   - _scan_file(phase="preview") 호출
   - FileMeta 생성 (stat 정보만)
   - FileRepository.save_meta()
   - FileRow 생성 (UI용)
   - 배치 큐에 추가 (2000개씩 emit)
3. 진행률 업데이트 (50개마다)
4. log_event("INFO", "스캔 완료", None) emit
```

**최적화 포인트**:
- 2-pass 제거: generator 직접 사용
- Path 객체 생성 최소화 (문자열 연산)
- 배치 처리로 Signal emit 오버헤드 감소
- 진행률 업데이트 간격 조정 (50개마다)

---

#### Phase 3: Enrich (자동 실행)
**Status**: Implemented (트리거 취약점 있음)

**목적**: 인코딩 감지 및 빠른 지문 생성

**실행 조건**:
- Main Scan 완료 후 자동 시작
- **현재 구현**: `_on_log_event`에서 `level == "INFO" and msg == "스캔 완료"` 문자열 감지
- **⚠️ 취약점**: 로그 문자열 감지로 i18n/문구 변경/중복 로그에 취약 (자세한 내용은 섹션 11 참조)

**처리 내용**:
- 작은 파일 우선 처리 (크기 기준 정렬)
- 파일 열어서 인코딩 감지 (`charset-normalizer`)
- 빠른 지문 생성 (xxhash, head+tail)
- `FileMeta` 업데이트
- UI 업데이트

**구현 위치**: `src/gui/workers/enrich_worker.py`

```python
# EnrichWorker.run()
1. file_id 리스트 수집 (작은 파일 우선 정렬)
2. 각 파일마다:
   - FileMeta 조회
   - enrich_file() 호출
     - 파일 열기 (rb 모드)
     - 인코딩 감지 (최대 5MB, 텍스트 파일만)
     - 빠른 지문 생성 (head 2KB + tail 512B)
   - FileMeta 업데이트
   - 배치 리스트에 추가
3. 배치 크기(100개) 도달 시 _emit_batch() 호출
4. 각 파일마다 개별 enrichment_item_completed Signal emit (⚠️ 진짜 배치 아님, 자세한 내용은 섹션 11 참조)
5. Enrich 완료 시그널 emit
```

**최적화 포인트**:
- 작은 파일 우선: 빠른 피드백
- 인코딩 감지 선택적: 큰 파일(>5MB) 또는 바이너리 건너뛰기
- 파일 한 번만 열기: 인코딩/지문 통합 처리

---

## 3. 데이터 흐름 및 상태 관리

**Status**: Implemented

### 3.1 데이터 모델 계층

```
FileMeta (스캔 단계, 경량)
├── file_id: int
├── path_str: str
├── name: str
├── ext: str
├── size: int
├── mtime: float
├── is_text_guess: bool
├── encoding_detected: Optional[str]  ← Enrich 단계에서 채움
├── encoding_confidence: Optional[float]
└── fingerprint_fast: Optional[str]   ← Enrich 단계에서 채움

FileRecord (도메인 모델, 무거움)
├── file_id: int
├── path: Path
├── name: str
├── ext: str
├── size: int
├── mtime: float
├── is_text: bool
├── encoding_detected: Optional[str]
├── encoding_confidence: Optional[float]
├── fingerprint_fast: Optional[str]
└── hash_strong: Optional[str]        ← 분석 단계에서 채움

FileRow (UI 뷰모델, 최적화됨)
├── file_id: int
├── short_path: str  (상대 경로)
├── size: int
├── mtime: float
├── encoding: Optional[str]
├── group_id: Optional[int]
├── group_type: Optional[str]
├── canonical: bool
├── similarity: Optional[float]
└── ...
```

### 3.2 데이터 모델 메모리 사용량

**Status**: Observed (추정, 실측 필요)

**현재 문서 상태**: 실측 프로파일링 결과 없음, 추정값만 제공

**임시 추정** (검증 필요):
- **FileMeta**: Python 객체 오버헤드 고려 시 실제 메모리 사용량은 1KB보다 클 수 있음 (수 KB~수십 KB도 가능)
- **FileRow**: 유사한 크기 (추정)
- **ResultStore**: 파일 수에 선형 증가 (O(n))

**권장 사항**:
- 실제 메모리 프로파일링 수행 (예: `memory_profiler`, `tracemalloc`)
- 다양한 파일 수(100, 1K, 10K)에 대한 측정 결과 문서화
- 메모리 사용량 표 추가

### 3.3 결과 파이프라인 상세

#### 파이프라인 구성 요소

**1. ResultStore (Single Source of Truth)**
- 스레드 안전한 중앙 저장소
- `_rows_by_id: dict[int, FileRow]` (파일 ID → FileRow)
- `_groups_by_id: dict[int, DuplicateGroup]` (중복 그룹)
- `_issues_by_file_id: dict[int, list[IntegrityIssue]]` (무결성 이슈)
- `Lock`을 사용한 동기화

**2. UIBatcher (배치 처리기)**
- 목적: Signal emit 오버헤드 감소
- 배치 정책:
  - Append: 최대 1000개씩
  - Update: 최대 500개씩
  - 플러시 간격: 16ms (60fps)
- 타이머 기반 자동 플러시

**3. ResultEventRouter (이벤트 라우터)**
- Signal → Store → Model 순서로 전파
- 배치 처리 통합
- 이벤트 타입별 분기 처리

**4. ResultIndexManager**
- 빠른 조회를 위한 인덱스 관리
- ResultStore를 참조하여 인덱스 유지

**5. ResultTableModel (Qt Model)**
- ResultStore를 소스로 사용
- `beginInsertRows` / `endInsertRows` 신호 emit
- 정렬/필터 지원

**6. ResultSortFilterProxyModel**
- 테이블 정렬/필터링
- 사용자 인터랙션 처리

### 3.4 UI 업데이트 흐름

```
Worker Thread (QRunnable)
  ↓ emit Signal
ResultSignals (Qt Signal)
  ↓ emit rows_appended([FileRow, ...])
UIBatcher.enqueue_append([FileRow, ...])
  ↓ 큐에 적재 (타이머 시작)
QTimer (16ms 간격)
  ↓ timeout
UIBatcher._flush()
  ↓ rows_appended.emit(chunk)  (최대 1000개)
ResultEventRouter._on_rows_appended(chunk)
  ↓
ResultStore.add_rows(chunk)  (Lock 획득)
  ↓
ResultTableModel 데이터 변경 감지
  ↓ beginInsertRows / endInsertRows emit
QTableView (UI 스레드)
  ↓
화면 업데이트
```

---

## 4. 핵심 로직 및 알고리즘

**Status**: Implemented

### 4.1 파일 스캔 로직

**FileScanner.scan_directory()**
```python
# 최적화 포인트
1. os.scandir() 사용 (stat 캐시 활용)
2. Path 객체 생성 없이 문자열 연산
3. 확장자 필터: set 조회 (O(1))
4. 숨김 파일: 파일명 기반 체크
5. 재귀 스캔: generator로 스트리밍
```

**성능 특성** (Observed, 측정 조건 명시 필요):
- FS traversal 속도: 측정 필요 (files/sec)
- 메모리 효율: generator로 스트리밍
- 병렬 처리 가능 구조 (현재는 단일 스레드)

### 4.2 인코딩 감지 로직

**EncodingDetector.detect_from_bytes()**
```python
# charset-normalizer 사용
1. 샘플 크기: 최대 131,072 bytes (128KB)
2. confidence threshold: 기본 0.7
3. 텍스트 파일만 처리 (확장자 기반)
4. 큰 파일(>5MB) 건너뛰기
```

**최적화**:
- 파일 전체 읽기 없음 (샘플만)
- 텍스트 파일 확장자 사전 필터링
- 큰 파일은 인코딩 감지 건너뛰기

### 4.3 빠른 지문 생성 로직

**FingerprintGenerator.generate_fast_fingerprint()**
```python
# xxhash 사용 (비암호화 해시)
1. 작은 파일(<512B): 건너뛰기
2. 일반 파일:
   - head: 최대 2KB
   - tail: 512B (파일 크기 > 2KB인 경우)
3. xxhash.xxh64() 사용
4. hexdigest() 반환
```

**목적**:
- 초기 중복 후보 탐지 (빠른 비교)
- 전체 해시는 별도 단계에서 계산

### 4.4 배치 처리 로직

**UIBatcher**
```python
# 배치 정책
- Append 큐: 최대 1000개씩 처리
- Update 큐: 최대 500개씩 처리
- 플러시 간격: 16ms (60fps 목표)
- 큐가 비면 타이머 자동 중지
```

**효과**:
- Signal emit 횟수 99% 감소
- UI 반응성 유지 (60fps)
- 메모리 사용량 최적화

---

## 5. 실행 순서 및 타임라인

**Status**: Implemented

### 5.1 정상 실행 시나리오

```
[시작] 프로그램 실행
  │
  ├─ [0ms] QApplication 생성
  ├─ [50ms] MainWindow 초기화
  │   ├─ 파이프라인 조립
  │   ├─ UI 구성 요소 생성
  │   └─ QSettings 복원
  │
  ├─ [100ms] UI 표시 (window.show())
  │
  ├─ [150ms] 자동 Preview 스캔 시작
  │   ├─ PreviewWorker 생성
  │   └─ QThreadPool에 작업 제출
  │
  ├─ [200ms ~ 2초] Preview 스캔 진행
  │   ├─ os.scandir()로 디렉토리 순회
  │   ├─ 파일 수 카운트
  │   └─ 확장자 분포 집계
  │
  ├─ [2초] Preview 완료
  │   ├─ PreviewStats 생성
  │   ├─ preview_completed 시그널 emit
  │   └─ UI에 예상 파일 수 표시
  │
  ├─ [사용자 액션] "스캔 시작" 버튼 클릭
  │
  ├─ [스캔 시작] Main Scan 시작
  │   ├─ Preview 모드 숨김
  │   ├─ 결과 저장소 초기화
  │   ├─ ScanWorker 생성
  │   └─ QThreadPool에 작업 제출
  │
  ├─ [스캔 진행] Main Scan 실행
  │   ├─ FileScanner.scan_directory()
  │   ├─ 각 파일마다 FileMeta 생성
  │   ├─ FileRepository.save_meta()
  │   ├─ FileRow 생성 및 배치 큐 적재
  │   ├─ 2000개마다 Signal emit
  │   └─ 50개마다 진행률 업데이트
  │
  ├─ [스캔 완료] log_event("INFO", "스캔 완료", None) emit
  │
  ├─ [자동] Enrich 스캔 시작
  │   ├─ _on_log_event에서 "스캔 완료" 문자열 감지 (⚠️ 취약점)
  │   ├─ file_id 리스트 수집 (작은 파일 우선)
  │   ├─ EnrichWorker 생성
  │   └─ QThreadPool에 작업 제출
  │
  ├─ [Enrich 진행] Enrich 실행
  │   ├─ 각 파일마다:
  │   │   ├─ 파일 열기 (rb)
  │   │   ├─ 인코딩 감지
  │   │   ├─ 빠른 지문 생성
  │   │   └─ FileMeta 업데이트
  │   ├─ 100개마다 배치 모음 (⚠️ 실제로는 개별 Signal emit, 자세한 내용은 섹션 11 참조)
  │   └─ UI에 인코딩 정보 표시
  │
  └─ [완료] Enrich 완료
      └─ 모든 파일 정보 수집 완료
```

### 5.2 취소 시나리오

**Status**: Implemented

```
[스캔 진행 중] 사용자가 "중지" 버튼 클릭
  │
  ├─ _on_stop_scan() 호출
  │   ├─ cancel_flag.set() 호출
  │   ├─ Enrich 트리거 금지 (상태 확인 필요)
  │   └─ UI 상태 복원 시작
  │
  ├─ Worker.run() 루프에서 cancel_flag 체크
  │
  ├─ 취소 감지 시:
  │   ├─ 현재 배치 완료 후 중단
  │   ├─ 남은 배치 1회 emit (최대 BATCH_SIZE)
  │   ├─ 로그 기록: "스캔 취소됨"
  │   └─ return (작업 종료)
  │
  ├─ MainWindow 취소 처리:
  │   ├─ 스캔 버튼 활성화
  │   ├─ 입력 필드 잠금 해제
  │   ├─ 진행률 바 리셋
  │   └─ sorting 복원
  │
  ├─ UIBatcher 큐 처리:
  │   └─ 현재 정책: [flush / discard 선택 필요] (⚠️ 미명시)
  │   └─ 권장: final flush (남은 큐 1회 처리 후 정리)
  │
  └─ Repository 상태:
      ├─ 현재까지 저장된 FileMeta는 유지
      └─ 새로운 save_meta 중단
```

**취소 시 세부 규칙** (명확화 필요):

1. **ScanWorker 취소**:
   - `cancel_flag.set()` 감지 즉시 현재 루프 반복 완료
   - 남은 배치 최대 1회 emit (현재 구현 확인)
   - 로그 기록 후 return

2. **MainWindow 취소 처리**:
   - `_on_stop_scan()`에서 `cancel_flag.set()` 호출
   - Enrich 트리거 금지 (현재는 로그 문자열 감지 방식이므로 취소 플래그 확인 필요)
   - UI 상태 복원 (버튼, 입력 필드, 진행률 바, sorting)

3. **UIBatcher 큐 처리**:
   - **현재 정책**: 미명시 (⚠️ 버그 재발 포인트)
   - **권장**: final flush (남은 큐 1회 처리 후 정리)

4. **Repository 상태**:
   - 현재까지 저장된 FileMeta는 유지 (취소되어도 부분 결과 보존)
   - 새로운 save_meta 중단

---

## 6. 성능 특성 및 최적화

**Status**: Observed (측정 조건 명시 필요)

### 6.1 측정 환경 표준화

**현재 문서 상태**: 실측 데이터 없음, 측정 환경 미명시

**측정 시 다음 조건을 명시해야 함**:

1. **저장장치**: HDD / SSD / 외장 드라이브 / 네트워크 드라이브
2. **파일 특성**: 
   - 파일 수
   - 평균 크기 (bytes)
   - 확장자 분포 (예: .txt 80%, .md 15%, .log 5%)
3. **측정 방식**: 
   - stat-only / open 포함 / UI 업데이트 포함 여부
   - 단계별 분리 측정 (FS traversal, Repository 저장, UI 반영)
4. **측정 시점**: 
   - 커밋 해시
   - 날짜/시간
   - 빌드 타입 (debug/release)
   - Python 버전
5. **시스템 환경**:
   - OS 버전
   - CPU (코어 수, 클럭)
   - RAM 크기
   - 백그라운드 프로세스 영향

### 6.2 단계별 SLA (Target vs Observed)

#### 1. Preview Scan (FS traversal only)

**Target**: 10,000개 파일 < 2초

**Observed**: [실측 데이터 필요]
- 측정 방식: os.scandir()만, stat 직접 호출 0회 (entry.is_file()는 호출하나 stat()은 호출 안 함)
- 측정 환경: [저장장치, 파일 특성, 시스템 환경]
- 결과: [files/sec, 실제 소요 시간]

**측정 항목**:
- FS traversal 속도: [files/sec]
- 메모리 사용량: [MB]

---

#### 2. Main Scan (stat + FileMeta 생성)

**Target**: 10,000개 파일 < 10초 (stat-only 기준)

**Observed**: [실측 데이터 필요]
- 측정 방식: FileScanner.scan_directory() + FileMeta 생성, UI 업데이트 제외
- 측정 환경: [저장장치, 파일 특성, 시스템 환경]
- 결과: [files/sec, 실제 소요 시간]

**측정 항목**:
- FS traversal 속도: [files/sec] (stat 포함)
- Repository 저장 속도: [files/sec]
- 메모리 사용량: [MB] (FileMeta 기준)

**⚠️ 참고**: 현재 문서의 "1000개 파일 약 30초" 수치는 측정 조건 불명으로 신뢰도 낮음

---

#### 3. Enrich (open + encoding + fingerprint)

**Target**: 2,000개 작은 파일 (<100KB) < 10초

**Observed**: [실측 데이터 필요]
- 측정 방식: 파일 열기 + 인코딩 감지 + 빠른 지문 생성
- 측정 환경: [저장장치, 파일 특성(평균 크기), 시스템 환경]
- 결과: [files/sec, 실제 소요 시간]

**측정 항목**:
- 파일 처리 속도: [files/sec]
- 인코딩 감지 속도: [files/sec]
- 빠른 지문 생성 속도: [files/sec]
- 메모리 사용량: [MB]

**⚠️ 참고**: 작은 파일 우선 처리로 빠른 피드백 제공

---

### 6.3 성능 병목 분석 (Observed)

**현재 문서 상태**: 실측 데이터 없음, 병목 분석 불가

**측정 시 다음 항목을 분석해야 함**:

1. **FS traversal 속도** (Preview/Scan)
   - `os.scandir()` 호출 시간
   - `entry.stat()` 호출 시간
   - 확장자 필터링 시간

2. **Repository 저장 속도** (Scan)
   - `save_meta()` 호출 시간
   - 딕셔너리 insert 시간

3. **UI 반영 속도** (Scan/Enrich)
   - Signal emit 시간
   - UIBatcher 큐 처리 시간
   - Model 업데이트 시간 (beginInsertRows/endInsertRows)
   - View 렌더링 시간

**성능 프로파일링 권장 도구**:
- Python: `cProfile`, `line_profiler`, `memory_profiler`
- Qt: Qt Creator Profiler, `QElapsedTimer`

---

### 6.4 최적화 기법

**Status**: Implemented

1. **2-pass 제거**: generator 직접 사용
2. **Path 객체 생성 최소화**: 문자열 연산 사용
3. **배치 처리**: Signal emit 횟수 99% 감소 (UIBatcher 활용)
4. **지연 처리**: Enrich는 별도 단계로 분리
5. **선택적 처리**: 큰 파일(>5MB) 또는 바이너리 건너뛰기
6. **캐싱**: stat 정보 재사용 (DirEntry 캐시 활용)
7. **스트리밍**: 전체 메모리 로드 없음 (generator 사용)

---

## 7. 주요 의존성 및 설정

**Status**: Implemented

### 7.1 필수 패키지
- **PySide6** (>=6.6.0): GUI 프레임워크
- **charset-normalizer** (>=3.0.0): 인코딩 자동 감지
- **pydantic** (>=2.0.0): 데이터 모델 검증
- **xxhash** (>=3.4.0): 빠른 해시 계산

### 7.2 설정 관리
- **QSettings**: 사용자 설정 저장 (Windows Registry/파일)
  - 마지막 선택 폴더
  - 확장자 필터
  - 스캔 옵션 (recursive, include_hidden 등)

---

## 8. 에러 처리 및 복구

**Status**: Implemented

### 8.1 에러 처리 전략

**파일 시스템 에러**:
- `OSError`, `PermissionError`: 로그만 남기고 계속 진행
- 심볼릭 링크 해석 실패: 건너뛰기
- 접근 권한 없음: 경고 로그

**파일 처리 에러**:
- 인코딩 감지 실패: `encoding_detected = None`
- 빠른 지문 생성 실패: `fingerprint_fast = None`
- 개별 파일 오류는 전체 스캔 중단하지 않음

**Worker 스레드 에러**:
- try-except로 전체 루프 보호
- 에러 발생 시 Signal로 UI에 전달
- 로그 기록

### 8.2 취소 메커니즘

**구현**:
- `threading.Event` 객체 사용
- Worker 루프에서 주기적 체크
- 취소 시 안전하게 종료 (남은 배치 처리)

**세부 규칙**: 섹션 5.2 참조

---

## 9. 확장성 및 향후 계획

**Status**: Planned

### 9.1 현재 아키텍처의 장점

1. **레이어 분리**: UI / UseCase / Infrastructure 명확히 분리
2. **비동기 처리**: Worker 스레드로 UI 블로킹 방지
3. **배치 처리**: 대량 파일 처리 최적화
4. **확장 가능**: 새로운 UseCase 추가 용이

### 9.2 향후 개선 방향

**v1.5 계획**:
- 중복 탐지 UseCase 통합
- 무결성 검사 UseCase 통합
- 파일명 파싱 기능

**v2 계획**:
- 유사본 탐지 (SimHash)
- 병렬 처리 (멀티 스레드 스캔)
- 데이터베이스 영속화 (SQLite)

---

## 10. Progress 정의 및 계산 규칙

**Status**: Implemented

### 10.1 Progress 계산 공식

**전체 진행률 (Overall Progress)**:
```python
overall_progress = int((done / total * 100)) if total > 0 else 0
```
- 범위: 0~100%
- Label: `{overall_progress}%`
- Indeterminate 모드: `total == -1` 또는 `total == 0`일 때 progress bar를 indeterminate로 설정

**단계별 진행률 (Stage Progress)**:
- Preview: 파일 수 카운트 (indeterminate, total 미지)
- Scan: `files_processed / files_total` (determinate, Preview 결과 또는 -1)
- Enrich: `files_processed / files_total` (determinate)

### 10.2 진행률 업데이트 간격

- **Scan**: 50개마다 (`PROGRESS_UPDATE_INTERVAL = 50`)
- **Enrich**: 20개마다 (`PROGRESS_UPDATE_INTERVAL = 20`)

**목적**: Signal emit 오버헤드 감소

### 10.3 Indeterminate vs Determinate 모드

**Indeterminate 모드** (`total == -1` 또는 `total == None`):
- Preview Scan: 전체 파일 수 미지
- 진행률 바: 무한 애니메이션 (range 0~0)
- 표시: `{done:,} files` (퍼센트 대신)

**Determinate 모드** (`total > 0`):
- Main Scan: Preview 결과 또는 사용자 지정
- Enrich: 파일 수 알려짐
- 진행률 바: 0~total 범위, done 값 표시
- 표시: `{overall_progress}%`

---

## 11. 부록: 구현 상태 및 알려진 이슈

**Status**: Observed

### 11.1 Enrich 트리거 취약점

**현재 구현** (`src/gui/views/main_window.py:2158`):
```python
def _on_log_event(self, level: str, msg: str, file_id: object) -> None:
    # 스캔 완료 감지 시 Enrich 자동 시작
    if level == "INFO" and msg == "스캔 완료":
        self._start_enrich_scan()
```

**취약점**:
1. **로그 문자열 감지**: i18n/문구 변경/중복 로그에 취약
2. **Dry Run 등 다른 모드**: 오작동 가능
3. **테스트 어려움**: 문자열 매칭에 의존

**권장 개선 방안**:
1. `ResultSignals`에 명시적 `scan_completed` 시그널 추가
2. `ScanWorker`에서 `scan_completed(total_files, elapsed_ms)` 시그널 emit
3. `MainWindow`에서 시그널로 연결 (로그 문자열 감지 제거)
4. 상태 머신으로 관리: `IDLE → PREVIEWING → SCANNING → ENRICHING → DONE / CANCELED / ERROR`

**상태 머신 다이어그램**:
```
stateDiagram-v2
    [*] --> IDLE
    IDLE --> PREVIEWING: 폴더 선택
    PREVIEWING --> IDLE: 취소
    PREVIEWING --> SCANNING: Preview 완료 + 스캔 시작
    SCANNING --> IDLE: 취소
    SCANNING --> ENRICHING: scan_completed 시그널
    ENRICHING --> IDLE: 취소
    ENRICHING --> DONE: enrichment_completed 시그널
    DONE --> IDLE: 재시작
```

### 11.2 Enrich 배치 처리 문제

**현재 구현** (`src/gui/workers/enrich_worker.py:143-165`):
```python
def _emit_batch(
    self, 
    batch_updates: list[tuple[int, str, Optional[str], Optional[float], Optional[str]]]
) -> None:
    """배치 업데이트를 Signal로 emit."""
    for file_id, path_str, encoding, confidence, fingerprint in batch_updates:
        # Repository 업데이트
        self.repository.update_meta(...)
        
        # 개별 Signal emit (⚠️ 진짜 배치가 아님)
        self.signals.enrichment_item_completed.emit(file_id, encoding, fingerprint)
    
    # 배치 완료 Signal emit
    self.signals.enrichment_batch_completed.emit(len(batch_updates))
```

**문제점**:
- **실제로는 배치가 아님**: 100개 모았다가 100번 Signal emit
- **UI 이벤트 폭주**: 마지막 구간 프리징의 원인일 가능성
- **MainWindow에서 개별 처리**: `_on_enrichment_item_completed`가 각 파일마다 호출되어 FileRow 업데이트

**성능 영향**:
- Signal emit 횟수: 100개 배치당 100회 (Scan의 2000개 배치당 1회와 비교 시 매우 많음)
- UI 업데이트 빈도: 파일당 1회 (UIBatcher를 통과하더라도 개별 Signal 처리)

**권장 개선 방안**:
1. `enrichment_item_completed`를 배치로 변경: `enrichment_items_completed.emit(list[FileRow])`
2. 또는 UIBatcher를 통한 배치 처리 활용 (현재 `rows_updated`는 UIBatcher를 거치지 않음)
3. `MainWindow`에서 배치 업데이트 처리

### 11.3 취소 시 UIBatcher 큐 처리 정책 미명시

**현재 문제**: 취소 시 UIBatcher 큐를 flush할지 discard할지 미명시

**영향**: 취소 후 UI 상태 불일치 가능성

**권장 정책**: final flush (남은 큐 1회 처리 후 정리)

**구현 필요**: `UIBatcher`에 `final_flush()` 메서드 추가, `MainWindow._on_stop_scan()`에서 호출

### 11.4 성능 지표 측정 데이터 부재

**현재 상태**: 모든 성능 지표가 추정치 또는 측정 조건 미명시

**권장 사항**:
1. 표준 벤치마크 데이터셋 생성
2. 자동화된 성능 테스트 스크립트 작성
3. 측정 결과를 CSV/JSON으로 저장하여 문서화
4. CI/CD에 성능 회귀 테스트 추가

---

## 12. 결론

**Status**: Intended Design

NovelGuard는 **안전성과 성능을 모두 고려한 아키텍처**로 설계되었습니다:

- ✅ **3단계 스캔 프로세스**: Preview → Scan → Enrich로 점진적 정보 수집
- ✅ **배치 처리 파이프라인**: UI 반응성 유지하면서 대량 데이터 처리
- ✅ **비동기 Worker 패턴**: UI 블로킹 없이 백그라운드 작업 수행
- ✅ **최적화된 파일 처리**: 2-pass 제거, Path 객체 최소화, 선택적 처리
- ✅ **스레드 안전성**: Lock을 사용한 안전한 상태 관리

**알려진 개선 사항**:
- ⚠️ Enrich 트리거 취약점 (섹션 11.1)
- ⚠️ Enrich 배치 처리 문제 (섹션 11.2)
- ⚠️ 성능 지표 측정 데이터 부재 (섹션 11.4)

이러한 설계로 **수만 개의 파일을 안정적으로 처리**하면서도 **사용자에게 빠른 피드백**을 제공할 수 있습니다.

---

## 문서 변경 이력

- **v1.1** (2025-01-09): Observed vs Intended 분리, 성능 지표 표준화, 구현 상태 및 알려진 이슈 추가
- **v1.0** (2025-01-09): 초기 버전
