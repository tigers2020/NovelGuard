# PR-46: Streaming Scan Pipeline and Phased UI — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix 7k+ scan freeze at 100% / 0 files in ShellFileDock by streaming probe→persist batches, separating `indexReady`, `scan.state=success`, and `deepAnalysisComplete`, and aligning `pipeline.phase` + Korean labels with [spec 028](../specs/028-2026-06-03-infra-scan-streaming-phases-design.md).

**Architecture:** Keep `LibrarySession` as orchestrator. Probe in batches (existing `scan_content_probe` pool), persist via new `LibraryIndexPort.append_files_batch`, bump `libraryRevision` per commit. After all batches, `exact_index` reads `index.files()` (not an in-memory `collected[]`). Near/relation post-scan worker also uses `index.files()`. Web maps legacy `phase="scan"` → `probe` only.

**Tech Stack:** Python 3.12 (`threading`, existing SQLite WAL), React + TypeScript (`web/src/types/snapshot.ts`, Vitest).

**Spec:** [028 streaming scan phases](../specs/028-2026-06-03-infra-scan-streaming-phases-design.md) (**approved** 2026-06-03)

**Plan status:** Done (2026-06-03) — core streaming persist, signals, and hotfix busy boundary landed on `main` via PR #23.

**Test policy:** Extend `tests/test_bridge_contract.py`, `web/src/bridge/bridgeParity.test.ts` only. No new `test_*.py` without user approval.

**Non-goals:** Work hub IA change; incremental/mtime scan; new `scan_stream.py` unless `library_session._run_scan` exceeds ~200 lines after refactor (prefer `application/scan_stream.py` only if split is needed).

---

## Plan-locked decisions

### 1. Persist strategy (`append_files_batch`)

```text
On scan start (before first batch):
  SqliteLibraryIndex.append_files_batch(folder, batch, *, reset=True)
    → DELETE FROM files WHERE folder_path = ? once, then INSERT batch + COMMIT
  Subsequent batches: reset=False (INSERT only + COMMIT)

MemoryLibraryIndex: reset=True replaces _files with batch; reset=False extends _files.

library_session bumps library_revision after every successful batch commit.
First batch sets index_ready=True and scan.indexReady in snapshot.
```

### 2. Three signals (do not conflate)

```text
indexReady=true          → first persist batch committed, library.fileCount > 0
work.scan.state=success  → finalize_index (exact_index) finished
deepAnalysisComplete=true → post_scan worker finished or skipped (library < 3000 files)
```

### 3. `pipeline.phase` enum (Python emits only)

```text
idle | probe | persist | exact_index | analyze
Never emit "scan" from Python after this PR.
Web: normalizePhase("scan") === "probe" for labels + deriveScanSectionState compat only.
```

### 4. Probe labels (LOCK-SCAN-5)

```text
probe:   pipeline.label = "파일 확인 중… (n/N)"
persist: pipeline.label = "인덱스 저장 중… (n/N)"  — never "스캔 중" at 100%
exact_index: "정확 중복 인덱스 생성 중…"
analyze: "중복·관계 분석 중… (백그라운드)"
```

### 5. RAM / `near_text_preview`

```text
FileRecord.near_text_preview is always None at scan time and never persisted.
scan_content_probe does not set near_text_preview on FileRecord.
near_text_reader reads head bytes from disk when analysis runs.
Remove _records_for_persistence() duplication path once streaming writes persist shape directly.
```

### 6. Background near/relation threshold

```text
SCAN_DEEP_ANALYSIS_BACKGROUND_THRESHOLD = 3000
If file_count >= 3000 after exact_index: start post_scan worker (non-blocking).
If file_count < 3000: run near+relation synchronously in worker thread (same as today) but still set deepAnalysisComplete when done.
scan.state=success is set BEFORE worker starts (after exact_index).
```

### 7. True streaming (Task 6 hard rule)

```text
Do NOT call a scan API that returns list[FileRecord] for the full library.
Do NOT accumulate collected: list[FileRecord] in library_session before persist.

Allowed: O(N) path-metadata list from collect_scan_path_entries (small structs only).
Forbidden: O(N) FileRecord (+ preview blobs) in memory before persist.

Implement record streaming via one of:
  1. scan_folder_stream(..., on_record=...) in filesystem_scanner.py
  2. enrich_scan_entries_with_content_probe(..., out=on_record) called from session without buffering all records
  3. iterator/generator yielding FileRecord one-by-one into probe_buffer (max SCAN_PERSIST_BATCH_SIZE)

probe_buffer may hold at most one persist batch of FileRecord; flush to append_files_batch then clear.
Any design that probes the full library into a list, then slices into batches for SQLite, FAILS this plan.
```

