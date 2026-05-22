# Layer Seams and Composition Root Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Align NovelGuard layer dependencies with `docs/current_architecture.md`: hash ports in `domain/ports`, no dead `log_sink` in domain, `application` free of `app`/`sqlite3`, duplicate pipeline wired only from `app/`.

**Architecture:** Move `IHashService`/`ISimHashService` to `domain/ports`; delete `application/ports/hash_service.py`; strip unused `log_sink` from domain service constructors; add `application/config.py` and `application/exceptions.py`; inject `DuplicateDetectionPipeline` from `app/main.py` through `QtJobManager` into `DuplicateDetectionWorker`.

**Tech Stack:** Python 3.12+, src layout, pytest / ruff / mypy / black via `scripts/verify_phase_completion.py`.

**Spec:** [../specs/2026-05-22-layer-seams-and-composition-design.md](../specs/2026-05-22-layer-seams-and-composition-design.md)

---

## File map (create / modify / delete)

| Action | Path |
|--------|------|
| Create | `src/domain/ports/__init__.py`, `content_hash.py`, `sim_hash.py` |
| Delete | `src/application/ports/hash_service.py` |
| Modify | `src/domain/services/*.py` (6), `src/domain/services/__init__.py` |
| Modify | `src/infrastructure/hashing/hash_service_adapter.py` |
| Modify | `src/app/factories.py`, `scripts/run_duplicate_check_cli.py` |
| Create | `src/application/config.py`, `src/application/exceptions.py` |
| Modify | `src/application/use_cases/scan_folder.py` |
| Modify | `src/app/settings/constants.py`, `src/app/main.py` |
| Modify | `src/infrastructure/db/sqlite_index_repository.py` |
| Modify | `src/gui/services/qt_job_manager.py`, `src/gui/workers/duplicate_detection_worker.py` |
| Modify | `tests/gui/workers/test_duplicate_detection_worker.py` |
| Create | `tests/infrastructure/db/test_index_persistence_error.py` (if no existing coverage) |
| Modify | `docs/current_architecture.md` |

---

### Task 1: Domain hash ports

**Files:**
- Create: `src/domain/ports/__init__.py`, `src/domain/ports/content_hash.py`, `src/domain/ports/sim_hash.py`
- Delete: `src/application/ports/hash_service.py`
- Modify: `src/domain/services/exact_duplicate_detector.py`, `src/domain/services/near_duplicate_detector.py`, `src/domain/services/__init__.py`
- Modify: `src/infrastructure/hashing/hash_service_adapter.py`

- [ ] **Step 1: Add `content_hash.py`**

Create `src/domain/ports/content_hash.py` (copy `IHashService` from `application/ports/hash_service.py`):

```python
"""Content hash port (domain seam)."""

from pathlib import Path
from typing import Protocol

from domain.value_objects.detection_config import DetectionDefaults


class IHashService(Protocol):
    """해시 서비스 인터페이스 — Exact 중복 탐지용."""

    def calculate_hash(self, file_path: Path) -> str: ...
    def calculate_prefix_hash(
        self, file_path: Path, size: int = DetectionDefaults.SAMPLE_SIZE
    ) -> str: ...
    def calculate_suffix_hash(
        self, file_path: Path, size: int = DetectionDefaults.SAMPLE_SIZE
    ) -> str: ...
```

- [ ] **Step 2: Add `sim_hash.py`**

Create `src/domain/ports/sim_hash.py` with `ISimHashService` (same three methods as current `hash_service.py` lines 55–98).

- [ ] **Step 3: Barrel export**

Create `src/domain/ports/__init__.py`:

```python
from domain.ports.content_hash import IHashService
from domain.ports.sim_hash import ISimHashService

__all__ = ["IHashService", "ISimHashService"]
```

- [ ] **Step 4: Update domain detectors**

In `exact_duplicate_detector.py`, replace TYPE_CHECKING import:

```python
from domain.ports.content_hash import IHashService
```

Use runtime import (not only TYPE_CHECKING) because `__init__` annotates `hash_service: IHashService`.

In `near_duplicate_detector.py`:

```python
from domain.ports.sim_hash import ISimHashService
```

- [ ] **Step 5: Delete old port module**

Remove `src/application/ports/hash_service.py`.

- [ ] **Step 6: Adapter docstring only (optional)**

