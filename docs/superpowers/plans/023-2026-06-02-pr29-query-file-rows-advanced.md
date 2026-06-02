# PR-29: queryFileRows Advanced / SQL Page Query — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Plan 023 implements approved Spec 017 only.**

```text
No Work UI consumer.
No FileRowsProvider.
No filter chips.
No keyset cursor.
No BridgeApi refactor beyond query_file_rows pass-through/validation.
```

**Goal:** Move production `queryFileRows` from in-memory full-library scan to SQLite-backed paginated queries with normalized `*_key` columns, `file_review_projection` enrichment, extended bridge contract (sort/filters/`technical`), and ShellFileDock-only UI (search, header sort, load-more).

**Architecture:** `LibrarySession` normalizes raw bridge dict → `NormalizedFileRowsQuery` (LOCK-29-13); `SqliteLibraryIndex.query_file_rows_page` runs SQL on `files` + 1:1 `file_review_projection`; projection rebuilds from merged `_review_rows_cache` (exact > near > relation). mockBridge and `file_query.py` share key/sort/filter semantics for tests. UI changes limited to `ShellFileDock`.

**Tech Stack:** Python 3.12 (`application/`, `infrastructure/sqlite_library_index.py`, `app/bridge_api.py`); React 19 + Tailwind v4 (`web/`); pytest + Vitest + minimal Playwright smoke.

**Spec:** [017-2026-06-02-query-file-rows-advanced-design.md](../specs/017-2026-06-02-query-file-rows-advanced-design.md) (**approved** 2026-06-02 — LOCK-29-1..16)

**Plan status:** **Approved** (2026-06-02)

**Prerequisite:** Spec 017 approved; PR-25 FileDock + `queryFileRows` v1; PR-26 invalidation (no second snapshot pollers); **merge PR-28 to `main` before Task 1 implementation** (baseline per spec §0)

**Parent:** [002 PR-26..30 roadmap](../roadmap/002-2026-06-02-pr26-pr30-platform-polish-roadmap.md)

**Test policy:** Extend **`tests/test_bridge_contract.py`**, **`web/src/bridge/bridgeParity.test.ts`**, **`web/e2e/smoke.spec.ts`** — **no new test files** without `TEST_ALLOWED`.

**Scope freeze (LOCK-29):** Copy spec LOCK-29-1..16. PR-30 facade work is **documentation note only** in Task 0 — no implementation in this plan.

---

## Plan-locked constants

| Constant | Value |
|----------|--------|
| Sort whitelist | `name`, `path`, `extension`, `size`, `modifiedAt`, `encoding`, `duplicateGroup`, `integrity` |
| Reject reasons | `INVALID_SORT_FIELD`, `INVALID_FILTER_VALUE` |
| File query max `limit` | **500** |
| Review/quality max `limit` | **200** (unchanged) |
| Default sort | `{ field: "path", direction: "asc" }` |
| Cursor wire | offset string; malformed → `0` |
| Revision reset | `libraryRevision` change → `cursor: null`, replace rows |
| Text key fn | `unicodedata.normalize("NFC", value or "").casefold()` |
| Integrity **ok** | `utf-8`, `ascii` (case-insensitive) |
| Integrity **unknown** | `NULL` or `""` |
| Integrity **issue** | any other non-empty `encoding_status` |
| Projection priority | exact > near > relation; tie `groupId` ASC |
| Perf p95 (10k, local smoke) | initial ≤150ms; search/sort ≤250ms; duplicateGroup join-sort per spec §8 caveat |
| UI consumer | `ShellFileDock` only — **does not send `filters`** in PR-29 |

### LOCK-P29-1 — Layer boundary

```text
Raw bridge dict stops at LibrarySession.query_file_rows.
Infrastructure receives NormalizedFileRowsQuery only.
SQLite row shapes never leak past LibraryIndexPort return DTO.
```

### LOCK-P29-2 — SQL text fields

```text
Do not use LOWER(name) or LOWER(relative_path) for sort/search in production SQL.
Use name_key, relative_path_key, extension_key, encoding_key columns only.
```

### LOCK-P29-3 — Cardinality

```text
query_file_rows_page must return at most one row per files.id.
Enrichment via file_review_projection LEFT JOIN only — no multi-join review_member_state in page SQL.
```

### LOCK-P29-4 — totalFiltered

```text
totalFiltered uses the same WHERE clause as the page query (before LIMIT/OFFSET).
```

### LOCK-P29-5 — File-row limit vs review/quality