---

## File map

| File | Responsibility |
| ---- | ---------------- |
| `src/application/scan_pipeline_constants.py` | `SCAN_PERSIST_BATCH_SIZE`, threshold constants |
| `src/application/ports/library_index.py` | Add `append_files_batch` to protocol |
| `src/infrastructure/sqlite_library_index.py` | Batch insert + per-batch commit |
| `src/infrastructure/memory_library_index.py` | Batch append for tests |
| `src/infrastructure/scan_content_probe.py` | Probe labels; `out(record)` streaming (no full FileRecord list) |
| `src/infrastructure/filesystem_scanner.py` | `scan_folder_stream` or probe path wired to `on_record` only |
| `src/application/library_session.py` | Streaming `_run_scan`, phase flags, readiness fields |
| `src/application/dto_mapper.py` | `indexReady`, `deepAnalysisComplete` on `work.scan` |
| `src/app/bridge_contract.py` | Validate phase enum + scan booleans |
| `src/domain/models.py` | Docstring: `near_text_preview` scan-time only, never persisted |
| `tests/test_bridge_contract.py` | Mid-scan `fileCount`, phases, flags, no preview persist |
| `web/src/types/snapshot.ts` | `ScanSnapshot` fields + `PipelinePhase` union |
| `web/src/features/work/scanSectionState.ts` | `scan.state` driven; legacy `scan` phase shim |
| `web/src/features/work/pipelinePhase.ts` | **Create:** `normalizePipelinePhase`, label helper |
| `web/src/features/work/ScanWorkspace.tsx` | Dock CTA when `indexReady`; counts during persist |
| `web/src/components/layout/GlobalCommandBar.tsx` | Analyze vs scan progress |
| `web/src/bridge/mockBridge.ts` | Default flags on snapshot |
| `web/src/bridge/bridgeParity.test.ts` | Phase + flag tests |
| `web/src/contracts/fixtures.ts` | Fixture scan fields |

---

## Acceptance criteria (from spec §9)

```text
✓ 7k library: no "스캔 중 (N/N)" at 100% during persist
✓ After ~400 files: library.fileCount > 0, ShellFileDock rows
✓ indexReady after batch 1; scan.state=success only after exact_index
✓ pipeline.phase=analyze allowed while scan.state=success
✓ deepAnalysisComplete only after near/relation worker
✓ pytest tests/test_bridge_contract.py (scan-related) PASS
✓ npm run test -- src/bridge/bridgeParity.test.ts PASS
```

---

### Task 1: Scan pipeline constants

**Files:**
- Create: `src/application/scan_pipeline_constants.py`

- [ ] **Step 1: Add constants module**

```python
"""Thresholds for streaming scan pipeline (spec 028)."""

SCAN_PERSIST_BATCH_SIZE = 400
SCAN_DEEP_ANALYSIS_BACKGROUND_THRESHOLD = 3000
SCAN_PROGRESS_THROTTLE_FILES = 48
```

- [ ] **Step 2: Commit**

```bash
git add src/application/scan_pipeline_constants.py
git commit -m "chore: add scan pipeline constants for spec 028"
```

---

### Task 2: Stop attaching `near_text_preview` at scan time

**Files:**
- Modify: `src/infrastructure/scan_content_probe.py` (line ~88)
- Modify: `src/domain/models.py` (field docstring)
- Test: `tests/test_bridge_contract.py`

- [ ] **Step 1: Write failing test**

Append to `tests/test_bridge_contract.py`:

```python
def test_scan_does_not_persist_near_text_preview(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("hello world\n" * 100, encoding="utf-8")
    session = create_library_session(MemoryLibraryIndex())
    session.select_folder(str(tmp_path))
    api = create_bridge_api(session)
    api.start_scan()
    _scan_until_idle(api)
    for record in session.index.files():
        assert record.near_text_preview is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_bridge_contract.py::test_scan_does_not_persist_near_text_preview -v`  
Expected: FAIL if preview is set on records today.

- [ ] **Step 3: Set `near_text_preview=None` in probe record build**

In `src/infrastructure/scan_content_probe.py`, change the `FileRecord(...)` construction:

```python
                record = FileRecord(
                    id=make_file_id(
                        entry.relative_path, entry.size_bytes, entry.modified_at_ns
                    ),
                    relative_path=entry.relative_path,
                    name=entry.name,
                    size_bytes=entry.size_bytes,
                    modified_at_ns=entry.modified_at_ns,
                    extension=entry.extension,
                    content_sha256=probe.content_sha256,
                    encoding_status=probe.encoding_status,
                    near_text_preview=None,
                )
```

