# Integrity Check and UTF-8 Conversion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace finalize **「무결성 검사 (미구현)」** with real MVP integrity checks, auto-run after apply (including `[전체 작업 실행]`), enabled encoding buttons, and **safe auto UTF-8 conversion** with `.novelguard.bak` backups.

**Architecture:** `IntegrityCheckService` (domain) + `CheckIntegrityUseCase` / `ConvertFilesToUtf8UseCase` (application) + charset-normalizer adapter (infra). GUI runs work on `IntegrityWorker` / `Utf8ConvertWorker` via extended `QtJobManager`; `IntegrityViewModel` chains auto finalize flow; `FinalizeSection` blocks on `finalize_flow_completed`.

**Tech Stack:** Python 3.12, PySide6, `charset-normalizer` (already in `pyproject.toml`), existing `FileDataStore`, `QtJobManager`, `WorkPipelineRunner`.

**Spec:** [../specs/2026-05-22-integrity-check-design.md](../specs/2026-05-22-integrity-check-design.md) (approved 2026-05-22)

**Prerequisite:** Workflow pipeline UI plan landed (`FinalizeSection`, `WorkPipelineRunner._begin_finalize`). `python scripts/verify_phase_completion.py` PASS before starting.

---

## File map

| Path | Responsibility |
|------|----------------|
| `src/domain/ports/text_encoding.py` | **Create** — `EncodingDetection`, `ITextEncodingDetector` |
| `src/domain/services/integrity_check_service.py` | **Create** — pure rule evaluation |
| `src/application/constants.py` | **Modify** — `INTEGRITY_SAMPLE_BYTES`, `ENCODING_MIN_CONFIDENCE`, `UTF8_BACKUP_SUFFIX` |
| `src/application/exceptions.py` | **Modify** — `FileEncodingError`, `FileConvertError` |
| `src/application/dto/integrity_issue.py` | **Create** |
| `src/application/dto/integrity_check_request.py` | **Create** |
| `src/application/dto/integrity_check_result.py` | **Create** |
| `src/application/dto/utf8_convert_request.py` | **Create** |
| `src/application/dto/utf8_convert_result.py` | **Create** |
| `src/application/ports/file_content_reader.py` | **Create** — `FileContentReader` Protocol |
| `src/application/use_cases/check_integrity.py` | **Create** |
| `src/application/use_cases/convert_files_to_utf8.py` | **Create** |
| `src/infrastructure/encoding/charset_normalizer_detector.py` | **Create** |
| `src/infrastructure/filesystem/file_content_reader.py` | **Create** |
| `src/gui/workers/integrity_worker.py` | **Create** |
| `src/gui/workers/utf8_convert_worker.py` | **Create** |
| `src/gui/view_models/integrity_view_model.py` | **Create** |
| `src/application/ports/job_runner.py` | **Modify** — `start_integrity_check`, `start_utf8_convert` |
| `src/gui/services/qt_job_manager.py` | **Modify** — wire workers + events |
| `src/gui/models/file_data_store.py` | **Modify** — `clear_integrity_for_files`, `reset_integrity` helper |
| `src/gui/views/work/sections/finalize_section.py` | **Modify** — VM wiring, buttons, auto flow |
| `src/gui/view_models/work_pipeline_dto.py` | **Modify** — extend `FinalizeSubstate` |
| `src/app/main.py` | **Modify** — composition |
| `src/gui/views/main_window.py` | **Modify** — inject VM, stats refresh |
| `src/gui/views/work/pipeline_run_confirm_sheet.py` | **Modify** — UTF-8 auto line |
| `tests/unit/domain/services/test_integrity_check_service.py` | **Create** |
| `tests/application/use_cases/test_check_integrity.py` | **Create** |
| `tests/application/use_cases/test_convert_files_to_utf8.py` | **Create** |
| `tests/infrastructure/encoding/test_charset_normalizer_detector.py` | **Create** |
| `tests/fixtures/encoding/utf8_sample.txt` | **Create** |
| `tests/fixtures/encoding/cp949_sample.txt` | **Create** (bytes CP949) |
| `tests/gui/view_models/test_integrity_view_model.py` | **Create** |
| `tests/gui/services/test_qt_job_manager_integrity.py` | **Create** |