```text
query_file_rows must not use LibrarySession._clamp_query_limit (max 200).
Limit clamp lives only in normalize_file_rows_query (max 500).
query_review_rows / query_quality_rows keep _clamp_query_limit unchanged.
```

### LOCK-P29-6 — Green commits

Every task commit leaves touched tests green:

- Python: `pytest tests/test_bridge_contract.py -k file_row -q` (or narrower `-k`)
- Web: `cd web && npm run test -- src/bridge/bridgeParity.test.ts`
- Before PR close: `python scripts/verify_phase_completion.py`

---

## File map

| File | Action |
|------|--------|
| `src/application/file_row_query.py` | **Create** — `NormalizedFileRowsQuery`, `normalize_file_rows_query`, `text_sort_key`, errors |
| `src/application/file_query.py` | **Modify** — use shared key fn; reference path for tests/mock |
| `src/application/ports/library_index.py` | **Modify** — `query_file_rows_page(normalized)` |
| `src/infrastructure/sqlite_library_index.py` | **Modify** — schema migration, keys on `replace_files`, projection table, SQL page query, indexes §spec 8.2 |
| `src/application/file_review_projection.py` | **Create** — build projection from `_review_rows_cache` rows |
| `src/application/library_session.py` | **Modify** — delegate `query_file_rows`; rebuild projection on review cache refresh |
| `src/app/bridge_contract.py` | **Modify** — `FileRowQueryError`, `FILE_ROW_SORT_FIELDS` |
| `src/app/bridge_api.py` | **Modify** — map `FileRowQueryError` on `query_file_rows` |
| `tests/test_bridge_contract.py` | **Extend** — sort, filter, cursor, keys, projection, 10k optional smoke |
| `web/src/types/fileRows.ts` | **Modify** — `sort`, `filters`, `technical`, sort field type |
| `web/src/contracts/fileRowsPageContract.ts` | **Modify** — max limit 500 |
| `web/src/contracts/reviewPageContract.ts` | **No change** to `MAX_QUERY_LIMIT` (200) |
| `web/src/bridge/bridgeErrors.ts` | **Modify** — `INVALID_FILTER_VALUE` |
| `web/src/bridge/parseBridgeRejection.ts` | **Modify** — recognize filter rejection |
| `web/src/bridge/mockFileRows.ts` | **Modify** — sort/filter/key parity |
| `web/src/bridge/mockBridge.ts` | **Modify** — wire extended query |
| `web/src/bridge/bridgeParity.test.ts` | **Extend** |
| `web/src/components/layout/shellFileDockColumns.ts` | **Modify** — `technical` preset |
| `web/src/components/layout/ShellFileDock.tsx` | **Modify** — sort headers, load more, revision reset |
| `web/e2e/smoke.spec.ts` | **Extend** — minimal dock sort + load more |
| `scripts/perf_file_rows_query.py` | **Create** (optional) — local 10k perf smoke; non-blocking CI |
| `docs/superpowers/specs/017-*.md` | **Modify** — link plan status when done |
| `docs/superpowers/roadmap/002-*.md` | **Modify** — PR-29 plan approved / done |

---

## Recommended commit slices

| # | Contents |
|---|----------|
| 1 | Plan approval only (docs) |
| 2 | Task 1 — normalization + port types + bridge errors |
| 3 | Tasks 2–3 — schema, keys, indexes, key parity tests |
| 4 | Tasks 4–7 — SQL page query, projection lifecycle, session delegation |
| 5 | Tasks 8–9 — bridge + mock parity |
| 6 | Task 10 — ShellFileDock UI |
| 7 | Tasks 11–14 — contract tests, E2E, perf smoke, docs/verify |

Each commit: touched tests green (`pytest tests/test_bridge_contract.py -k file_row -q` and targeted `npm run test`).

---

## PR-30 parallel note (Task 0 only — no code)

Per spec 017 §12: PR-30 may run in parallel only with characterization-first, behavior-preserving facade skeleton — **no** `queryFileRows` ownership change, **no** BridgeApi surgery before this plan completes. This plan does not schedule PR-30 tasks.

---

### Task 0: Plan gate

**Gate passed 2026-06-02 — Tasks 1–14 may proceed.**

- [x] Confirm [spec 017](../specs/017-2026-06-02-query-file-rows-advanced-design.md) `status: approved`
- [x] Baseline: PR-28 waiver — implement on current feature branch until merged to `main`
- [x] **No new test files** unless `TEST_ALLOWED`
- [x] Commit slices 1–7 approved
- [x] `Plan status: **Approved** (2026-06-02)`
- [x] Roadmap 002: PR-29 plan row → approved

---

### Task 1: Query normalization / application errors