In `src/domain/models.py`, document the field:

```python
    near_text_preview: str | None = None  # in-memory only; never persisted (spec 028)
```

- [ ] **Step 4: Run test — PASS**

Run: `pytest tests/test_bridge_contract.py::test_scan_does_not_persist_near_text_preview -v`

- [ ] **Step 5: Commit**

```bash
git add src/infrastructure/scan_content_probe.py src/domain/models.py tests/test_bridge_contract.py
git commit -m "fix: do not attach near_text_preview during scan probe"
```

---

### Task 3: `append_files_batch` on index port

**Files:**
- Modify: `src/application/ports/library_index.py`
- Modify: `src/infrastructure/sqlite_library_index.py`
- Modify: `src/infrastructure/memory_library_index.py`
- Test: `tests/test_bridge_contract.py`

- [ ] **Step 1: Write failing test**

```python
def test_append_files_batch_increments_count_without_full_replace(tmp_path: Path) -> None:
    index = SqliteLibraryIndex(tmp_path / "lib.db")
    folder = str(tmp_path)
    index.activate_library_folder(folder)
    from domain.models import FileRecord, make_file_id

    def _row(name: str) -> FileRecord:
        rel = name
        return FileRecord(
            id=make_file_id(rel, 1, 1),
            relative_path=rel,
            name=name,
            size_bytes=1,
            modified_at_ns=1,
            extension=".txt",
        )

    index.append_files_batch(folder, [_row("a.txt")], reset=True)
    assert index.file_count() == 1
    index.append_files_batch(folder, [_row("b.txt")], reset=False)
    assert index.file_count() == 2
    names = {f.name for f in index.files()}
    assert names == {"a.txt", "b.txt"}
```

- [ ] **Step 1b: Empty `reset=True` clears prior rows (re-scan safety)**

```python
def test_append_files_batch_reset_empty_clears_folder(tmp_path: Path) -> None:
    index = SqliteLibraryIndex(tmp_path / "lib.db")
    folder = str(tmp_path)
    index.activate_library_folder(folder)
    from domain.models import FileRecord, make_file_id

    def _row(name: str) -> FileRecord:
        return FileRecord(
            id=make_file_id(name, 1, 1),
            relative_path=name,
            name=name,
            size_bytes=1,
            modified_at_ns=1,
            extension=".txt",
        )

    index.append_files_batch(folder, [_row("old.txt")], reset=True)
    assert index.file_count() == 1
    index.append_files_batch(folder, [], reset=True)
    assert index.file_count() == 0
```

- [ ] **Step 2: Run tests — FAIL** (`AttributeError: append_files_batch` or count not zero)

Run: `pytest tests/test_bridge_contract.py::test_append_files_batch_increments_count_without_full_replace -v`

- [ ] **Step 3: Extend protocol**

In `src/application/ports/library_index.py` after `replace_files`:

```python
    def append_files_batch(
        self,
        folder_path: str,
        files: list[FileRecord],
        *,
        reset: bool = False,
    ) -> None: ...
```

- [ ] **Step 4: Implement SQLite**

In `src/infrastructure/sqlite_library_index.py`, add method (reuse insert SQL from `replace_files`):

```python
    def append_files_batch(
        self,
        folder_path: str,
        files: list[FileRecord],
        *,
        reset: bool = False,
    ) -> None:
        if not files and not reset:
            return
        self._current_folder = folder_path
        insert_sql = """ ... same as replace_files INSERT ... """
        with self._connect() as conn:
            if reset:
                conn.execute("DELETE FROM files WHERE folder_path = ?", (folder_path,))
            conn.executemany(insert_sql, [tuple row for f in files])
            conn.commit()
```

- [ ] **Step 5: Implement memory index**

```python
    def append_files_batch(
        self,
        folder_path: str,
        files: list[FileRecord],
        *,
        reset: bool = False,
    ) -> None:
        self._current_folder = folder_path
        if reset:
            self._files = list(files)
        else:
            self._files.extend(files)
```

- [ ] **Step 6: Run test — PASS**

- [ ] **Step 7: Commit**

```bash
git add src/application/ports/library_index.py src/infrastructure/sqlite_library_index.py src/infrastructure/memory_library_index.py tests/test_bridge_contract.py
git commit -m "feat: add append_files_batch to library index port"
```

---

### Task 4: Probe progress labels (`파일 확인 중…`)

**Files:**
- Modify: `src/infrastructure/scan_content_probe.py`
- Modify: `src/infrastructure/filesystem_scanner.py` (collect label if needed)

- [ ] **Step 1: Update probe progress strings**

In `enrich_scan_entries_with_content_probe`, replace labels:

```python
on_progress(pct, f"파일 확인 중… ({completed}/{total})")
```

Empty case:

```python
on_progress(100, "파일 확인 중… (0/0)")
```

- [ ] **Step 2: Run existing scan tests**

Run: `pytest tests/test_bridge_contract.py -k "scan_folder or bridge_api_scan" -q`  
Expected: PASS (labels only).

- [ ] **Step 3: Commit**

```bash
git add src/infrastructure/scan_content_probe.py src/infrastructure/filesystem_scanner.py
git commit -m "ux: use probe-phase Korean labels during content scan"
```

---

### Task 5: Snapshot readiness fields (`dto_mapper` + session state)

**Files:**
- Modify: `src/application/library_session.py` (`__init__`, `get_snapshot`, `start_scan`)
- Modify: `src/application/dto_mapper.py`
- Modify: `src/app/bridge_contract.py`
- Test: `tests/test_bridge_contract.py`

- [ ] **Step 1: Write failing test**

```python
def test_snapshot_includes_index_ready_and_deep_analysis_flags(tmp_path: Path) -> None:
    (tmp_path / "one.txt").write_text("x", encoding="utf-8")
    api = create_bridge_api(create_library_session(MemoryLibraryIndex()))
    api.select_folder(str(tmp_path))
    snap = api.get_snapshot()
    assert "indexReady" in snap["work"]["scan"]
    assert "deepAnalysisComplete" in snap["work"]["scan"]
    assert snap["work"]["scan"]["indexReady"] is False
    assert snap["work"]["scan"]["deepAnalysisComplete"] is False
    api.start_scan()
    _scan_until_idle(api)
    snap = api.get_snapshot()
    assert snap["work"]["scan"]["indexReady"] is True
    assert snap["work"]["scan"]["deepAnalysisComplete"] is True
```

- [ ] **Step 2: Run test — FAIL**

- [ ] **Step 3: Add session fields**

In `LibrarySession.__init__`:

```python
        self._index_ready = False
        self._deep_analysis_complete = False
```

Reset in `start_scan` (with lock):

```python
            self._index_ready = False
            self._deep_analysis_complete = False
```

Set `_deep_analysis_complete = True` in post-scan worker `finally` block. Set `_index_ready = True` after first batch (Task 6).

- [ ] **Step 4: Extend `build_snapshot`**

Add parameters `index_ready: bool`, `deep_analysis_complete: bool` and emit:

```python
"scan": {
    "state": scan_state,
    "lastRun": scan_last_run,
    "indexReady": index_ready,
    "deepAnalysisComplete": deep_analysis_complete,
},
```

Wire from `get_snapshot()`.

- [ ] **Step 5: Validate in `validate_app_snapshot`**

```python
    scan = work.get("scan")
    if not isinstance(scan, dict):
        raise SnapshotContractError("work.scan must be a dict")
    for key in ("state", "lastRun", "indexReady", "deepAnalysisComplete"):
        if key not in scan:
            raise SnapshotContractError(f"work.scan missing {key}")
```

- [ ] **Step 6: Run test — PASS** (after Task 6 sets flags; may implement Task 5+6 together)

- [ ] **Step 7: Commit**

```bash
git add src/application/library_session.py src/application/dto_mapper.py src/app/bridge_contract.py tests/test_bridge_contract.py
git commit -m "feat: expose indexReady and deepAnalysisComplete on scan snapshot"
```

---

### Task 6: Streaming `_run_scan` + phase transitions

**Files:**
- Modify: `src/application/library_session.py`
- Modify: `src/infrastructure/filesystem_scanner.py` (add `scan_folder_stream` or equivalent)
- Modify: `src/infrastructure/scan_content_probe.py` (ensure `out(record)` per probe; no full `list[FileRecord]` return)
- Uses: `src/application/scan_pipeline_constants.py`
- Test: `tests/test_bridge_contract.py`

**Task 6 hard rule (plan gate):** Do not call a scan API that returns `list[FileRecord]` for the full library. Do not build `collected: list[FileRecord]` before persist. Use `on_record` / generator streaming only (see Plan-locked §7).

**Tests must be deterministic.** Do not rely only on timing/polling. Use `monkeypatch` on `SCAN_PERSIST_BATCH_SIZE` and `threading.Event` around `append_files_batch` to observe the first committed batch and the window before `exact_index`.

- [ ] **Step 1: Write failing tests — mid-scan count + indexReady before success**