---

### Task 1: Domain port + integrity rules

**Files:**
- Create: `src/domain/ports/text_encoding.py`
- Create: `src/domain/services/integrity_check_service.py`
- Modify: `src/application/constants.py`
- Test: `tests/unit/domain/services/test_integrity_check_service.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/unit/domain/services/test_integrity_check_service.py
from application.constants import Constants
from domain.services.integrity_check_service import IntegrityCheckService, IntegrityRuleId


def test_empty_file_error() -> None:
    issues = IntegrityCheckService.evaluate(
        size=0,
        encoding=None,
        confidence=None,
        decode_ok=True,
        min_text_size=Constants.MIN_TEXT_FILE_SIZE,
        min_confidence=0.7,
    )
    assert any(i.rule_id == IntegrityRuleId.EMPTY_FILE and i.severity == "ERROR" for i in issues)


def test_small_file_warn() -> None:
    issues = IntegrityCheckService.evaluate(
        size=50,
        encoding="utf-8",
        confidence=0.99,
        decode_ok=True,
        min_text_size=Constants.MIN_TEXT_FILE_SIZE,
        min_confidence=0.7,
    )
    assert any(i.rule_id == IntegrityRuleId.SMALL_FILE for i in issues)


def test_non_utf8_info() -> None:
    issues = IntegrityCheckService.evaluate(
        size=500,
        encoding="cp949",
        confidence=0.95,
        decode_ok=True,
        min_text_size=Constants.MIN_TEXT_FILE_SIZE,
        min_confidence=0.7,
    )
    assert any(i.rule_id == IntegrityRuleId.ENCODING_NON_UTF8 and i.severity == "INFO" for i in issues)
```

- [ ] **Step 2: Run test — expect FAIL**

```bash
pytest tests/unit/domain/services/test_integrity_check_service.py -v
```

- [ ] **Step 3: Implement**

`IntegrityRuleId` StrEnum; `IntegrityIssueDto` frozen dataclass in domain or return tuples consumed by application DTO mapper (prefer `domain/value_objects/integrity_issue.py` if VO folder exists; else dataclass in service module).

`normalize_encoding(name: str | None) -> str | None` maps `utf8`, `UTF_8` → `utf-8`.

`evaluate(...)` returns list ordered ERROR > WARN > INFO; include `DECODE_ERROR` when `decode_ok` is False.

Add to `application/constants.py`:

```python
INTEGRITY_SAMPLE_BYTES: Final[int] = 65536
ENCODING_MIN_CONFIDENCE: Final[float] = 0.7
UTF8_BACKUP_SUFFIX: Final[str] = ".novelguard.bak"
```

- [ ] **Step 4: Run test — expect PASS**

```bash
pytest tests/unit/domain/services/test_integrity_check_service.py -v
```

- [ ] **Step 5: Commit**

```bash
git add src/domain/ports/text_encoding.py src/domain/services/integrity_check_service.py src/application/constants.py tests/unit/domain/services/test_integrity_check_service.py
git commit -m "[domain] integrity check rules and encoding port"
```

---

### Task 2: Application DTOs + exceptions

**Files:**
- Create: `src/application/dto/integrity_issue.py`, `integrity_check_request.py`, `integrity_check_result.py`, `utf8_convert_request.py`, `utf8_convert_result.py`
- Modify: `src/application/exceptions.py`

- [ ] **Step 1: Implement DTOs (no test file — covered in Task 3)**