**Files:**
- Create: `src/application/file_row_query.py`
- Modify: `src/app/bridge_contract.py`
- Test: `tests/test_bridge_contract.py` (reject cases first)

- [x] **Step 1:** Add `FILE_ROW_SORT_FIELDS`, `FileRowQueryError` with `reason` (`INVALID_SORT_FIELD` | `INVALID_FILTER_VALUE`) in `bridge_contract.py` (mirror `QualityQueryError` pattern).

- [x] **Step 2:** Implement `NormalizedFileRowsQuery` dataclass and `normalize_file_rows_query(raw: dict) -> NormalizedFileRowsQuery`:
  - sort whitelist + default path asc
  - filter enum validation (§spec 5.5, 5.5.1)
  - cursor parse (int offset, malformed → 0)
  - limit clamp 1..500
  - normalized search term (casefolded) or None
  - **Do not** pass raw dict to port layer

- [x] **Step 3:** Export `text_sort_key(value: str) -> str` for shared use (LOCK-P29-2).

- [x] **Step 4:** Tests — unknown `sort.field` → `FileRowQueryError`; invalid `filters.duplicateGroup` → `INVALID_FILTER_VALUE`; limit 999 → 500.

**Verify:** `pytest tests/test_bridge_contract.py -k "file_row and (sort or filter or limit)" -q`

---

### Task 2: SQLite schema upgrade

**Files:**
- Modify: `src/infrastructure/sqlite_library_index.py`
- Test: `tests/test_bridge_contract.py` (schema + replace_files keys)

- [x] **Step 1:** Extend `_SCHEMA` — add columns to `files`:
  - `name_key`, `relative_path_key`, `extension_key`, `encoding_key` TEXT NOT NULL DEFAULT ''
  - Migration: `ALTER TABLE` or recreate — existing DBs on disk must be handled (see Step 4)

- [x] **Step 2:** Add `file_review_projection` table per spec §5.4 + index `idx_file_review_folder_group_key_id`.

- [x] **Step 3:** Add spec §8.2 indexes (verbatim DDL from spec 017):

```sql
CREATE INDEX IF NOT EXISTS idx_files_folder_path_id
  ON files(folder_path, relative_path_key, id);
CREATE INDEX IF NOT EXISTS idx_files_folder_name_id
  ON files(folder_path, name_key, id);
CREATE INDEX IF NOT EXISTS idx_files_folder_extension_id
  ON files(folder_path, extension_key, id);
CREATE INDEX IF NOT EXISTS idx_files_folder_size_id
  ON files(folder_path, size_bytes, id);
CREATE INDEX IF NOT EXISTS idx_files_folder_modified_id
  ON files(folder_path, modified_at_ns, id);
CREATE INDEX IF NOT EXISTS idx_files_folder_encoding_id
  ON files(folder_path, encoding_key, id);
CREATE INDEX IF NOT EXISTS idx_file_review_folder_group_key_id
  ON file_review_projection(folder_path, duplicate_group_key, file_id);
```

- [x] **Step 4:** **Backfill strategy (plan lock):** On connect, `ALTER TABLE` missing `*_key` columns then `_backfill_file_keys()` from stored columns. **Forbidden:** empty `*_key` on active rows after migration.

- [x] **Step 5:** Update `replace_files()` to populate all `*_key` via `text_sort_key`.

**Verify:** pytest — insert files, assert keys non-empty; projection table exists.

---

### Task 3: Key generation parity

**Files:**
- Modify: `src/application/file_query.py`
- Modify: `web/src/bridge/mockFileRows.ts`
- Test: `tests/test_bridge_contract.py`, `web/src/bridge/bridgeParity.test.ts`

- [ ] **Step 1:** Refactor `file_query._filter_rows` / sort to use `text_sort_key` on name/path/extension (in-memory reference).

- [ ] **Step 2:** TS `textSortKey` in `mockFileRows.ts` — same NFC + casefold semantics (export for tests).

- [ ] **Step 3:** Fixtures — ASCII case pair, Korean filename pair, accent Unicode pair (`café` / `CAFE`), extension case-insensitive filter.

**Verify:** Python + TS parity tests green on small fixture set.

---

### Task 4: Port extension

**Files:**
- Modify: `src/application/ports/library_index.py`
- Modify: in-memory test double if any (else skip)

- [ ] **Step 1:** Add `query_file_rows_page(self, normalized: NormalizedFileRowsQuery) -> dict[str, Any]` to `LibraryIndexPort` — return `FileRowsPage`-compatible dict only.

- [ ] **Step 2:** Stub raises `NotImplementedError` on non-SQLite fakes until Task 5; `LibrarySession` will not call production path until Task 7.