```python
def test_scan_increments_file_count_after_first_persist_batch(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    import application.scan_pipeline_constants as scan_constants

    monkeypatch.setattr(scan_constants, "SCAN_PERSIST_BATCH_SIZE", 2)
    for i in range(5):
        (tmp_path / f"f{i}.txt").write_text("x\n", encoding="utf-8")

    session = create_library_session(SqliteLibraryIndex(tmp_path / "idx.db"))
    index = session.index
    original_append = index.append_files_batch
    first_batch_done = threading.Event()
    release_after_first = threading.Event()

    def wrapping_append(folder_path: str, files: list, *, reset: bool = False) -> None:
        original_append(folder_path, files, reset=reset)
        if not first_batch_done.is_set():
            first_batch_done.set()
            release_after_first.wait(timeout=5.0)

    monkeypatch.setattr(index, "append_files_batch", wrapping_append)
    session.select_folder(str(tmp_path))
    api = create_bridge_api(session)
    api.start_scan()

    assert first_batch_done.wait(timeout=5.0), "first persist batch never committed"
    snap = api.get_snapshot()
    assert 0 < snap["library"]["fileCount"] < 5
    release_after_first.set()
    _scan_until_idle(api)
    assert api.get_snapshot()["library"]["fileCount"] == 5


def test_index_ready_before_scan_success(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    import application.scan_pipeline_constants as scan_constants

    monkeypatch.setattr(scan_constants, "SCAN_PERSIST_BATCH_SIZE", 1)
    (tmp_path / "a.txt").write_text("a\n", encoding="utf-8")
    (tmp_path / "b.txt").write_text("b\n", encoding="utf-8")

    session = create_library_session(MemoryLibraryIndex())
    index = session.index
    original_append = index.append_files_batch
    first_batch_done = threading.Event()
    release_exact_index = threading.Event()

    def wrapping_append(folder_path: str, files: list, *, reset: bool = False) -> None:
        original_append(folder_path, files, reset=reset)
        if not first_batch_done.is_set():
            first_batch_done.set()
            release_exact_index.wait(timeout=5.0)

    monkeypatch.setattr(index, "append_files_batch", wrapping_append)
    api = create_bridge_api(session)
    api.select_folder(str(tmp_path))
    api.start_scan()

    assert first_batch_done.wait(timeout=5.0)
    snap = api.get_snapshot()
    assert snap["work"]["scan"]["indexReady"] is True
    assert snap["work"]["scan"]["state"] == "running"

    release_exact_index.set()
    _scan_until_idle(api)
    snap = api.get_snapshot()
    assert snap["work"]["scan"]["state"] == "success"
```

- [ ] **Step 2: Run tests — FAIL**

- [ ] **Step 3: Change `start_scan` initial phase**

Replace `self._pipeline_phase = "scan"` with:

```python
            self._pipeline_phase = "probe"
            self._pipeline_label = "파일 확인 중…"
```

- [ ] **Step 4: Add `scan_folder_stream` (or refactor probe entrypoint)**

In `src/infrastructure/filesystem_scanner.py`, add:

```python
def scan_folder_stream(
    folder_path: str,
    *,
    on_progress: ProgressCallback,
    cancel_check: CancelCheck,
    on_record: RecordSink,
    extensions: set[str] | None = None,
    include_hidden: bool = False,
) -> None:
    """Walk + content-probe; emit FileRecord via on_record only (no list[FileRecord] return)."""
    # collect_scan_path_entries → enrich_scan_entries_with_content_probe(..., out=on_record)
```

Wire `session_factory._scan_with_content_probe` to call `scan_folder_stream` instead of `scan_folder(..., out=collected.append)`.

- [ ] **Step 5: Refactor `_run_scan` to stream batches**

High-level structure (implement in `library_session.py`):

```python
    def _run_scan(self, folder: str) -> None:
        probe_buffer: list[FileRecord] = []
        first_batch = True

        def flush_batch() -> None:
            nonlocal probe_buffer, first_batch
            if not probe_buffer:
                return
            with self._lock:
                self._pipeline_phase = "persist"
            self._index.append_files_batch(folder, probe_buffer, reset=first_batch)
            first_batch = False
            probe_buffer = []
            with self._lock:
                if not self._index_ready:
                    self._index_ready = self._index.file_count() > 0
                self._library_revision += 1

        def on_record(record: FileRecord) -> None:
            probe_buffer.append(record)
            if len(probe_buffer) >= SCAN_PERSIST_BATCH_SIZE:
                flush_batch()

        scan_folder_stream(folder, on_progress=..., cancel_check=..., on_record=on_record, ...)
        flush_batch()  # remainder

        with self._lock:
            self._pipeline_phase = "exact_index"
            self._pipeline_label = "정확 중복 인덱스 생성 중…"
        files = self._index.files()
        # rebuild review/quality from files — NOT from collected[]
        # scan.state=success, then post_scan worker (index.files() inside worker)
```