`hash_service_adapter.py` — add comment that it implements `domain.ports.content_hash.IHashService`; no import required for structural subtyping.

- [ ] **Step 7: Fix `domain/services/__init__.py` comment**

Remove reference to `application.ports.hash_service`.

- [ ] **Step 8: Verify no stale imports**

Run: `rg "application\.ports\.hash_service" f:/Python_Projects/NovelGuard`

Expected: no matches.

- [ ] **Step 9: Run domain-related tests**

Run: `pytest tests/unit/domain tests/application/use_cases/duplicate_detection -q --tb=short`

Expected: PASS (may fail until Task 2 if factories still pass `log_sink` — continue).

- [ ] **Step 10: Commit**

```bash
git add src/domain/ports src/domain/services/exact_duplicate_detector.py src/domain/services/near_duplicate_detector.py src/domain/services/__init__.py src/application/ports/hash_service.py
git commit -m "[domain] move hash ports to domain/ports"
```

---

### Task 2: Remove dead `log_sink` from domain services

**Files:**
- Modify: `src/domain/services/blocking_service.py`, `filename_parser.py`, `exact_duplicate_detector.py`, `containment_detector.py`, `near_duplicate_detector.py`, `keeper_score_service.py`
- Modify: `src/app/factories.py`, `scripts/run_duplicate_check_cli.py`

- [ ] **Step 1: Strip `log_sink` from each domain service**

For each file in the list above:

1. Remove `if TYPE_CHECKING: from application.ports.log_sink import ILogSink`
2. Remove `log_sink` parameter from `__init__`
3. Remove `self._log_sink = log_sink`
4. Update docstrings

Example `exact_duplicate_detector.py`:

```python
def __init__(self, hash_service: IHashService) -> None:
    self._hash_service = hash_service
```

`blocking_service.py`:

```python
def __init__(self, filename_parser: Optional[FilenameParser] = None) -> None:
    self._parser = filename_parser or FilenameParser()
```

- [ ] **Step 2: Update `app/factories.py`**

```python
filename_parser = FilenameParser()
blocking_service = BlockingService(filename_parser=filename_parser)
containment_detector = ContainmentDetector()
hash_service = HashServiceAdapter()
exact_detector = ExactDuplicateDetector(hash_service=hash_service)
```

- [ ] **Step 3: Update `scripts/run_duplicate_check_cli.py`**

Same constructor calls (no `log_sink=` on domain services).

- [ ] **Step 4: Grep domain layer**

Run: `rg "from application" src/domain`

Expected: no matches.

- [ ] **Step 5: Run tests**

Run: `pytest tests/unit/domain tests/application/use_cases/duplicate_detection tests/unit/test_filename_parser.py -q`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/domain/services src/app/factories.py scripts/run_duplicate_check_cli.py
git commit -m "[domain] remove unused log_sink from domain services"
```

---

### Task 3: Application config and `IndexPersistenceError`

**Files:**
- Create: `src/application/config.py`, `src/application/exceptions.py`
- Modify: `src/application/use_cases/scan_folder.py`, `src/app/settings/constants.py`
- Modify: `src/infrastructure/db/sqlite_index_repository.py`
- Create: `tests/infrastructure/db/test_index_persistence_error.py`

- [ ] **Step 1: Write failing test for wrapped SQLite error**

Create `tests/infrastructure/db/test_index_persistence_error.py`:

```python
"""IndexPersistenceError mapping tests."""

import sqlite3
from pathlib import Path
from unittest.mock import patch

import pytest

from application.dto.scan_request import ScanRequest
from application.exceptions import IndexPersistenceError
from infrastructure.db.sqlite_index_repository import SQLiteIndexRepository


def test_start_run_wraps_sqlite_error(tmp_path: Path) -> None:
    repo = SQLiteIndexRepository(db_path=tmp_path / "index.db")
    request = ScanRequest(root_folder=tmp_path)

    with patch.object(repo, "_connect", side_effect=sqlite3.OperationalError("disk I/O error")):
        with pytest.raises(IndexPersistenceError) as exc_info:
            repo.start_run(request)

    assert exc_info.value.__cause__ is not None
```

- [ ] **Step 2: Run test — expect FAIL**

Run: `pytest tests/infrastructure/db/test_index_persistence_error.py::test_start_run_wraps_sqlite_error -v`

Expected: FAIL (`IndexPersistenceError` or wrapping not implemented).

- [ ] **Step 3: Add exception type**

Create `src/application/exceptions.py`:

```python
"""Application-layer exceptions."""