**Verify:** `mypy src` clean on port import.

---

### Task 5: SQL page query

**Files:**
- Modify: `src/infrastructure/sqlite_library_index.py`
- Test: `tests/test_bridge_contract.py`

- [ ] **Step 1:** Implement `query_file_rows_page(normalized)`:
  - **WHERE:** `folder_path = current`; search on `*_key` LIKE (escape `%` `_`); extension/encoding filters on keys; duplicateGroup on projection; integrity buckets per spec 5.5.1
  - **ORDER BY:** whitelist column mapping; `id ASC` tie-break always
  - **Pagination:** OFFSET from cursor; LIMIT; compute `hasMore`, `nextCursor`, `totalFiltered` (LOCK-P29-4)
  - **SELECT:** map to `FileRow` wire dict; join projection 1:1 (LOCK-P29-3)

- [ ] **Step 2:** Sort `duplicateGroup` via `duplicate_group_key`; document join-sort in test comment.

- [ ] **Step 3:** Empty library → `empty_file_rows_page` shape (regression LOCK-P25-3).

- [ ] **Step 4:** Tests — default path order; each whitelist sort; search `%` `_` escaping; cursor math; totalFiltered with filter.

**Verify:** `pytest tests/test_bridge_contract.py -k file_row -q`

---

### Task 6: Review projection lifecycle

**Files:**
- Create: `src/application/file_review_projection.py`
- Modify: `src/application/library_session.py`
- Modify: `src/infrastructure/sqlite_library_index.py` — `replace_file_review_projection(folder, rows)`

- [ ] **Step 1:** `build_file_review_projection(review_rows_cache) -> list[projection_row]`:
  - member rows only (`rowKind == "file"` or equivalent locked id pattern)
  - priority exact > near > relation; tie `groupId` ASC
  - `isKeeper` from member row keeper semantics (`proposedAction == "keep"` or spec-aligned field)

- [ ] **Step 2:** Call rebuild after every `_review_rows_cache` refresh (scan complete, near/relation merge, review decision updates — find all rebuild sites).

- [ ] **Step 3:** Persist via `replace_file_review_projection` in same folder scope as files.

- [ ] **Step 4:** Tests — two memberships → one projection row; keeper flag; exact beats near.

**Verify:** projection cardinality tests pass.

---

### Task 7: LibrarySession delegation

**Files:**
- Modify: `src/application/library_session.py`
- Modify: `src/app/bridge_api.py`

- [ ] **Step 1:** Replace in-memory path — **remove** `_clamp_query_limit` from `query_file_rows` (LOCK-P29-5; limit only in `normalize_file_rows_query`):

```python
# REMOVE:
limit = _clamp_query_limit(query)
rows = [file_record_to_row(record) for record in self._files_by_id.values()]
return query_file_page(rows, query, limit=limit)
```

With:

```python
normalized = normalize_file_rows_query(query)
return self._index.query_file_rows_page(normalized)
```

- [ ] **Step 2:** Catch `FileRowQueryError` in `bridge_api.query_file_rows` → rejected JSON (mirror quality).

- [ ] **Step 3:** Acceptance grep / test: production path does not iterate all `_files_by_id` for query (allow `files()` for other use cases).

**Verify:** contract tests + mypy.

---

### Task 8: Bridge / contract validation (TS)

**Files:**
- Modify: `web/src/types/fileRows.ts`
- Modify: `web/src/contracts/fileRowsPageContract.ts`
- Modify: `web/src/bridge/bridgeErrors.ts`, `parseBridgeRejection.ts`
- Modify: `web/src/bridge/pywebviewBridge.ts` (validate page if needed)

- [ ] **Step 1:** Extend `FileRowsQuery` / `FileRowSortField` / `filters` / `technical` preset type.

- [ ] **Step 2:** `clampFileRowsLimit` max **500** — do not change `reviewPageContract.MAX_QUERY_LIMIT`.

- [ ] **Step 3:** Parse `INVALID_FILTER_VALUE` for dock error display.

**Verify:** `cd web && npm run lint`

---

### Task 9: mockBridge parity

**Files:**
- Modify: `web/src/bridge/mockFileRows.ts`, `mockBridge.ts`
- Test: `web/src/bridge/bridgeParity.test.ts`

- [ ] **Step 1:** Apply sort/filter/search/cursor/limit before slice; same whitelist rejects.

- [ ] **Step 2:** Enrich mock rows with duplicate fields when mock review data exists (or stub consistent with Python small fixture).