Delete `collected: list[FileRecord]` and `_records_for_persistence()` from the scan path.

On progress during probe, set `pipeline_phase = "probe"` and map percent (existing 2–100 mapping from `filesystem_scanner`).

During persist callback, set label `인덱스 저장 중… (saved/total)` using `file_count()` from index.

- [ ] **Step 6: Post-scan worker**

Change `_start_post_scan_detection_thread(folder, collected, ...)` to `_start_post_scan_detection_thread(folder)` that loads `files = self._index.files()` inside worker.

Set `_pipeline_phase = "analyze"` and label `중복·관계 분석 중… (백그라운드)` when starting worker (after `scan.state=success`).

In `finally`: `_deep_analysis_complete = True`, `_pipeline_phase = "idle"`.

- [ ] **Step 7: Hydrate path**

On `_hydrate_from_persisted_index`, set `_index_ready = bool(files)`, `_deep_analysis_complete = True` (already indexed).

- [ ] **Step 8: Run tests**

Run: `pytest tests/test_bridge_contract.py -k "scan or append_files" -q`

Update `_scan_until_idle` and cancel test: wait for `phase in ("probe","persist","exact_index")` instead of `"scan"`:

```python
    while snap["pipeline"]["phase"] == "scan" and time.monotonic() < deadline:
```
→ change to `probe` or remove branch if cancel test patches slow scan during probe.

- [ ] **Step 9: Commit**

```bash
git add src/application/library_session.py src/infrastructure/filesystem_scanner.py src/infrastructure/scan_content_probe.py src/app/session_factory.py
git commit -m "feat: streaming scan persist with phased pipeline"
```

---

### Task 7: Validate `pipeline.phase` in bridge contract

**Files:**
- Modify: `src/app/bridge_contract.py`
- Test: `tests/test_bridge_contract.py`

- [ ] **Step 1: Add allowed phases + test**

```python
_PIPELINE_PHASES = frozenset(
    {"idle", "probe", "persist", "exact_index", "analyze", "finalize"}
)
# finalize = finalize subflow (existing). "scan" is NOT allowed on Python snapshots.

def validate_app_snapshot(snapshot: Any) -> None:
    ...
    pipeline = snapshot.get("pipeline")
    if not isinstance(pipeline, dict):
        raise SnapshotContractError("AppSnapshot.pipeline must be a dict")
    phase = pipeline.get("phase")
    if not isinstance(phase, str) or phase not in _PIPELINE_PHASES:
        raise SnapshotContractError(f"invalid pipeline.phase: {phase!r}")
```

Legacy `phase="scan"` compat is **web-only** (`normalizePipelinePhase("scan") === "probe"`). Python `validate_app_snapshot` must **reject** `"scan"`.

```python
def test_snapshot_rejects_unknown_pipeline_phase(tmp_path: Path) -> None:
    api = create_bridge_api(create_library_session(MemoryLibraryIndex()))
    api.select_folder(str(tmp_path))
    snap = api.get_snapshot()
    snap["pipeline"]["phase"] = "bogus"
    with pytest.raises(SnapshotContractError):
        validate_app_snapshot(snap)


def test_snapshot_rejects_legacy_scan_phase(tmp_path: Path) -> None:
    api = create_bridge_api(create_library_session(MemoryLibraryIndex()))
    api.select_folder(str(tmp_path))
    snap = api.get_snapshot()
    snap["pipeline"]["phase"] = "scan"
    with pytest.raises(SnapshotContractError):
        validate_app_snapshot(snap)
```

- [ ] **Step 2: Run tests — PASS**

- [ ] **Step 3: Commit**

```bash
git add src/app/bridge_contract.py tests/test_bridge_contract.py
git commit -m "chore: validate pipeline.phase in app snapshot contract"
```

---

### Task 8: Web types + `normalizePipelinePhase`

**Files:**
- Modify: `web/src/types/snapshot.ts`
- Create: `web/src/features/work/pipelinePhase.ts`
- Modify: `web/src/contracts/fixtures.ts`
- Test: `web/src/bridge/bridgeParity.test.ts`

- [ ] **Step 1: Extend types**

```typescript
export type PipelinePhase =
  | "idle"
  | "probe"
  | "persist"
  | "exact_index"
  | "analyze"
  | "finalize"; // finalize subflow — not part of scan enum but still emitted

export interface PipelineSnapshot {
  phase: PipelinePhase | "scan"; // "scan" = legacy compat input only
  percent: number;
  label: string;
  cancellable: boolean;
}

export interface ScanSnapshot {
  state: "empty" | "ready" | "running" | "success" | "error";
  lastRun: string | null;
  indexReady: boolean;
  deepAnalysisComplete: boolean;
}
```