```python
# src/application/dto/integrity_issue.py
from dataclasses import dataclass

@dataclass(frozen=True)
class IntegrityIssue:
    rule_id: str
    message: str
    severity: str  # INFO | WARN | ERROR


# src/application/dto/integrity_check_request.py
from dataclasses import dataclass

@dataclass(frozen=True)
class IntegrityCheckRequest:
    file_ids: list[int] | None = None


# src/application/dto/integrity_check_result.py
from dataclasses import dataclass
from application.dto.integrity_issue import IntegrityIssue

@dataclass(frozen=True)
class IntegrityCheckResult:
    file_id: int
    issues: list[IntegrityIssue]
    encoding: str | None
    encoding_confidence: float | None


# src/application/dto/utf8_convert_request.py
from dataclasses import dataclass
from typing import Literal

Utf8ConvertMode = Literal["auto_eligible", "manual_default", "manual_include_info"]

@dataclass(frozen=True)
class Utf8ConvertRequest:
    file_ids: list[int] | None
    mode: Utf8ConvertMode


# src/application/dto/utf8_convert_result.py
from dataclasses import dataclass

@dataclass(frozen=True)
class Utf8ConvertResult:
    converted: int
    skipped: int
    failed: int
    errors: list[str]
```

```python
# src/application/exceptions.py
class FileEncodingError(Exception):
    """Encoding detection or decode failed."""

class FileConvertError(Exception):
    """UTF-8 conversion or backup failed."""
```

- [ ] **Step 2: Commit**

```bash
git add src/application/dto/integrity_issue.py src/application/dto/integrity_check_request.py src/application/dto/integrity_check_result.py src/application/dto/utf8_convert_request.py src/application/dto/utf8_convert_result.py src/application/exceptions.py
git commit -m "[application] integrity and utf8 convert DTOs"
```

---

### Task 3: File content reader port + CheckIntegrityUseCase

**Files:**
- Create: `src/application/ports/file_content_reader.py`
- Create: `src/application/use_cases/check_integrity.py`
- Test: `tests/application/use_cases/test_check_integrity.py`

- [ ] **Step 1: Write failing test with fakes**

```python
# tests/application/use_cases/test_check_integrity.py
from pathlib import Path
from application.dto.integrity_check_request import IntegrityCheckRequest
from application.dto.file_data import FileData
from application.use_cases.check_integrity import CheckIntegrityUseCase
from domain.ports.text_encoding import EncodingDetection


class FakeReader:
    def read_bytes(self, path: Path, max_bytes: int | None = None) -> bytes:
        if max_bytes:
            return b"hello"
        return b"hello"


class FakeDetector:
    def detect(self, sample: bytes) -> EncodingDetection:
        return EncodingDetection(encoding="utf-8", confidence=0.99)


class FakeStore:
    def __init__(self) -> None:
        self.files = [
            FileData(
                file_id=1,
                path=Path("/tmp/a.txt"),
                size=500,
                mtime=0.0,
                extension=".txt",
            )
        ]

    def get_all_files(self) -> list[FileData]:
        return self.files


def test_check_integrity_returns_result() -> None:
    uc = CheckIntegrityUseCase(FakeStore(), FakeReader(), FakeDetector())
    results = uc.execute(IntegrityCheckRequest())
    assert len(results) == 1
    assert results[0].file_id == 1
```

- [ ] **Step 2: Run — expect FAIL**

```bash
pytest tests/application/use_cases/test_check_integrity.py -v
```

- [ ] **Step 3: Implement use case**

- Resolve file list from `request.file_ids` or `store.get_all_files()`.
- Skip missing paths gracefully (log via optional log_sink).
- Read `Constants.INTEGRITY_SAMPLE_BYTES`; detect; `decode_ok = _try_decode(sample, encoding)`.
- Map domain issues → `IntegrityIssue` DTOs.
- Optional `progress_callback(processed, total, path_name)`.

- [ ] **Step 4: PASS + commit**

```bash
pytest tests/application/use_cases/test_check_integrity.py -v
git add src/application/ports/file_content_reader.py src/application/use_cases/check_integrity.py tests/application/use_cases/test_check_integrity.py
git commit -m "[application] CheckIntegrityUseCase"
```

---

### Task 4: ConvertFilesToUtf8UseCase

**Files:**
- Create: `src/application/use_cases/convert_files_to_utf8.py`
- Create: `tests/fixtures/encoding/cp949_sample.txt` (write CP949 bytes for "안녕")
- Test: `tests/application/use_cases/test_convert_files_to_utf8.py`

- [ ] **Step 1: Write failing test**