- [ ] **Step 3:** Tests — sort changes order; invalid sort throws `BridgeCallError`; limit clamp 500.

**Verify:** `npm run test -- src/bridge/bridgeParity.test.ts`

---

### Task 10: ShellFileDock UI

**Files:**
- Modify: `web/src/components/layout/shellFileDockColumns.ts`
- Modify: `web/src/components/layout/ShellFileDock.tsx`
- Test: `web/e2e/smoke.spec.ts` (Task 12)

- [ ] **Step 1:** Add `technical` preset + columns (속성 = `—` silent).

- [ ] **Step 2:** Sortable headers per spec §6.3 — click toggles asc/desc; map `col.id` → `sort.field`; call `queryFileRows` with `cursor: null`.

- [ ] **Step 3:** Load more button when `pageInfo.hasMore` — append rows with `cursor: nextCursor`.

- [ ] **Step 4:** Reset on `debouncedSearch`, sort, `libraryRevision` — replace rows, clear accumulated.

- [ ] **Step 5:** **LOCK-29-16:** Do not add filter chips; do not send `filters` in query object.

- [ ] **Step 6:** Optional `data-testid` on sort header / load-more for E2E.

**Verify:** `npm run test` + manual dock smoke.

---

### Task 11: Python contract tests (consolidated)

**Files:**
- Modify: `tests/test_bridge_contract.py`

- [ ] Cover checklist from spec §9:
  - default path sort
  - each whitelist sort field
  - `INVALID_SORT_FIELD` / `INVALID_FILTER_VALUE`
  - cursor math; malformed cursor → 0
  - limit 500 clamp
  - search escaping
  - projection cardinality + enrichment
  - empty library shape
  - filter contract via API (bridge-only — no UI)

**Verify:** `pytest tests/test_bridge_contract.py -k file_row -q`

---

### Task 12: E2E smoke (minimal)

**Files:**
- Modify: `web/e2e/smoke.spec.ts`

- [ ] Expand dock only:
  - expand file dock
  - rows visible after scan fixture
  - click sortable header → request/order change observable
  - load more visible when fixture large enough → append rows

- [ ] **Forbidden:** full E2E suite expansion unrelated to dock.

**Verify:** `cd web && npm run test:e2e` (or project script)

---

### Task 13: Perf smoke (local checklist)

**Files:**
- Create (optional): `scripts/perf_file_rows_query.py`
- Modify: this plan verification section when run

- [ ] Insert 10k file rows (test helper or script).
- [ ] Measure p95: initial page, search, path/name sort, duplicateGroup sort.
- [ ] Record results in PR notes; **non-blocking** for CI.
- [ ] Note join-sort caveat if duplicateGroup > 250ms.

**Local checklist item (required before plan Complete):**

```text
[ ] perf_file_rows_query.py run locally OR documented skip reason
```

---

### Task 14: Final verification / docs

**Files:**
- Modify: spec 017 plan link; roadmap 002; this plan status

- [ ] Run `python scripts/verify_phase_completion.py` — record pass/fail.
- [ ] `pytest` full; `cd web && npm run test`; lint.
- [ ] Roadmap PR-29 → **Done** when merged.
- [ ] Update `Plan status: **Complete** (YYYY-MM-DD)`.

---

## Acceptance mapping (spec §10)

| Criterion | Task |
|-----------|------|
| SQL production path | 5, 7 |
| ShellFileDock only consumer | 10 |
| Sort whitelist + reject | 1, 5, 8, 9, 11 |
| Offset cursor + revision reset | 5, 10, 11 |
| `technical` preset | 8, 10 |
| Load-more 10k | 5, 10, 13 |
| duplicate enrichment | 6, 5, 11 |
| mock/Python parity | 3, 9, 11 |
| verify_phase_completion | 14 |
| No filter chips UI | 10 |
| Bridge filters tested | 1, 5, 11 |

---

## Risks / notes

- **DB migration:** dev machines with old `library.db` — Task 2 Step 4 must not ship broken keys.
- **`_files_by_id`:** still used for review/detail pipelines; only `query_file_rows` stops full materialization.
- **Join sort perf:** duplicateGroup may exceed 250ms p95 — perf smoke documents; do not weaken contract tests.
- **Breaking:** file-row limit 500 vs 200 on other queries — ensure clamps are API-specific.

---

## Changelog

| Date | Change |
|------|--------|
| 2026-06-02 | Initial plan 023 from approved spec 017; Tasks 0–14; commit slices; LOCK-P29-1..4 |
| 2026-06-02 | Gate review: LOCK-P29-5/6; §8.2 DDL in Task 2; Task 7 `_clamp_query_limit` split |