class IndexPersistenceError(Exception):
    """Index repository persistence failed (DB layer)."""
```

- [ ] **Step 4: Add config module**

Create `src/application/config.py` — move the full `DEFAULT_TEXT_EXTENSIONS` list from `src/app/settings/constants.py` lines 185–224 (verbatim).

- [ ] **Step 5: Re-export from app settings**

In `src/app/settings/constants.py`, replace the inline list with:

```python
from application.config import DEFAULT_TEXT_EXTENSIONS  # noqa: F401 — re-export for GUI
```

Remove the duplicate list definition (keep `Constants` class and QSettings keys).

- [ ] **Step 6: Update `scan_folder.py`**

```python
from application.config import DEFAULT_TEXT_EXTENSIONS
from application.exceptions import IndexPersistenceError
```

Remove `import sqlite3` and `from app.settings.constants import ...`.

Replace every `except (OSError, sqlite3.Error, ValueError)` (and similar tuples including `sqlite3.Error`) with:

```python
except (OSError, IndexPersistenceError, ValueError)
```

Keep `TypeError` where present in `_finalize_index_run`.

- [ ] **Step 7: Wrap SQLite in repository**

In `sqlite_index_repository.py`, add:

```python
from application.exceptions import IndexPersistenceError
```

Add helper:

```python
def _translate_sqlite_errors(self) -> None:
    """Use as: with self._translate_sqlite_errors(): ..."""
    # Implement as context manager or inline try/except in each public method.
```

Wrap bodies of `start_run`, `upsert_files`, and `finalize_run`:

```python
try:
    ... existing body ...
except sqlite3.Error as e:
    raise IndexPersistenceError(str(e)) from e
```

- [ ] **Step 8: Run persistence test**

Run: `pytest tests/infrastructure/db/test_index_persistence_error.py -v`

Expected: PASS.

- [ ] **Step 9: Run integration scan tests**

Run: `pytest tests/integration/test_scan_with_index_repository.py -v`

Expected: PASS.

- [ ] **Step 10: Grep application layer**

Run: `rg "sqlite3|from app\." src/application`

Expected: no matches.

- [ ] **Step 11: Commit**

```bash
git add src/application/config.py src/application/exceptions.py src/application/use_cases/scan_folder.py src/app/settings/constants.py src/infrastructure/db/sqlite_index_repository.py tests/infrastructure/db/test_index_persistence_error.py
git commit -m "[application] config module and IndexPersistenceError seam"
```

---

### Task 4: Composition root — inject duplicate pipeline

**Files:**
- Modify: `src/app/main.py`, `src/gui/services/qt_job_manager.py`, `src/gui/workers/duplicate_detection_worker.py`
- Modify: `tests/gui/workers/test_duplicate_detection_worker.py`

- [ ] **Step 1: Update worker constructor (API change)**

In `duplicate_detection_worker.py`:

1. Remove `from app.factories import create_duplicate_detection_pipeline`
2. Remove `index_repository` and `file_data_store` from `__init__` (pipeline already holds them).
3. New signature:

```python
def __init__(
    self,
    request: DuplicateDetectionRequest,
    *,
    pipeline: DuplicateDetectionPipeline | None = None,
    log_sink: Optional[ILogSink] = None,
    parent: Optional[QObject] = None,
) -> None:
    super().__init__(parent)
    self._request = request
    self._pipeline = pipeline
    self._log_sink = log_sink
    self._cancelled = False
```

4. In `run()`, when `self._pipeline is None`, emit error `"Duplicate detection pipeline is required"` (same UX as today's missing index message).

- [ ] **Step 2: Update `QtJobManager`**

Add imports:

```python
from collections.abc import Callable
from application.use_cases.duplicate_detection.duplicate_detection_pipeline import (
    DuplicateDetectionPipeline,
)
```

Extend `__init__`:

```python
duplicate_pipeline_factory: Callable[[], DuplicateDetectionPipeline] | None = None,
```

Store as `self._duplicate_pipeline_factory`.

In `start_duplicate_detection`, before creating worker:

```python
pipeline = (
    self._duplicate_pipeline_factory()
    if self._duplicate_pipeline_factory
    else None
)
worker = DuplicateDetectionWorker(
    request,
    pipeline=pipeline,
    log_sink=self._log_sink,
    parent=self,
)
```

- [ ] **Step 3: Wire `app/main.py`**

After `app_state` and before `QtJobManager`:

```python
from app.factories import create_duplicate_detection_pipeline

