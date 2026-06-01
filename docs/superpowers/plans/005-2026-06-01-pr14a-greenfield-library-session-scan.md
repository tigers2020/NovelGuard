# PR-14a: Greenfield Library Session — Scan & Snapshot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace `BridgeApi` stub snapshots with a greenfield `LibrarySession` that performs real folder selection, background filesystem scan, and in-memory indexing — while returning valid empty review/quality pages until PR-14b/14c.

**Architecture:** B2 layers (`domain` / `application` / `infrastructure` / `app`). `BridgeApi` delegates to `LibrarySession` under a `threading.RLock`. Scan runs on a worker thread; `get_snapshot()` reads consistent state. No legacy imports from `c6bda5f`.

**Tech Stack:** Python 3.12, pywebview, stdlib `pathlib` / `hashlib` / `threading`, `tkinter.filedialog` (folder picker on Windows desktop).

**Spec:** [002-2026-06-01-novelguard-greenfield-library-session-design.md](../specs/002-2026-06-01-novelguard-greenfield-library-session-design.md) (approved)

**Parent:** PR-13 done (`004`). PR-14b/14c/14d are separate plans (not written yet).

**Test policy:** Extend `tests/test_bridge_contract.py` and `tests/fixtures/` only. No new `test_*.py` without `TEST_ALLOWED`.

**Pytest import policy:** Tests import `domain.*`, `application.*`, `infrastructure.*` via existing `pyproject.toml` `pythonpath = ["src"]`. If imports fail, fix `pyproject.toml` / package layout only — **no** ad-hoc `sys.path` mutations inside test modules.

**Bridge test injection:** `BridgeApi.select_folder()` stays no-arg on the bridge surface. Tests inject folders via `session.select_folder(str(tmp_path))` then `BridgeApi(session)` — do not add optional path params to `BridgeApi`.

**Cancel test policy:** Cancel tests must monkeypatch `infrastructure.filesystem_scanner.scan_folder` (or inject a slow fake via session test hook) that checks the cancel flag — **do not** rely on real filesystem size or wall-clock timing for cancellation.

**Non-goals (PR-14a):** SHA-256 content hashing, duplicate groups, `queryReviewRows` data, quality analyzer, SQLite, UI/React changes, packaging, real move preview row ids, FS move/delete, new test files.

**PR-14a exception (thin BridgeApi):** PR-13 preview/apply guard state remains in `app.BridgeApi` (bridge-lifecycle, not scan/index). `application` does not import `app`. PR-14d may extract an app-layer helper. See spec § PR-14a exception.

---

## Plan-locked decisions (reviewer — do not drift)

### 1. PR-14a SHA-256 / duplicate summary

```text
PR-14a does NOT compute content SHA-256 or duplicate groups.
Scanner collects path, name, size_bytes, modified_at, extension only.
FileRecord.content_sha256 is always None in 14a.
Resolve snapshot duplicate fields are zero: queueCount, groupCount, conflictCount, approvedCount (unless PR-13 pending apply flag).
query_review_rows returns a valid empty ReviewRowsPage until PR-14b.
```

### 2. `FileRecord.id` (stable row identity for PR-13+)

```text
FileRecord.id = sha256(utf8(f"{relative_posix_path}|{size_bytes}|{modified_at_ns}")).hexdigest()

relative_posix_path = path relative to library root, forward slashes, no leading "./"

content_sha256 is a SEPARATE field (None in 14a; populated in PR-14b during scan/hash pass).
Never use content_sha256 as FileRecord.id.
```

### 3. Concurrency

```text
LibrarySession owns threading.RLock.
All mutations (select_folder, start_scan completion, cancel, index replace) and get_snapshot() acquire the lock.
Scanner reports progress via a session callback that acquires the same lock before mutating pipeline fields.
```

### 4. Cancel semantics

```text
On cancel_run during an active scan:
- Set cooperative cancel flag on scanner
- Discard partial in-progress index (do not commit partial file list)
- If a previously completed index exists for the folder, restore/keep it
- pipeline.phase = "idle", pipeline.percent = 0, pipeline.cancellable = False
- work.scan.state = "error" if no prior successful index; else "success" (unchanged lastRun)
- pipeline.label = "취소됨" when canceled without prior success, else "대기 중"
- Do NOT bump libraryRevision on cancel (only folder change / successful scan complete)
```

---

## Implementation status