- [ ] **Step 2: Create `pipelinePhase.ts`**

```typescript
/** Phases Python may emit; excludes legacy "scan" input. */
export type NormalizedPipelinePhase =
  | "idle"
  | "probe"
  | "persist"
  | "exact_index"
  | "analyze"
  | "finalize";

export function normalizePipelinePhase(phase: string): NormalizedPipelinePhase {
  if (phase === "scan") return "probe";
  return phase as NormalizedPipelinePhase;
}

export function pipelinePhaseLabel(
  phase: string,
  label: string,
  scan: { indexReady: boolean; state: string },
): string {
  const normalized = normalizePipelinePhase(phase);
  if (normalized === "probe" || normalized === "persist" || normalized === "exact_index" || normalized === "analyze") {
    return label;
  }
  if (scan.indexReady && scan.state === "running") {
    return "파일 목록 준비됨";
  }
  return label;
}
```

- [ ] **Step 3: Update fixtures + mockBridge defaults**

`fixtures.ts` scan object:

```typescript
scan: { state: "empty", lastRun: null, indexReady: false, deepAnalysisComplete: false },
```

- [ ] **Step 4: Commit**

```bash
git add web/src/types/snapshot.ts web/src/features/work/pipelinePhase.ts web/src/contracts/fixtures.ts
git commit -m "feat(web): snapshot types for scan readiness and pipeline phases"
```

---

### Task 9: `scanSectionState` + Vitest parity

**Files:**
- Modify: `web/src/features/work/scanSectionState.ts`
- Modify: `web/src/bridge/bridgeParity.test.ts`

- [ ] **Step 1: Update derive function**

```typescript
export function deriveScanSectionState(args: {
  folderPath: string | null;
  scan: ScanSnapshot;
  pipeline: PipelineSnapshot;
}): ScanSectionState {
  if (!args.folderPath?.trim()) {
    return "empty";
  }
  if (args.scan.state === "running") {
    return "running";
  }
  if (args.scan.state === "error") {
    return "error";
  }
  if (args.scan.state === "success") {
    return "success";
  }
  return "ready";
}
```

- [ ] **Step 2: Update tests**

Replace legacy test “running when pipeline phase is scan” with:

```typescript
  it("maps legacy pipeline phase scan to running only when scan.state is running", () => {
    expect(
      deriveScanSectionState({
        folderPath: "/tmp/lib",
        scan: { state: "running", lastRun: null, indexReady: false, deepAnalysisComplete: false },
        pipeline: { phase: "scan", percent: 10, label: "파일 확인 중…", cancellable: true },
      }),
    ).toBe("running");
    expect(
      deriveScanSectionState({
        folderPath: "/tmp/lib",
        scan: { state: "success", lastRun: "t", indexReady: true, deepAnalysisComplete: false },
        pipeline: { phase: "analyze", percent: 100, label: "중복·관계 분석 중…", cancellable: false },
      }),
    ).toBe("success");
  });
```

- [ ] **Step 3: Run Vitest**

Run: `cd web && npm run test -- src/bridge/bridgeParity.test.ts`

- [ ] **Step 4: Commit**

```bash
git add web/src/features/work/scanSectionState.ts web/src/bridge/bridgeParity.test.ts
git commit -m "fix(web): derive scan section from scan.state not legacy phase"
```

---

### Task 10: ScanWorkspace + GlobalCommandBar UX

**Files:**
- Modify: `web/src/features/work/ScanWorkspace.tsx`
- Modify: `web/src/components/layout/GlobalCommandBar.tsx`
- Modify: `web/src/bridge/mockBridge.ts` (snapshot builder)

- [ ] **Step 1: ScanWorkspace — dock CTA uses `indexReady`**

```typescript
  const canOpenFileDock =
    Boolean(library.folderPath) && (scan.indexReady || library.fileCount > 0);
```

Show `library.fileCount` in summary while `scan.state === "running"` (not only after success).

- [ ] **Step 2: GlobalCommandBar — show analyze separately**

When `scan.state === "success" && !scan.deepAnalysisComplete && pipeline.phase === "analyze"`, show secondary status from `pipeline.label` instead of treating as blocking scan.

- [ ] **Step 3: mockBridge**

Ensure `getSnapshot()` includes `indexReady` / `deepAnalysisComplete`; after mock scan completes, set both `true`.

- [ ] **Step 4: Manual smoke (dev)**

Run: `cd web && npm run dev` — confirm labels during mock scan if mock simulates phases.

- [ ] **Step 5: Commit**