```python
# tests/application/use_cases/test_convert_files_to_utf8.py
import tempfile
from pathlib import Path
from application.dto.file_data import FileData
from application.dto.utf8_convert_request import Utf8ConvertRequest
from application.use_cases.convert_files_to_utf8 import ConvertFilesToUtf8UseCase
from infrastructure.filesystem.file_content_reader import FileSystemContentReader


def test_convert_cp949_to_utf8_with_backup() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "a.txt"
        path.write_bytes("안녕하세요".encode("cp949"))
        store = _Store([FileData(file_id=1, path=path, size=path.stat().st_size, mtime=0.0, extension=".txt")])
        uc = ConvertFilesToUtf8UseCase(store, FileSystemContentReader())
        result = uc.execute(
            Utf8ConvertRequest(file_ids=[1], mode="auto_eligible"),
            encoding_by_file_id={1: ("cp949", 0.95)},
        )
        assert result.converted == 1
        assert path.read_bytes().startswith(b"\xec")  # UTF-8 Korean
        assert (path.parent / "a.txt.novelguard.bak").exists() or (path.with_suffix(path.suffix + ".novelguard.bak")).exists()
```

Note: implement `encoding_by_file_id` parameter on `execute` (worker passes from store after integrity) OR read from `FileData.encoding` on store — prefer **store fields** after integrity run.

- [ ] **Step 2–4: Implement, test, commit**

Policy:
- `auto_eligible`: INFO non-utf8, confidence OK, no ERROR rules on file, full decode OK.
- Backup path: `path.with_name(path.name + Constants.UTF8_BACKUP_SUFFIX)` (suffix style per spec).
- Skip if backup exists and `backup.stat().st_mtime >= path.stat().st_mtime`.
- On write error: restore from backup, increment `failed`.

```bash
git commit -m "[application] ConvertFilesToUtf8UseCase with backup"
```

---

### Task 5: Infrastructure adapters

**Files:**
- Create: `src/infrastructure/encoding/charset_normalizer_detector.py`
- Create: `src/infrastructure/filesystem/file_content_reader.py`
- Test: `tests/infrastructure/encoding/test_charset_normalizer_detector.py`

- [ ] **Step 1: Test charset detector**

```python
from infrastructure.encoding.charset_normalizer_detector import CharsetNormalizerDetector

def test_detect_utf8() -> None:
    det = CharsetNormalizerDetector()
    r = det.detect("hello".encode())
    assert r.encoding is not None
    assert r.confidence > 0
```

- [ ] **Step 2: Implement**

```python
from charset_normalizer import from_bytes
from domain.ports.text_encoding import EncodingDetection, ITextEncodingDetector

class CharsetNormalizerDetector:
    def detect(self, sample: bytes) -> EncodingDetection:
        if not sample:
            return EncodingDetection(encoding=None, confidence=0.0)
        best = from_bytes(sample).best()
        if best is None:
            return EncodingDetection(encoding=None, confidence=0.0)
        return EncodingDetection(encoding=best.encoding, confidence=float(best.coherence or best.chaos or 0.5))
```

`FileSystemContentReader.read_bytes(path, max_bytes)` — `path.read_bytes()` truncated to `max_bytes`.

- [ ] **Step 3: Commit**

```bash
git commit -m "[infrastructure] encoding detector and file reader"
```

---

### Task 6: FileDataStore integrity reset + worker apply

**Files:**
- Modify: `src/gui/models/file_data_store.py`
- Create: `src/gui/workers/integrity_worker.py`

- [ ] **Step 1: Add store helpers**

```python
def clear_integrity(self, file_id: int) -> None:
    file_data = self._files.get(file_id)
    if not file_data:
        return
    file_data.integrity_issues.clear()
    file_data.integrity_severity = None
    self.file_updated.emit(file_data)
```

- [ ] **Step 2: IntegrityWorker**

Pattern: duplicate worker — inject `CheckIntegrityUseCase`, on each result:
1. `clear_integrity(file_id)`
2. `add_integrity_issue` for each issue
3. `set_encoding(file_id, encoding, confidence)`

