# PR-14c: Quality Analyzer + Query Rows + Snapshot Counts — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Connect Quality tab backend row source — detect empty/tiny/invalid-UTF-8/read-error issues during scan, persist in SQLite, return real `QualityRowsPage` from `query_quality_rows`, and reflect issue counts in `get_snapshot` — without UI/React/mockBridge changes.

**Architecture:** After scan+hash+sqlite file replace (14b path), run `quality_analyzer` on collected files → persist `quality_issues` per folder → cache flattened `QualityRow` dicts in session. `MemoryLibraryIndex` mirrors folder-scoped quality storage for unit tests. Snapshot `work.quality.*` and `fileListSummary.issueCount` reflect real counts.

**Tech Stack:** Python 3.12, sqlite3 (stdlib), pytest.

**Spec:** [002-2026-06-01-novelguard-greenfield-library-session-design.md](../specs/002-2026-06-01-novelguard-greenfield-library-session-design.md) (approved)

**Parent plans:** [005-2026-06-01-pr14a-greenfield-library-session-scan.md](./005-2026-06-01-pr14a-greenfield-library-session-scan.md) (**Done**), [006-2026-06-01-pr14b-exact-duplicate-sqlite.md](./006-2026-06-01-pr14b-exact-duplicate-sqlite.md) (**Done**)

**Test policy:** Extend `tests/test_bridge_contract.py` only unless `TEST_ALLOWED`.

**Non-goals (PR-14c):** UI/React/mockBridge changes, apply/finalize repair, near/relation duplicate, small-file cleanup execution, NLP quality analysis.

---

## Plan-locked decisions

### Domain model

```text
src/domain/quality.py — QualityIssue dataclass
- issue_id: str (stable sha256 prefix of file_id|kind)
- file_id, path, severity, kind, message, evidence
- kind: empty_file | tiny_file | invalid_utf8 | read_error
- severity: warning | error (no info rows in v1)
```

### Row id (stable, PR-14b pattern)

```text
quality row id = "quality:" + issue_id
```

### One issue per file (priority)

```text
empty_file > read_error > invalid_utf8 > tiny_file
```

### Kind → UI `QualityIssueType` mapping

| kind | issueType | severity |
|------|-----------|----------|
| empty_file | small_file | error |
| tiny_file | small_file | warning |
| invalid_utf8 | encoding | error |
| read_error | integrity | error |

### Analyzer boundary

```text
Detect only — no UTF-8 conversion, no repair, no delete.
Default tiny threshold: 128 bytes (configurable in analyzer).
Inject read_file callable for read_error tests (monkeypatch).
```

### SQLite folder scope

```text
quality_issues(folder_path, issue_id, ...) — same folder scoping as files table.
replace_quality_issues(folder, issues) — DELETE folder rows + INSERT on scan complete.
Tests MUST use tmp_path DB injection — never Path.home().
```

### Query filter semantics

```text
issueType required; must be integrity | encoding | small_file — else empty valid page
filters.severity — exact match
filters.search — name/path/integrity message contains (case-insensitive)
limit/cursor — same contract as review_query
Unknown tokens (e.g. issueType "near") → empty valid page, no exception
```

### Snapshot counts

```text
work.quality.integrityIssueCount / encodingIssueCount / smallFileAnomalyCount
fileListSummary.issueCount = total issues
library.integrityIssues = integrityIssueCount
```

| Item | Decision |
|------|----------|
| Tiny threshold | 128 bytes default |
| Persistence | `SqliteLibraryIndex.replace_quality_issues` |
| Port | Extend `LibraryIndexPort` with quality methods |
| `get_quality_issue_detail` | Out of locked scope — keep stub (14d) |
| Scan order | files → duplicates → quality → revision bump |

```text
14c scan completion order (after 14b steps 1–4):
5. Run quality_analyzer on collected files
6. Persist quality_issues to SQLite
7. Build quality row cache + snapshot quality counts
8. Bump libraryRevision (unchanged — single bump at end)
```

---

## File map