```bash
git add web/src/features/work/ScanWorkspace.tsx web/src/components/layout/GlobalCommandBar.tsx web/src/bridge/mockBridge.ts
git commit -m "ux(web): scan workspace and command bar phased labels"
```

---

### Task 11: Python contract tests for phase emission

**Files:**
- Modify: `tests/test_bridge_contract.py`

**Note:** `indexReady` before `scan.state=success` is covered by Task 6 deterministic tests (`test_index_ready_before_scan_success`). Do not duplicate with a weak polling-only test.

- [ ] **Step 1: Add phase emission test**

```python
def test_scan_emits_probe_not_legacy_scan_phase(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("x", encoding="utf-8")
    api = create_bridge_api(create_library_session(MemoryLibraryIndex()))
    api.select_folder(str(tmp_path))
    api.start_scan()
    deadline = time.monotonic() + 10.0
    phases: set[str] = set()
    while time.monotonic() < deadline:
        snap = api.get_snapshot()
        phases.add(snap["pipeline"]["phase"])
        if snap["work"]["scan"]["state"] == "success":
            break
        time.sleep(0.02)
    _scan_until_idle(api)
    assert "scan" not in phases
    assert "probe" in phases or "persist" in phases
```

- [ ] **Step 2: Run**

Run: `pytest tests/test_bridge_contract.py -q`

- [ ] **Step 3: Commit**

```bash
git add tests/test_bridge_contract.py
git commit -m "test: scan emits probe phase not legacy scan"
```

---

### Task 12: Final verification gate

- [ ] **Step 1: Python targeted**

Run: `pytest tests/test_bridge_contract.py -q`  
Expected: all pass.

- [ ] **Step 2: Web parity**

Run: `cd web && npm run test -- src/bridge/bridgeParity.test.ts`  
Expected: all pass.

- [ ] **Step 3: Lint (changed paths)**

Run: `ruff check src/application/library_session.py src/infrastructure/sqlite_library_index.py`  
Run: `cd web && npm run lint`

- [ ] **Step 4: Optional full gate**

Run: `python scripts/verify_phase_completion.py`  
Report pass/fail in PR description.

- [ ] **Step 5: Manual 7k checklist** (human)

Record in PR or `docs/release/smoke-record-template.md`:

1. Folder `F:\kiwi\text\소설\정리` (or staging copy).
2. First ~400 files appear in ShellFileDock before scan success.
3. Label shows `인덱스 저장 중…` during persist, not `스캔 중` at 100%.

- [ ] **Step 6: Update spec frontmatter**

In `docs/superpowers/specs/028-...-design.md`:

```yaml
plan: docs/superpowers/plans/046-2026-06-03-infra-scan-streaming-phases.md
```

---

## Plan gate review

**Verdict:** PASS (2026-06-03) after targeted edits.

**Required edits applied before implementation:**

- Task 6 hard-requires record streaming; no full `list[FileRecord]` scan output (`scan_folder_stream` + Plan-locked §7).
- Python `validate_app_snapshot` rejects `phase="scan"`; legacy compat web-only.
- Mid-scan / `indexReady` tests use `monkeypatch` + `threading.Event` on `append_files_batch` (deterministic).
- Weak `indexReady` polling test removed; ordering enforced in Task 6.
- Plan path aligned to **046** (matches PR-46 title).
- Task 3: empty `reset=True` clears folder rows.
- Task 8: `NormalizedPipelinePhase` return type (no `"scan"` in normalize output).

---

## Spec coverage self-review

| Spec section | Task |
| ------------ | ---- |
| LOCK-SCAN-1 phases | Task 6, 7, 8, 9 |
| LOCK-SCAN-2 streaming RAM | Task 6 |
| LOCK-SCAN-3 revision bumps | Task 3, 6 |
| LOCK-SCAN-4 no preview persist | Task 2 |
| LOCK-SCAN-5 labels | Task 4, 6, 10 |
| LOCK-SCAN-6 flags | Task 5, 8, 9 |
| LOCK-SCAN-7 ≥3k background | Task 6 (worker start policy) |
| LOCK-SCAN-8 no IA change | — |
| §5.3 three signals | Task 5, 6 |
| §12 legacy `scan` phase | Task 8, 9 |
| §11 tests | Tasks 2, 3, 5, 6, 7, 11, 12 |
| Plan-locked §7 true streaming | Task 6 |

---

## Verification log

| Command | Status | Date |
| ------- | ------ | ---- |
| `pytest tests/test_bridge_contract.py -q` | PASS 131 | 2026-06-03 |
| `npm run test -- src/bridge/bridgeParity.test.ts` | PASS 50 | 2026-06-03 |
| `python scripts/verify_phase_completion.py` | (not run) | |