Signals: `integrity_completed(list[IntegrityCheckResult])`, `integrity_error(str)`, `integrity_progress(JobProgress)`.

- [ ] **Step 3: Commit**

```bash
git commit -m "[gui] integrity worker and store reset"
```

---

### Task 7: Utf8ConvertWorker + QtJobManager + IJobRunner

**Files:**
- Modify: `src/application/ports/job_runner.py`
- Modify: `src/gui/services/qt_job_manager.py`
- Create: `src/gui/workers/utf8_convert_worker.py`
- Test: `tests/gui/services/test_qt_job_manager_integrity.py`

- [ ] **Step 1: Extend IJobRunner Protocol**

```python
def start_integrity_check(self, request: IntegrityCheckRequest) -> int: ...
def start_utf8_convert(self, request: Utf8ConvertRequest) -> int: ...
```

- [ ] **Step 2: QtJobManager handlers**

- `start_integrity_check`: build worker, `_job_types[job_id] = JobType.INTEGRITY`, progress/completed/failed events.
- `start_utf8_convert`: `JobType.ENCODING`, same pattern.
- `cancel`: call `worker.cancel()` for both worker types.

- [ ] **Step 3: Smoke test with QTest (optional qapp fixture)**

```python
def test_start_integrity_check_returns_job_id(qtbot, job_manager_with_fixtures):
    job_id = job_manager.start_integrity_check(IntegrityCheckRequest())
    assert job_id >= 1
```

Use existing conftest `qapp` if present under `tests/gui`.

- [ ] **Step 4: Commit**

```bash
git commit -m "[gui] job runner integrity and utf8 convert jobs"
```

---

### Task 8: IntegrityViewModel + FinalizeSection

**Files:**
- Create: `src/gui/view_models/integrity_view_model.py`
- Modify: `src/gui/views/work/sections/finalize_section.py`
- Modify: `src/gui/view_models/work_pipeline_dto.py`
- Test: `tests/gui/view_models/test_integrity_view_model.py`

- [ ] **Step 1: Extend FinalizeSubstate**

```python
FinalizeSubstate = Literal[
    "idle", "applying", "apply_done",
    "integrity_running", "integrity_done",
    "utf8_auto_running", "utf8_auto_done", "utf8_auto_skipped",
    "finalize_done", "apply_failed",
]
```

- [ ] **Step 2: IntegrityViewModel**

Signals:
- `finalize_flow_completed = Signal(int, int)`  # issue_count, converted_count
- `integrity_finished = Signal(int)`
- `status_message = Signal(str)`

Methods:
- `start_auto_finalize_flow()` — integrity job → on complete compute issue_count (WARN+ERROR files) → utf8 `auto_eligible` job → emit completed.
- `start_integrity_only()` — no utf8.
- `start_manual_utf8_convert(parent, include_info: bool)` — QMessageBox + mode.

Subscribe to `job_manager` via `subscribe(JobEvent)` or dedicated worker signals wired in `MainWindow`.

- [ ] **Step 3: FinalizeSection**

- Constructor accepts `integrity_view_model: IntegrityViewModel`.
- Wire buttons: `인코딩 분석` → `start_integrity_only`; `UTF-8 변환` → manual dialog.
- `run_apply_and_integrity_auto(parent)`:
  - set applying → apply_done (stub OK for now)
  - call `view_model.start_auto_finalize_flow()`
  - `QEventLoop` wait on `finalize_flow_completed`; return True on success.
- Update `_status_label` per substate; hide indeterminate bar on done.

- [ ] **Step 4: Test view model with mock job manager**

- [ ] **Step 5: Commit**

```bash
git commit -m "[gui] integrity view model and finalize section wiring"
```

---

### Task 9: Composition root + MainWindow

**Files:**
- Modify: `src/app/main.py`
- Modify: `src/gui/views/main_window.py`
- Modify: `src/gui/views/work/work_tab.py` (pass VM into FinalizeSection)

- [ ] **Step 1: Wire in `app/main.py`**