| File | Action |
|------|--------|
| `src/domain/quality.py` | **Create** — `QualityIssue`, `make_issue_id` |
| `src/application/quality_analyzer.py` | **Create** — detect-only rules |
| `src/application/quality_rows_builder.py` | **Create** — issues → QualityRow dicts |
| `src/application/quality_query.py` | **Create** — filter/sort/paginate |
| `src/application/ports/library_index.py` | **Modify** — quality port methods |
| `src/infrastructure/sqlite_library_index.py` | **Modify** — `quality_issues` table |
| `src/infrastructure/memory_library_index.py` | **Modify** — in-memory quality store |
| `src/application/library_session.py` | **Modify** — analyze on scan, real query |
| `src/application/dto_mapper.py` | **Modify** — quality snapshot counts |
| `tests/test_bridge_contract.py` | **Extend** — quality fixture tests |

---

## Acceptance criteria

```text
✓ empty file → empty_file issue, issueType small_file, severity error
✓ very small non-empty file → tiny_file, issueType small_file, severity warning
✓ invalid UTF-8 bytes → invalid_utf8, issueType encoding
✓ read error (monkeypatch) → read_error, issueType integrity
✓ scan replaces quality cache; re-scan clears old issues for folder
✓ other folder quality issues do not leak into query
✓ query_quality_rows(issueType="near") → empty valid page
✓ row id stable: quality:<issue_id>
✓ snapshot quality counts match detected issues
✓ tmp_path DB only in tests; mockBridge unchanged
✓ verify_phase_completion.py PASS
```

---

### Task 1: Domain `QualityIssue`

**Files:** Create `src/domain/quality.py`

- [ ] **Step 1:** `QualityIssue` frozen dataclass with fields per plan
- [ ] **Step 2:** `make_issue_id(file_id, kind) -> str`
- [ ] **Step 3:** Test via bridge contract (analyzer tests)

---

### Task 2: Quality analyzer

**Files:** Create `src/application/quality_analyzer.py`

- [ ] **Step 1:** `analyze_quality(folder_path, files, *, tiny_threshold_bytes=128, read_bytes=...)`
- [ ] **Step 2:** Priority: empty → read_error → invalid_utf8 → tiny
- [ ] **Step 3:** Tests in `test_bridge_contract.py`

---

### Task 3: SQLite + Memory quality persistence

**Files:** Modify index port + implementations

- [ ] **Step 1:** Extend `LibraryIndexPort` with `replace_quality_issues`, `quality_issues`
- [ ] **Step 2:** SQLite schema + CRUD (folder-scoped replace)
- [ ] **Step 3:** MemoryLibraryIndex parity
- [ ] **Step 4:** Test round-trip + folder isolation

---

### Task 4: Quality rows builder + query

**Files:**
- Create `src/application/quality_rows_builder.py`
- Create `src/application/quality_query.py`

- [ ] **Step 1:** Map issues → QualityRow-shaped dicts (`quality:<issue_id>`)
- [ ] **Step 2:** Filter/paginate aligned with `mockBridge.ts` semantics
- [ ] **Step 3:** Unknown issueType → empty valid page

---

### Task 5: Wire `LibrarySession` + snapshot

**Files:**
- Modify `src/application/library_session.py`
- Modify `src/application/dto_mapper.py`

- [ ] **Step 1:** `_rebuild_quality_index` after scan; clear on folder reset/cancel
- [ ] **Step 2:** `query_quality_rows` delegates to `quality_query`
- [ ] **Step 3:** `build_snapshot` receives quality count kwargs

---

### Task 6: Contract tests

**Files:** Modify `tests/test_bridge_contract.py`

- [ ] **Step 1:** Fixture folder with empty, tiny, bad-UTF-8 files
- [ ] **Step 2:** `test_query_quality_rows_detects_issues`
- [ ] **Step 3:** `test_query_quality_rows_unknown_issue_type_empty`
- [ ] **Step 4:** `test_snapshot_quality_counts`
- [ ] **Step 5:** `test_sqlite_quality_issues_folder_scoped`
- [ ] **Step 6:** Run `python scripts/verify_phase_completion.py`

---

## Plan self-review

| Spec § | Task |
|--------|------|
| Quality analysis v1 | 1–2 |
| SQLite persistence | 3 |
| query_quality_rows | 4–5 |
| Snapshot quality counts | 5 |
| No UI / no repair | all |

---

## Implementation status

| Item | Status |
|------|--------|
| PR-14c Tasks 1–6 | **Done — CLOSED** |

**Verification (2026-06-01):** `pytest` 36/36 · `verify_phase_completion.py` 5/5 PASS

**Commits:** `1dc86e4` (docs), `52101c4` (app)

---

## Execution handoff

After PR-14c merges, proceed to **PR-14d** contract parity + E2E hooks.