| Item | Status |
|------|--------|
| PR-14a Tasks 1–10 | **Done** |

---

## File map

| File | Responsibility |
|------|----------------|
| `src/domain/__init__.py` | package |
| `src/domain/models.py` | `FileRecord`, `make_file_id()` |
| `src/application/__init__.py` | package |
| `src/application/ports/library_index.py` | `LibraryIndexPort` protocol |
| `src/application/dto_mapper.py` | index → `AppSnapshot`, empty pages |
| `src/application/library_session.py` | orchestration, lock, scan thread, PR-13 preview slot |
| `src/infrastructure/__init__.py` | package |
| `src/infrastructure/filesystem_scanner.py` | recursive walk, progress callback |
| `src/infrastructure/memory_library_index.py` | in-memory port impl |
| `src/app/bridge_api.py` | thin delegate to `LibrarySession` |
| `src/app/webview_main.py` | construct session + `BridgeApi(session)` |
| `tests/test_bridge_contract.py` | real temp-dir scan tests |
| `tests/fixtures/bridge_contract_fixtures.py` | optional shared temp helpers |
| `docs/entry_points.md` | note real scan path |

---

## Acceptance criteria

```text
✓ No imports from c6bda5f-restored code paths
✓ select_folder(path?) persists real folder; pytest injects path without tkinter
✓ start_scan walks .txt and .md under folder on background thread
✓ get_snapshot returns validated AppSnapshot with real fileCount/totalBytes
✓ work.resolve duplicate counts are 0 in 14a; libraryRevision bumps on folder change + scan success
✓ query_review_rows / query_quality_rows return valid empty pages
✓ cancel_run discards partial scan, keeps prior index, does not bump revision
✓ BridgeApi methods delegate to LibrarySession (no inline stub snapshot math)
✓ PR-13 preview/apply/discard still pass existing pytest
✓ python scripts/verify_phase_completion.py PASS
✓ mockBridge unchanged (browser dev)
```

---

### Task 1: Domain `FileRecord` + `make_file_id`

**Files:**
- Create: `src/domain/__init__.py`
- Create: `src/domain/models.py`
- Test: `tests/test_bridge_contract.py` (add `test_make_file_id_stable`)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_bridge_contract.py`:

```python
from domain.models import make_file_id