```python
from infrastructure.encoding.charset_normalizer_detector import CharsetNormalizerDetector
from infrastructure.filesystem.file_content_reader import FileSystemContentReader
from application.use_cases.check_integrity import CheckIntegrityUseCase
from application.use_cases.convert_files_to_utf8 import ConvertFilesToUtf8UseCase

content_reader = FileSystemContentReader()
encoding_detector = CharsetNormalizerDetector()
check_integrity_uc = CheckIntegrityUseCase(
    app_state.file_data_store,
    content_reader,
    encoding_detector,
    log_sink=log_sink,
)
convert_utf8_uc = ConvertFilesToUtf8UseCase(
    app_state.file_data_store,
    content_reader,
    log_sink=log_sink,
)

job_manager = QtJobManager(
    ...,
    check_integrity_use_case=check_integrity_uc,
    convert_utf8_use_case=convert_utf8_uc,
)
```

Pass `IntegrityViewModel(job_manager, store)` into `MainWindow`.

- [ ] **Step 2: MainWindow**

- On `finalize_flow_completed`: `self._refresh_work_stats()` / existing `update_work_context_stats`.
- Ensure `WorkTab` / `FinalizeSection` receive VM.

- [ ] **Step 3: Commit**

```bash
git commit -m "[app] wire integrity use cases and view model"
```

---

### Task 10: Pipeline confirm copy + runner await

**Files:**
- Modify: `src/gui/views/work/pipeline_run_confirm_sheet.py`
- Modify: `src/gui/services/work_pipeline_runner.py` (only if finalize still returns too early)

- [ ] **Step 1: Add hint line in confirm sheet**

After destructive checkbox block, add `QLabel` with objectName `formHint`:

`무결성 검사 후, 백업(.novelguard.bak)을 남기고 변환 가능한 비 UTF-8 파일을 UTF-8로 자동 변환합니다.`

- [ ] **Step 2: Verify runner**

`WorkPipelineRunner._begin_finalize` already calls `run_apply_and_integrity_auto` — after Task 8 it should block until jobs finish. Manual test: run pipeline on small folder.

- [ ] **Step 3: Commit**

```bash
git commit -m "[gui] pipeline confirm integrity utf8 notice"
```

---

### Task 11: Full verification

- [ ] **Step 1: Run targeted tests**

```bash
pytest tests/unit/domain/services/test_integrity_check_service.py tests/application/use_cases/test_check_integrity.py tests/application/use_cases/test_convert_files_to_utf8.py tests/infrastructure/encoding/ tests/gui/view_models/test_integrity_view_model.py tests/gui/services/test_qt_job_manager_integrity.py -v
```

- [ ] **Step 2: Full gate**

```bash
python scripts/verify_phase_completion.py
```

Expected: all stages PASS.

- [ ] **Step 3: Commit any fixes**

```bash
git commit -m "[integrity] verification fixes"
```

---

## Spec coverage checklist (self-review)

| Spec requirement | Task |
|------------------|------|
| MVP rules A (0-byte, small, encoding, decode) | 1, 3 |
| Buttons C (analyze / convert) | 8 |
| Auto integrity after apply | 8, 9 |
| Auto UTF-8 when safe | 4, 8 |
| Job worker architecture | 6, 7 |
| `.novelguard.bak` | 4 |
| Pipeline confirm copy | 10 |
| Context bar stats refresh | 9 |
| Layer boundaries | 1–5, 9 |
| Acceptance tests | 1–4, 7–8, 11 |

## Manual smoke (post-implementation)

1. Scan folder with mixed encodings (small sample).
2. `[인코딩 분석]` → table 무결성 column populated.
3. `[전체 작업 실행]` → finalize shows N건 / M건 without UI freeze.
4. Confirm `.novelguard.bak` next to converted files.
5. `[UTF-8 변환]` manual with INFO checkbox on one non-utf8 file.

---

## Execution handoff

Plan complete and saved to `docs/superpowers/plans/2026-05-22-integrity-check.md`.

**Two execution options:**

1. **Subagent-Driven (recommended)** — fresh subagent per task, review between tasks  
2. **Inline Execution** — same session with `executing-plans`, batched checkpoints  

Which approach do you want?