duplicate_pipeline_factory = lambda: create_duplicate_detection_pipeline(
    index_repository=index_repo,
    file_data_store=app_state.file_data_store,
    log_sink=log_sink,
)

job_manager = QtJobManager(
    scanner,
    index_repository=index_repo,
    log_sink=log_sink,
    file_data_store=app_state.file_data_store,
    duplicate_pipeline_factory=duplicate_pipeline_factory,
)
```

- [ ] **Step 4: Rewrite worker tests**

Update `tests/gui/workers/test_duplicate_detection_worker.py`:

```python
from unittest.mock import Mock
from application.use_cases.duplicate_detection.duplicate_detection_pipeline import (
    DuplicateDetectionPipeline,
)

def test_worker_initialization():
    request = DuplicateDetectionRequest(run_id=1)
    pipeline = Mock(spec=DuplicateDetectionPipeline)
    log_sink = Mock(spec=ILogSink)
    worker = DuplicateDetectionWorker(request=request, pipeline=pipeline, log_sink=log_sink)
    assert worker._pipeline is pipeline

def test_worker_run_no_pipeline():
    request = DuplicateDetectionRequest(run_id=1)
    worker = DuplicateDetectionWorker(request=request, pipeline=None, log_sink=Mock(spec=ILogSink))
    ...
    assert "pipeline is required" in error_emitted[0].lower()
```

Adjust `test_worker_run_pipeline_error` to inject mock pipeline directly (no `index_repository`).

- [ ] **Step 5: Grep GUI for factories**

Run: `rg "app\.factories" src/gui`

Expected: no matches.

- [ ] **Step 6: Run GUI worker tests**

Run: `pytest tests/gui/workers/test_duplicate_detection_worker.py -v`

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add src/app/main.py src/gui/services/qt_job_manager.py src/gui/workers/duplicate_detection_worker.py tests/gui/workers/test_duplicate_detection_worker.py
git commit -m "[app] inject duplicate pipeline from composition root"
```

---

### Task 5: Documentation and full verification

**Files:**
- Modify: `docs/current_architecture.md`

- [ ] **Step 1: Update architecture doc**

Under **Composition root**, add bullets:

- Hash protocols: `src/domain/ports/` (`IHashService`, `ISimHashService`).
- Duplicate pipeline: built in `app/factories.py`, factory passed from `app/main.py` → `QtJobManager` → `DuplicateDetectionWorker`.
- Scan default extensions: `application/config.py` (`DEFAULT_TEXT_EXTENSIONS`).

- [ ] **Step 2: Success criteria grep**

```bash
rg "from application" src/domain
rg "from app\." src/application
rg "sqlite3" src/application
rg "app\.factories" src/gui
```

All must return no matches.

- [ ] **Step 3: Full verification gate**

Run: `python scripts/verify_phase_completion.py`

Expected: exit code 0 (pytest → ruff → mypy → black).

- [ ] **Step 4: Commit**

```bash
git add docs/current_architecture.md
git commit -m "[docs] document domain ports and pipeline injection"
```

---

## Spec coverage checklist (self-review)

| Spec requirement | Task |
|------------------|------|
| `domain/ports` hash move | Task 1 |
| Delete `application/ports/hash_service.py` | Task 1 |
| Remove domain `log_sink` | Task 2 |
| `application/config.py` | Task 3 |
| `IndexPersistenceError` + sqlite wrap | Task 3 |
| `scan_folder` no app/sqlite3 | Task 3 |
| `app.settings` re-export | Task 3 |
| Pipeline injection main → QtJobManager → worker | Task 4 |
| `docs/current_architecture.md` | Task 5 |
| `verify_phase_completion.py` | Task 5 |
| Non-goals (Constants move, FileDataStore, CONTEXT, node_modules) | Not in plan ✓ |

**Placeholder scan:** None.

---

**Plan complete and saved to `docs/superpowers/plans/2026-05-22-layer-seams-and-composition.md`.**

**Execution options:**

1. **Subagent-Driven (recommended)** — fresh subagent per task, review between tasks  
2. **Inline Execution** — run tasks in this session with `executing-plans`, checkpoints after each task  

Which approach do you want?