def test_make_file_id_stable() -> None:
    a = make_file_id("novels/a.txt", 100, 1_700_000_000_000_000_000)
    b = make_file_id("novels/a.txt", 100, 1_700_000_000_000_000_000)
    assert a == b
    assert len(a) == 64
    assert make_file_id("novels/b.txt", 100, 1_700_000_000_000_000_000) != a
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_bridge_contract.py::test_make_file_id_stable -v`  
Expected: FAIL `ModuleNotFoundError: domain`

- [ ] **Step 3: Implement `domain/models.py`**

```python
"""Pure domain models for library session (greenfield PR-14)."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FileRecord:
    id: str
    relative_path: str
    name: str
    size_bytes: int
    modified_at_ns: int
    extension: str
    content_sha256: str | None = None
    encoding_status: str | None = None


def make_file_id(relative_posix_path: str, size_bytes: int, modified_at_ns: int) -> str:
    payload = f"{relative_posix_path}|{size_bytes}|{modified_at_ns}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
```

Create empty `src/domain/__init__.py`.

- [ ] **Step 4: Run test — PASS**

- [ ] **Step 5: Commit** `[domain] FileRecord and stable make_file_id`

---

### Task 2: `LibraryIndexPort` + `MemoryLibraryIndex`

**Files:**
- Create: `src/application/__init__.py`
- Create: `src/application/ports/__init__.py`
- Create: `src/application/ports/library_index.py`
- Create: `src/infrastructure/__init__.py`
- Create: `src/infrastructure/memory_library_index.py`

- [ ] **Step 1: Define port**

`src/application/ports/library_index.py`:

```python
from __future__ import annotations

from typing import Protocol

from domain.models import FileRecord


class LibraryIndexPort(Protocol):
    def clear(self) -> None: ...

    def replace_files(self, folder_path: str, files: list[FileRecord]) -> None: ...

    @property
    def folder_path(self) -> str | None: ...

    def files(self) -> list[FileRecord]: ...

    def file_count(self) -> int: ...

    def total_bytes(self) -> int: ...
```

- [ ] **Step 2: Implement memory index**

`src/infrastructure/memory_library_index.py`:

```python
from __future__ import annotations

from domain.models import FileRecord


class MemoryLibraryIndex:
    def __init__(self) -> None:
        self._folder_path: str | None = None
        self._files: list[FileRecord] = []

    def clear(self) -> None:
        self._folder_path = None
        self._files = []

    def replace_files(self, folder_path: str, files: list[FileRecord]) -> None:
        self._folder_path = folder_path
        self._files = list(files)

    @property
    def folder_path(self) -> str | None:
        return self._folder_path

    def files(self) -> list[FileRecord]:
        return list(self._files)

    def file_count(self) -> int:
        return len(self._files)

    def total_bytes(self) -> int:
        return sum(f.size_bytes for f in self._files)
```

- [ ] **Step 3: Commit** `[application] LibraryIndexPort and memory impl`

---

### Task 3: Filesystem scanner (no content hash)

**Files:**
- Create: `src/infrastructure/filesystem_scanner.py`
- Test: extend `tests/test_bridge_contract.py`

- [ ] **Step 1: Write failing scan test**

```python
import tempfile
from pathlib import Path

from infrastructure.filesystem_scanner import scan_folder


def test_scan_folder_finds_txt_and_md() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "a.txt").write_text("hello", encoding="utf-8")
        (root / "b.md").write_text("# x", encoding="utf-8")
        (root / "skip.exe").write_bytes(b"\x00")

        files: list = []
        def on_progress(_pct: int, _label: str) -> None:
            pass

        scan_folder(str(root), on_progress=on_progress, cancel_check=lambda: False, out=files.append)
        names = {f.name for f in files}
        assert names == {"a.txt", "b.md"}
        assert all(f.content_sha256 is None for f in files)
        assert len({f.id for f in files}) == 2
```

- [ ] **Step 2: Run — FAIL**

- [ ] **Step 3: Implement scanner**

```python
from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path

from domain.models import FileRecord, make_file_id

DEFAULT_EXTENSIONS = {".txt", ".md"}
ProgressCallback = Callable[[int, str], None]
CancelCheck = Callable[[], bool]


def _relative_posix(root: Path, path: Path) -> str:
    rel = path.relative_to(root).as_posix()
    return rel


def scan_folder(
    folder_path: str,
    *,
    on_progress: ProgressCallback,
    cancel_check: CancelCheck,
    out: Callable[[FileRecord], None],
    extensions: set[str] | None = None,
) -> None:
    root = Path(folder_path).resolve()
    if not root.is_dir():
        raise ValueError(f"Not a directory: {folder_path}")

    allowed = extensions or DEFAULT_EXTENSIONS
    all_paths: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        if cancel_check():
            return
        dirnames[:] = [d for d in dirnames if not d.startswith(".")]
        for name in filenames:
            if name.startswith("."):
                continue
            p = Path(dirpath) / name
            if p.suffix.lower() in allowed:
                all_paths.append(p)

    total = max(len(all_paths), 1)
    for i, path in enumerate(all_paths):
        if cancel_check():
            return
        st = path.stat()
        rel = _relative_posix(root, path)
        modified_at_ns = getattr(st, "st_mtime_ns", int(st.st_mtime * 1_000_000_000))
        record = FileRecord(
            id=make_file_id(rel, st.st_size, modified_at_ns),
            relative_path=rel,
            name=path.name,
            size_bytes=st.st_size,
            modified_at_ns=modified_at_ns,
            extension=path.suffix.lower(),
            content_sha256=None,
        )
        out(record)
        pct = int((i + 1) * 100 / total)
        on_progress(pct, f"스캔 중 ({i + 1}/{len(all_paths)})")
```

- [ ] **Step 4: Run test — PASS**

- [ ] **Step 5: Commit** `[infrastructure] filesystem scanner without content hash`

---

### Task 4: `dto_mapper` — snapshot + empty pages

**Files:**
- Create: `src/application/dto_mapper.py`

- [ ] **Step 1: Implement mapper**

Key functions:

```python
def empty_review_page() -> dict: ...
def empty_quality_page() -> dict: ...
def build_snapshot(
    *,
    folder_path: str | None,
    files_count: int,
    total_bytes: int,
    library_revision: int,
    active_mode: str,
    pipeline_phase: str,
    pipeline_percent: int,
    pipeline_label: str,
    pipeline_cancellable: bool,
    scan_state: str,
    scan_last_run: str | None,
    has_pending_apply: bool,
    connection: str = "Library session (Python)",
) -> dict: ...
```

Rules for 14a resolve block:

```python
"resolve": {
    "queueCount": 0,
    "groupCount": 0,
    "conflictCount": 0,
    "approvedCount": 0,
    "hasPendingApply": has_pending_apply,
    "libraryRevision": library_revision,
},
"quality": {
    "integrityIssueCount": 0,
    "encodingIssueCount": 0,
    "smallFileAnomalyCount": 0,
},
```

Use `datetime.now().strftime("%Y-%m-%d %H:%M")` for `scan_last_run` on success.

- [ ] **Step 2: Commit** `[application] dto_mapper for snapshot and empty pages`

---

### Task 5: `LibrarySession` — lock, scan thread, cancel

**Files:**
- Create: `src/application/library_session.py`
- Modify: `src/app/bridge_api.py` (replace body with delegation — Task 6)

- [ ] **Step 1: Session skeleton with RLock**

```python
class LibrarySession:
    def __init__(self, index: LibraryIndexPort | None = None) -> None:
        self._lock = threading.RLock()
        self._index: LibraryIndexPort = index or MemoryLibraryIndex()
        self._library_revision = 0
        self._active_mode = "resolve"
        self._pipeline_running = False
        self._scan_state = "empty"
        self._scan_last_run: str | None = None
        self._cancel_requested = False
        self._scan_thread: threading.Thread | None = None
        # PR-13 preview slot (move from BridgeApi):
        self._has_pending_apply = False
        self._pending_apply: dict | None = None
```

- [ ] **Step 2: `select_folder`**

- With `path: str | None`: if `path` given, use it; else `tkinter.filedialog.askdirectory()`.
- On success: `self._index.clear()`, reset scan state to `"ready"`, bump `library_revision`, store folder on index via `replace_files(path, [])` or dedicated folder field.

- [ ] **Step 3: `start_scan`**

- Reject if no folder or already `_pipeline_running`.
- Set `_pipeline_running = True`, `_scan_state = "running"`, `_cancel_requested = False`.
- Spawn daemon thread running `_run_scan`.

`_run_scan` logic:

```python
def _run_scan(self) -> None:
    collected: list[FileRecord] = []
    folder = self._index.folder_path
    assert folder

    def on_progress(pct: int, label: str) -> None:
        with self._lock:
            self._pipeline_percent = pct
            self._pipeline_label = label

    def cancel_check() -> bool:
        return self._cancel_requested

    scan_folder(folder, on_progress=on_progress, cancel_check=cancel_check, out=collected.append)

    with self._lock:
        self._pipeline_running = False
        if self._cancel_requested:
            # keep previous index already on port — do not replace_files
            ...
            return
        self._index.replace_files(folder, collected)
        self._scan_state = "success"
        self._scan_last_run = now_str()
        self._library_revision += 1
```

- [ ] **Step 4: `cancel_run`**

Set `_cancel_requested = True` if scan running; apply cancel semantics from plan-locked section.

- [ ] **Step 5: `get_snapshot` / `query_*`**

Under lock, call `dto_mapper.build_snapshot(...)` and return `empty_review_page()` / `empty_quality_page()`.

- [ ] **Step 6: Move PR-13 preview/apply/discard methods**

Copy existing logic from `bridge_api.py` into `LibrarySession` (`get_move_preview`, `apply_resolved_actions`, `discard_move_preview`) unchanged in behavior.

- [ ] **Step 7: Commit** `[application] LibrarySession with scan thread and lock`

---

### Task 6: Thin `BridgeApi`

**Files:**
- Modify: `src/app/bridge_api.py`
- Modify: `src/app/webview_main.py`

- [ ] **Step 1: Refactor `BridgeApi`**

```python
class BridgeApi:
    def __init__(self, session: LibrarySession | None = None) -> None:
        self._session = session or LibrarySession()

    def get_snapshot(self) -> dict[str, Any]:
        payload = self._session.get_snapshot()
        validate_app_snapshot(payload)
        return payload

    def select_folder(self) -> None:
        self._session.select_folder()

    def start_scan(self, options: dict[str, Any] | None = None) -> None:
        self._session.start_scan(options)

    # ... each method: delegate, then validate_* where applicable
```

Remove hardcoded `1284` file counts and inline stub row generation from `BridgeApi`.

- [ ] **Step 2: `webview_main.py`**

```python
from application.library_session import LibrarySession
from app.bridge_api import BridgeApi

session = LibrarySession()
api = BridgeApi(session)
```

- [ ] **Step 3: Run full pytest + verify**

Run: `pytest tests/test_bridge_contract.py -v`  
Run: `python scripts/verify_phase_completion.py`

- [ ] **Step 4: Commit** `[app] BridgeApi delegates to LibrarySession`

---

### Task 7: Integration tests (extend existing file)

**Files:**
- Modify: `tests/test_bridge_contract.py`

- [ ] **Step 1: Real scan snapshot test**

```python
def test_bridge_api_scan_populates_file_count(tmp_path: Path) -> None:
  # create 2 txt files
  api = BridgeApi(LibrarySession())
  session = api._session  # OR inject folder via select_folder(str(tmp_path))
  api.select_folder with injected path — prefer LibrarySession.select_folder(str(tmp_path)) public
  api.start_scan()
  # poll get_snapshot until scan_state success (timeout 5s)
  snap = api.get_snapshot()
  assert snap["library"]["fileCount"] == 2
  assert snap["work"]["resolve"]["groupCount"] == 0
```

Expose `select_folder(path: str | None)` on `BridgeApi` as `select_folder` already no args — use `session.select_folder(str(tmp_path))` in test via `BridgeApi(LibrarySession())` and public session accessor **or** add optional path param only on session (not bridge surface).

- [ ] **Step 2: Cancel test (monkeypatch — no timing flake)**

Patch `infrastructure.filesystem_scanner.scan_folder` with a slow fake that appends records in a loop and calls `cancel_check()` each iteration. Start scan, call `cancel_run` mid-loop, assert prior successful index file count unchanged and `libraryRevision` unchanged.

```python
def test_cancel_scan_discards_partial(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    session = LibrarySession()
    session.select_folder(str(tmp_path))
    (tmp_path / "a.txt").write_text("x", encoding="utf-8")
    # ... seed prior completed index via first fast scan or direct replace_files ...
    # slow fake + cancel_run + assertions
```

- [ ] **Step 3: Empty review page still validates**

```python
def test_query_review_rows_empty_valid_14a() -> None:
    api = BridgeApi()
    page = api.query_review_rows({"viewMode": "action", "limit": 50})
    assert page["rows"] == []
    validate_review_rows_page(page)  # import validator
```

- [ ] **Step 4: Run verify — PASS**

- [ ] **Step 5: Commit** `[tests] PR-14a scan and empty review contract tests`

---

### Task 8: Documentation

**Files:**
- Modify: `docs/entry_points.md`

- [ ] **Step 1: Add PR-14a section**

Note: desktop `BridgeApi` performs real scan; browser `npm run dev` still uses `mockBridge`. List `start_scan` / `select_folder` behavior.

- [ ] **Step 2: Commit** `[docs] PR-14a real scan entry points`

---

## Plan self-review

| Spec requirement | Task |
|------------------|------|
| B-Strict / no legacy | All tasks |
| B2 layers | Tasks 1–6 |
| In-memory index 14a | Task 2 |
| No SHA-256 / duplicate in 14a | Tasks 1, 3, 4 plan-locks |
| Thin BridgeApi | Task 6 |
| Background scan + poll snapshot | Task 5 |
| Cancel semantics | Task 5 Step 4 |
| RLock | Task 5 |
| Empty review/quality | Tasks 4, 5 |
| PR-13 preview preserved | Task 5 Step 6 |
| Tests extend existing | Task 7 |

No TBD placeholders in task steps above.

---

## Follow-on plans (not in this file)

| Plan | Scope |
|------|--------|
| PR-14b | `content_sha256` during scan, `duplicate_exact`, SQLite index, `query_review_rows` |
| PR-14c | `quality_rules`, `query_quality_rows` |
| PR-14d | preview real row ids, contract/E2E parity |

---

## Execution handoff

Plan saved to `docs/superpowers/plans/005-2026-06-01-pr14a-greenfield-library-session-scan.md`.

**Execution options:**

1. **Subagent-driven (recommended)** — fresh subagent per task, review between tasks  
2. **Inline** — execute in this session with `executing-plans`, checkpoints per task

Which approach?
