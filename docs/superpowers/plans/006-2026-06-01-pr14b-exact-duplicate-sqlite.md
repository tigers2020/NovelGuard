# PR-14b: SQLite Index + Exact Duplicate + Review Rows — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add streaming SHA-256 during scan, persist files in SQLite via `LibraryIndexPort`, compute exact duplicate groups, and return real `ReviewRowsPage.rows` from `query_review_rows` — without quality rows, FS apply, or UI changes.

**Architecture:** Extend scan completion path: hash files → store in SQLite → run `domain.duplicate_exact` → cache flattened `ReviewRow` dicts in session (or recompute on query from groups). `MemoryLibraryIndex` remains for unit tests; desktop uses `SqliteLibraryIndex`. Snapshot `work.resolve` duplicate counts reflect real groups.

**Tech Stack:** Python 3.12, sqlite3 (stdlib), pytest.

**Spec:** [002-2026-06-01-novelguard-greenfield-library-session-design.md](../specs/002-2026-06-01-novelguard-greenfield-library-session-design.md) (approved)

**Parent plan:** [005-2026-06-01-pr14a-greenfield-library-session-scan.md](./005-2026-06-01-pr14a-greenfield-library-session-scan.md) (**Done**)

**Test policy:** Extend `tests/test_bridge_contract.py` only unless `TEST_ALLOWED`.

**Non-goals (PR-14b):** Quality analyzer / `query_quality_rows` data, near/relation duplicate, FS move/delete, apply behavior change, UI/React, packaging, legacy restore.

---

## Plan-locked decisions

### Hash injection (scanner stays walk-only)

```text
filesystem_scanner.scan_folder(..., content_hash_fn: Callable[[Path], str] | None = None)
LibrarySession injects infrastructure.content_hasher.hash_file via content_hash_fn.
Scanner only walks + stats; hashing is enabled in PR-14b by session composition, not embedded hasher imports in domain/application.
```

### SQLite folder scope (port unchanged)

```text
LibraryIndexPort.files() has no folder argument (frozen since PR-14a).
SqliteLibraryIndex.replace_files(folder, files) sets _current_folder = folder.
SqliteLibraryIndex.files() SELECTs rows for _current_folder only.
MemoryLibraryIndex mirrors the same _current_folder semantics for tests.
```

### DB path test isolation

```text
Production default: Path.home() / ".novelguard" / "library.db"
Tests MUST inject tmp_path / "library.db" via create_library_session(index=SqliteLibraryIndex(tmp_path / "library.db")).
Tests must not write to Path.home() / ".novelguard".
```

### Review row stable ids

```text
group row id = "group:" + group_id
member row id = "file:" + group_id + ":" + file_id
FileRecord.id unchanged (make_file_id). Never use content_sha256 as row id.
```

### Filter semantics (near/relation)

```text
filters.types contains only near | relation | move_only (no exact) → empty valid ReviewRowsPage
filters.types contains exact or types omitted → filter exact rows normally
unknown type tokens → treated as non-matching (empty), no exception
```

| Item | Decision |
|------|----------|
| Content hash | SHA-256 via injected `content_hash_fn` during scan |
| `FileRecord.id` | Unchanged from 14a (`make_file_id`) — **not** content hash |
| `content_sha256` | Separate field; used only for duplicate grouping |
| Storage | `SqliteLibraryIndex` implements `LibraryIndexPort`; default in `create_library_session()` |
| Duplicate | Exact only: size bucket → `content_sha256` → groups with count ≥ 2 |
| Review rows | Real `ReviewRowsPage`; filter/sort/pagination aligned with `mockData.ts` semantics |
| Keeper v1 | Largest `size_bytes`; tie → lexicographic `relative_path` |
| Quality | Empty valid pages (14c) |
| Apply | PR-13 no-op unchanged; preview row id may use real file ids when present |
| `libraryRevision` | Bump after scan completes **and** duplicate index built |

```text
14b scan completion order:
1. Walk files (14a scanner)
2. Stream-hash each file → set content_sha256
3. Persist FileRecord rows to SQLite
4. Run duplicate_exact → DuplicateGroup list
5. Build review row cache + snapshot aggregate counts
```

---

## File map

| File | Action |
|------|--------|
| `src/domain/duplicate_exact.py` | **Create** — grouping + keeper selection |
| `src/domain/models.py` | **Modify** — `DuplicateGroup` dataclass |
| `src/infrastructure/content_hasher.py` | **Create** — streaming SHA-256 |
| `src/infrastructure/filesystem_scanner.py` | **Modify** — optional hash callback per file |
| `src/infrastructure/sqlite_library_index.py` | **Create** — schema + CRUD |
| `src/infrastructure/db/schema.sql` or inline | **Create** — files table |
| `src/application/review_rows_builder.py` | **Create** — groups → ReviewRow dicts |
| `src/application/review_query.py` | **Create** — filter/sort/paginate |
| `src/application/library_session.py` | **Modify** — hash, duplicate, real query |
| `src/application/dto_mapper.py` | **Modify** — resolve counts from session stats |
| `src/app/session_factory.py` | **Modify** — default SQLite path under user data or temp |
| `tests/test_bridge_contract.py` | **Extend** — duplicate fixture, review rows |

---

## Acceptance criteria

```text
✓ After scan, content_sha256 populated on stored files
✓ SQLite persists files; re-open session can reload (same process) optional smoke
✓ query_review_rows returns type "exact" rows for duplicate fixture (2+ same content)
✓ Snapshot groupCount / queueCount match duplicate groups (not mock 37)
✓ Near/relation filter returns empty rows, not error
✓ PR-13 pytest still pass; apply no-op
✓ verify_phase_completion.py PASS
✓ mockBridge unchanged
```

---

### Task 1: `DuplicateGroup` + `duplicate_exact`

**Files:**
- Modify: `src/domain/models.py`
- Create: `src/domain/duplicate_exact.py`

- [ ] **Step 1: Add `DuplicateGroup`**

```python
@dataclass(frozen=True, slots=True)
class DuplicateGroup:
    group_id: str
    member_ids: tuple[str, ...]
    keeper_id: str
```

- [ ] **Step 2: Implement `find_exact_duplicate_groups(files: list[FileRecord]) -> list[DuplicateGroup]`**

- Skip files with `content_sha256 is None`
- Size bucket → hash bucket → count >= 2
- `group_id = f"dup-{content_sha256[:16]}"` (document in code)
- Keeper: max size, tie `relative_path`

- [ ] **Step 3: Unit test in `tests/test_bridge_contract.py`**

Two in-memory `FileRecord` same size+hash → one group, keeper = larger path or only tie-break.

- [ ] **Step 4: Commit** `[domain] exact duplicate grouping`

---

### Task 2: Streaming content hasher

**Files:**
- Create: `src/infrastructure/content_hasher.py`

- [ ] **Step 1: `hash_file(path: Path) -> str` using 64KiB chunks**

- [ ] **Step 2: Test** small temp file → known SHA-256 vector (use short `"hello"` golden)

- [ ] **Step 3: Commit** `[infrastructure] streaming content SHA-256`

---

### Task 3: Scanner hash hook + session injection

**Files:**
- Modify: `src/infrastructure/filesystem_scanner.py`
- Modify: `src/application/library_session.py`

- [ ] **Step 1: Add optional `content_hash_fn: Callable[[Path], str] | None` to `scan_folder`**

After `stat`, if fn provided: `content_sha256 = content_hash_fn(path)` else `None`.

- [ ] **Step 2: `LibrarySession` passes `hash_file` from `content_hasher` when starting scan**

- [ ] **Step 3: Commit** `[infrastructure] optional content_hash_fn on scan`

---

### Task 4: `SqliteLibraryIndex`

**Files:**
- Create: `src/infrastructure/sqlite_library_index.py`

- [ ] **Step 1: Schema**

```sql
CREATE TABLE files (
  id TEXT PRIMARY KEY,
  folder_path TEXT NOT NULL,
  relative_path TEXT NOT NULL,
  name TEXT NOT NULL,
  size_bytes INTEGER NOT NULL,
  modified_at_ns INTEGER NOT NULL,
  extension TEXT NOT NULL,
  content_sha256 TEXT,
  encoding_status TEXT
);
CREATE INDEX idx_files_folder ON files(folder_path);
```

- [ ] **Step 2: `replace_files(folder, files)` — DELETE folder rows + INSERT**

- [ ] **Step 3: `files() -> list[FileRecord]` for current folder**

- [ ] **Step 4: `session_factory` — default `Path.home() / ".novelguard" / "library.db"`; accept optional `db_path` for tests**

- [ ] **Step 5: Test round-trip** with `tmp_path / "library.db"` only — never `Path.home()`

- [ ] **Step 6: Commit** `[infrastructure] SQLite library index`

---

### Task 5: Review row builder + query

**Files:**
- Create: `src/application/review_rows_builder.py`
- Create: `src/application/review_query.py`

- [ ] **Step 1: `build_review_rows(groups, files_by_id) -> list[dict]`** per spec mapping (group header + member rows)

- [ ] **Step 2: Port filter/sort/paginate logic from `web/src/bridge/mockData.ts` behavior** (Python rewrite, no TS import)

- [ ] **Step 3: `query_review_rows(query) -> ReviewRowsPage` dict**

- [ ] **Step 4: Commit** `[application] review rows builder and query`

---

### Task 6: Wire `LibrarySession`

**Files:**
- Modify: `src/application/library_session.py`
- Modify: `src/application/dto_mapper.py`

- [ ] **Step 1: After successful scan+hash+sqlite replace, compute groups; store `_review_rows_cache` under lock**

- [ ] **Step 2: `get_snapshot` — set `duplicateGroups`, `queueCount`, `groupCount` from cache**

- [ ] **Step 3: `query_review_rows` delegates to `review_query`**

- [ ] **Step 4: `get_duplicate_group_detail` — return member file names/paths minimal JSON**

- [ ] **Step 5: Commit** `[application] wire duplicate review into session`

---

### Task 7: Contract tests

**Files:**
- Modify: `tests/test_bridge_contract.py`

- [ ] **Step 1: Fixture folder with two identical-content `.txt` files (same bytes, different names)**

- [ ] **Step 2: `test_query_review_rows_exact_duplicate_pair` — rows non-empty, all `type == "exact"`**

- [ ] **Step 3: `test_snapshot_duplicate_group_count` — `groupCount >= 1`**

- [ ] **Step 4: `test_query_review_rows_near_filter_empty` — types `["near"]` → empty valid page**

- [ ] **Step 5: Run `python scripts/verify_phase_completion.py`**

- [ ] **Step 5: Commit** `[tests] PR-14b duplicate review rows`

---

## Plan self-review

| Spec § | Task |
|--------|------|
| SHA-256 streaming | 2–3 |
| SQLite port | 4 |
| duplicate_exact | 1, 6 |
| Review row mapping | 5 |
| Empty quality (14c) | unchanged |
| No FS apply | unchanged |

---

## Execution handoff

After PR-14b merges, proceed to **PR-14c** quality analyzer plan.
