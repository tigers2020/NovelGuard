---
title: PR-29 queryFileRows Advanced / SQL Page Query
status: approved
grill_me: 2026-06-02
approved: 2026-06-02
date: 2026-06-02
authors: PR-29 brainstorming + scope gate + grill review 2026-06-02
parent_spec: docs/superpowers/specs/013-2026-06-02-shell-filedock-design.md
related_specs:
  - docs/superpowers/specs/002-2026-06-01-novelguard-greenfield-library-session-design.md
  - docs/superpowers/specs/014-2026-06-02-snapshot-invalidation-design.md
  - docs/superpowers/specs/015-2026-06-02-quality-grid-parity-design.md
roadmap: docs/superpowers/roadmap/002-2026-06-02-pr26-pr30-platform-polish-roadmap.md
pr_label: PR-29
plan: docs/superpowers/plans/023-2026-06-02-pr29-query-file-rows-advanced.md
prerequisite: PR-25 Shell FileDock + `queryFileRows` v1; PR-14a scan + `SqliteLibraryIndex.files`; PR-26 snapshot invalidation (no second pollers)
baseline_branch: merge PR-28 to main before implementation (see §0)
---

# 017 — queryFileRows Advanced / SQL Page Query

## Status

**Approved** (2026-06-02) — grill review blockers B1–B4 and G1–G4 incorporated below.

**Approval note:** Infrastructure never accepts raw bridge dicts (LOCK-29-13). Text sort/search uses persisted `*_key` columns (LOCK-29-14). Duplicate enrichment uses one-row-per-file projection from merged review cache (LOCK-29-15). UI ships search + header sort + load-more + `technical` preset only; filter chips deferred (LOCK-29-16).

**Scope sentence:** PR-29 moves production `queryFileRows` from **in-memory full-library scan** to **SQLite-backed paginated queries** on the existing `files` table (plus normalized key columns and a 1:1 review projection table), extends the bridge contract with optional sort/filters and a `technical` column preset, enforces deterministic sort + offset-cursor rules scoped to `libraryRevision`, and adds perf/parity gates for 10k-file libraries. **Only `ShellFileDock` consumes the API in PR-29** — no Work visible “all files” mode, no public `FileRowsProvider` React seam.

---

## 0. Program position

| Track | Item | Status |
|-------|------|--------|
| 002 | PR-26 snapshot invalidation | Done |
| 002 | PR-27 quality grid parity | Done |
| 002 | PR-28 settings/logs v1 | Implemented on feature branch; **merge to `main` before PR-29 implementation** |
| 002 | **PR-29** (this spec) | **Approved** (2026-06-02) |
| 002 | PR-30 bridge hygiene | Proposed — parallel rules §12 |

**Code reality (2026-06-02):** `SqliteLibraryIndex` already persists scanned files (`replace_files` on rescan). `LibrarySession.query_file_rows` still materializes **all** `FileRecord` rows in memory and filters via `application/file_query.py`. PR-29 changes the **query execution path**, not the existence of the SQLite `files` table.

---

## Locked decisions (brainstorming + scope gate — 2026-06-02)

### LOCK-29 — PR scope (verbatim)

```text
LOCK-29-1  ShellFileDock is the only UI consumer in PR-29.
LOCK-29-2  queryFileRows remains the single file-grid read API on the bridge.
LOCK-29-3  SQLite schema is an internal implementation detail; wire contract is FileRowsQuery/FileRowsPage only.
LOCK-29-4  No FileDock IA/layout redesign; no Work route changes.
LOCK-29-5  Sort whitelist + deterministic tie-break; invalid sort.field → bridge rejected.
LOCK-29-6  10k-file library query latency budgets (§8).
LOCK-29-7  v1 query fields remain backward compatible; advanced fields are optional.
LOCK-29-8  PR-29 keeps offset cursor wire format (stringified non-negative integer offset).
LOCK-29-9  Cursor stability is guaranteed only within the same libraryRevision and normalized query.
LOCK-29-10 Keyset cursor is explicitly deferred (not PR-29).
LOCK-29-11 No public React FileRowsProvider or Work “all files” visible mode in PR-29.
LOCK-29-12 Internal query helpers/adapters allowed; no new bridge methods beyond query_file_rows shape extensions.
LOCK-29-13 Infrastructure receives NormalizedFileRowsQuery, not raw bridge query dict.
LOCK-29-14 SQL text sort/search parity uses normalized *_key columns (NFC + casefold at ingest).
LOCK-29-15 File-row duplicate enrichment is one row per file_id via file_review_projection (merged review cache source).
LOCK-29-16 PR-29 UI ships search + header sort + load-more + technical preset only; filter chips deferred; bridge filters implemented + tested.
```

### PR-25 vs PR-29 boundary

| PR-25 (done) | PR-29 (this PR) |
|--------------|-----------------|
| `queryFileRows` v1: `search`, `preset`, `cursor`, `limit` | + `sort`, `filters`; `technical` preset |
| In-memory `query_file_page` on all files | Production path: `LibraryIndexPort.query_file_rows_page` → SQL |
| Offset cursor; path sort default | Whitelist sort; SQL `ORDER BY` + `id` tie-break |
| Dock fetch when expanded; first page only | Pagination UI (“Load more”) when `hasMore` |
| `duplicateGroupId` / `isKeeper` always null in mapper | Enriched via `file_review_projection` (§5.4, LOCK-29-15) |
| Index rebuild on rescan via `replace_files` | **Confirm** full rebuild policy; no incremental index in PR-29 |

---

## 1. Problem

`ShellFileDock` calls `bridge.queryFileRows` when expanded. Today Python builds a full row list from `_files_by_id` on every query. For libraries approaching **10k+ files**, this:

1. Allocates O(n) row dicts per query regardless of `limit`.
2. Cannot meet stable sort/filter/search at scale without loading the full library.
3. Leaves review signals (`duplicateGroupId`, `isKeeper`) unpopulated in file rows even though review state exists in SQLite.

PR-25 intentionally shipped v1 in-memory paging. PR-29 completes the backend path promised in [013 LOCK-B4](013-2026-06-02-shell-filedock-design.md) without expanding UI ownership beyond the shell dock.

---

## 2. Goals

1. **SQL production path:** `LibrarySession.query_file_rows` delegates to `LibraryIndexPort.query_file_rows_page` when the index is `SqliteLibraryIndex`.
2. **Contract extensions:** optional `sort` and `filters` on `FileRowsQuery`; `technical` preset; file-row `limit` max **500** (file queries only — review/quality limits stay 200).
3. **Deterministic ordering:** whitelist sort fields; SQL tie-break `id ASC` always applied after primary sort.
4. **Cursor rules:** offset cursor unchanged on wire; invalidate cursors when `libraryRevision` changes (UI resets to `cursor: null`).
5. **ShellFileDock UX:** header sort for mapped columns; `technical` preset; load-more pagination; reset page on sort/search/revision change (no filter chips — LOCK-29-16).
6. **Parity:** Python, mockBridge, and contract tests share sort/filter semantics; `file_query.py` remains reference + mock helper.
7. **Perf evidence:** contract tests for correctness; optional non-blocking perf smoke for §8 budgets.

---

## 3. Non-goals

- Work visible “전체 파일” mode or shared `FileRowsProvider` (defer PR-30+ / separate slice)
- FileDock IA redesign, column chooser per-column editor, AG Grid migration
- Keyset / seek cursors
- Incremental SQLite index updates on partial scans (full `replace_files` on successful rescan remains policy)
- Mutations from file grid (move/delete stay in Resolve)
- Replacing `queryReviewRows` / duplicate pipelines
- `queryLogEntries`, Settings, packaging changes
- Bridge facade extraction (PR-30)
- New pywebview method names (still `query_file_rows`)

---

## 4. Architecture

```text
ShellFileDock (only UI consumer)
  → bridge.queryFileRows(raw_query dict)
  → BridgeApi.query_file_rows(raw_query)
  → LibrarySession.query_file_rows(raw_query)
       → normalize_file_rows_query(raw_query) → NormalizedFileRowsQuery
  → LibraryIndexPort.query_file_rows_page(normalized)   # LOCK-29-13
  → SqliteLibraryIndex: SQL on files + 1:1 LEFT JOIN file_review_projection
  → map rows + pageInfo DTO
```

**Fallback:** In-memory `query_file_page` in `application/file_query.py` for:

- unit tests without SQLite
- mockBridge (must apply same sort/filter/cursor rules as SQL path)
- optional non-SQLite test doubles implementing `LibraryIndexPort`

**Forbidden:** Production pywebview path that rebuilds all rows from `_files_by_id.values()` per query after PR-29.

### 4.1 Layer ownership

| Layer | Responsibility |
|-------|----------------|
| `domain` | No change |
| `application` | `file_row_query.py`: `normalize_file_rows_query`, `NormalizedFileRowsQuery`, whitelist/errors; `LibrarySession` delegation |
| `application/ports/library_index.py` | `query_file_rows_page(normalized: NormalizedFileRowsQuery)` — **no raw dict** |
| `infrastructure/sqlite_library_index.py` | SQL on `files` + `file_review_projection`; `*_key` columns; indexes §8.2 |
| `app/bridge_api.py` | Pass-through; reject invalid query via application errors |
| `web/` | `FileRowsQuery` types, `ShellFileDock` sort/pagination/preset |

Internal private adapters are allowed (LOCK-29-12). No new public React provider.

### 4.2 Index rebuild policy

On **successful rescan** completion, existing `replace_files(folder, files)` clears and repopulates the `files` table for that folder — **full rebuild v1**. PR-29 does not add incremental file upserts.

**Normalized keys at ingest (LOCK-29-14):** when files are inserted/replaced, infrastructure stores:

| Column | Source |
|--------|--------|
| `name_key` | `casefold(NFC(name))` |
| `relative_path_key` | `casefold(NFC(relative_path))` |
| `extension_key` | `casefold(NFC(extension))` |
| `encoding_key` | `casefold(NFC(encoding_status or ""))` |

Python: `unicodedata.normalize("NFC", value).casefold()`. SQLite sorts/searches/filter text fields on `*_key` columns — **not** bare `LOWER(name)` on wire columns. mockBridge and in-memory fallback must use the same key function.

**Review projection (LOCK-29-15):** `file_review_projection` is rebuilt whenever `LibrarySession` refreshes `_review_rows_cache` (same lifecycle as Resolve grid data). It is the physical 1:1 enrichment source; query SQL must not multiply rows via ambiguous review-table JOINs.

---

### 4.3 `NormalizedFileRowsQuery` (LOCK-29-13)

Application-layer dataclass (names in plan), populated only by `normalize_file_rows_query(raw: dict)`:

- Validates sort whitelist, filter enums, cursor, limit clamp
- Raises application errors mapped to `INVALID_SORT_FIELD` / `INVALID_FILTER_VALUE`
- Carries normalized search term (for `*_key` / `LIKE`)
- **Never** passed through `BridgeApi` or pywebview as a new wire type — bridge remains `dict` in/out

Infrastructure and port methods accept **`NormalizedFileRowsQuery` only**.

---

## 5. Contract

### 5.1 TypeScript — `FileRowsQuery` (backward compatible)

```typescript
export type FileRowColumnPreset = "basic" | "review" | "technical";

export type FileRowSortField =
  | "name"
  | "path"
  | "extension"
  | "size"
  | "modifiedAt"
  | "encoding"
  | "duplicateGroup"
  | "integrity";

export interface FileRowsQuery {
  search?: string;
  preset?: FileRowColumnPreset;
  cursor?: string | null;
  limit?: number;

  sort?: {
    field: FileRowSortField;
    direction: "asc" | "desc";
  };

  filters?: {
    extension?: string[];
    encoding?: string[];
    duplicateGroup?: "any" | "none";
    integrity?: "ok" | "issue" | "unknown";
  };
}
```

`FileRowsPage` shape unchanged (`rows`, `pageInfo` with `cursor`, `nextCursor`, `hasMore`, `totalFiltered`).

### 5.2 Defaults (omitted fields)

| Field | Default |
|-------|---------|
| `sort` | `{ field: "path", direction: "asc" }` |
| `filters` | none |
| `cursor` | `null` → offset `0` |
| `limit` | `100` |
| `preset` | UI persists `basic` / `review` / `technical` — does not change server sort |

### 5.3 Sort whitelist and errors

- Valid `sort.field` values = LOCK-29 sort field set (§5.1).
- Unknown field → bridge **`rejected`** with reason **`INVALID_SORT_FIELD`** (mirror PR-27 quality grid).
- Text fields (`name`, `path`, `extension`, `encoding`): sort/search on `*_key` columns (LOCK-29-14).
- `duplicateGroup`, `integrity`: sort on projection / `encoding_key` as below; tie-break **`id ASC`** always appended.
- Numeric/time: `size` → `size_bytes`; `modifiedAt` → `modified_at_ns`.

### 5.4 Row enrichment (duplicate / keeper) — LOCK-29-15 Option C

**Cardinality rule:** each `file_id` appears **at most once** in a `queryFileRows` page. Enrichment must not use a live multi-table JOIN that can emit duplicate file rows when a file appears in multiple review memberships.

**Source of truth:** merged **`_review_rows_cache`** member rows (`rowKind == "file"`), not raw duplicate graph tables at query time.

**Projection build** (on every review-cache rebuild):

1. Scan member rows from `_review_rows_cache` only.
2. For each `file_id`, keep **one** winning row by priority: `type` **exact** > **near** > **relation**, then `groupId` ASC.
3. Set `duplicateGroupId` = winning `groupId`; `isKeeper` = member row’s keeper semantics (same as review grid: keeper if `proposedAction == "keep"` or equivalent locked field in plan).

**Persistence:** `file_review_projection` table:

```text
PRIMARY KEY (folder_path, file_id)
duplicate_group_id TEXT NULL
is_keeper INTEGER NOT NULL DEFAULT 0
duplicate_group_key TEXT NULL   -- casefold(NFC(duplicate_group_id)) for sort; NULL when no group
```

Replaced atomically when projection rebuild runs (same transaction as cache refresh when possible).

**Query SQL:** `files` LEFT JOIN `file_review_projection` ON `files.id = file_review_projection.file_id` AND matching `folder_path` — **1:1**, safe cardinality.

If no projection row, `duplicateGroupId` null and `isKeeper` false.

| Field | Source |
|-------|--------|
| Core file metadata | `files` |
| `duplicateGroupId` | `file_review_projection.duplicate_group_id` |
| `isKeeper` | `file_review_projection.is_keeper` |
| `integrityStatus` | `files.encoding_status` (wire unchanged) |

### 5.5 Filters (server-side)

| Filter | Semantics |
|--------|-----------|
| `extension` | Match `extension_key` against casefolded filter values; OR |
| `encoding` | Match `encoding_key` against casefolded filter values |
| `duplicateGroup: "any"` | `duplicate_group_id` IS NOT NULL |
| `duplicateGroup: "none"` | `duplicate_group_id` IS NULL |
| `integrity: "ok"` | §5.5.1 ok set |
| `integrity: "issue"` | §5.5.1 issue set |
| `integrity: "unknown"` | §5.5.1 unknown set |

Invalid filter enum → **`INVALID_FILTER_VALUE`** (new reason; add to bridge parity tests).

`search` (existing): substring match on `name_key`, `relative_path_key`, `extension_key` (SQL `LIKE` with escaped `%`/`_`, pattern uses casefolded term).

#### 5.5.1 Integrity filter sets (G2 — locked in spec)

| Filter | `encoding_status` rule |
|--------|-------------------------|
| **ok** | `utf-8` or `ascii` (case-insensitive) |
| **unknown** | `NULL` or empty string |
| **issue** | any other non-empty value |

Sort field `integrity` uses `encoding_key` (same ordering as filter buckets).

### 5.6 Cursor (offset wire)

- `cursor` is a stringified non-negative integer offset into the **filtered, sorted** result set.
- `nextCursor` = `str(offset + len(rows))` when `hasMore`; else `null`.
- **LOCK-29-9:** If `libraryRevision` changes, clients MUST discard accumulated rows and query with `cursor: null`. ShellFileDock listens to `snapshot.work.resolve.libraryRevision` (existing) and resets pagination state.
- Malformed `cursor` → treat as `0` (match v1 `_parse_cursor` behavior).

### 5.7 Limit clamp

| Query API | Max `limit` |
|-----------|-------------|
| `queryFileRows` | **500** |
| `queryReviewRows` / `queryQualityRows` | **200** (unchanged) |

Update `web/src/contracts/fileRowsPageContract.ts` and Python file-row clamp to **500** without changing review/quality clamps.

### 5.8 Preset `technical`

Display-only column layout in `shellFileDockColumns.ts` (no server-side preset logic except passthrough for mock parity):

| Column | Field |
|--------|-------|
| 파일명 | `name` |
| 경로 | `path` |
| 확장자 | `extension` |
| 인코딩 | map from `integrityStatus` / encoding |
| 속성 | `—` (silent placeholder; no tooltip copy) |
| 수정일 | `modifiedAt` |

**G3:** “속성” shows `—` only — no “not available yet” tooltip or helper text.

### 5.9 v1 → advanced diff table (plan must copy)

| v1 | PR-29 advanced |
|----|----------------|
| In-memory all files | SQLite `query_file_rows_page` |
| `search`, `preset`, `cursor`, `limit` | + `sort`, `filters` |
| `basic` \| `review` presets | + `technical` |
| max limit 200 | max limit **500** (file rows only) |
| path sort only | whitelist sort |
| first page only in UI | load-more pagination |
| `duplicateGroupId` null | `file_review_projection` 1:1 |

---

## 6. UI — ShellFileDock only (LOCK-29-1)

### 6.1 In scope

- Add **`technical`** to preset `<select>`.
- **Column header sort:** clicking a sortable header toggles asc/desc for the mapped `FileRowSortField`; triggers `queryFileRows` with `cursor: null` and replaces rows.
- **Load more:** when `pageInfo.hasMore`, footer button fetches with `cursor: pageInfo.nextCursor` and **appends** rows (same normalized query + sort + filters + search).
- On `debouncedSearch`, `sort`, or `libraryRevision` change → reset to `cursor: null`, replace rows.
- **LOCK-29-16:** No filter chips / filter toolbar in PR-29 UI. Bridge `filters` contract is implemented and covered by contract tests; ShellFileDock does not send `filters` in v1 UI.

### 6.2 Out of scope

- Work route changes, `FileRowsProvider`, second dock
- VirtualizedDataGrid migration for dock (may remain HTML `<table>` with pagination; no full-library DOM load)
- Per-column chooser / resize editor

### 6.3 Column id → sort field map

| Header `col.id` | `sort.field` |
|-----------------|--------------|
| `name` | `name` |
| `path` | `path` |
| `size` | `size` |
| `modified` | `modifiedAt` |
| `dup` | `duplicateGroup` |
| `integrity` | `integrity` |
| `extension` (technical) | `extension` |

Non-sortable columns: no click handler.

---

## 7. Python / bridge errors

| Reason | When |
|--------|------|
| `INVALID_SORT_FIELD` | Unknown `sort.field` |
| `INVALID_FILTER_VALUE` | Unknown filter enum or malformed filter payload |
| (existing) | Library not scanned → empty page per v1 |

Bridge returns standard rejected dict; TS `parseBridgeRejection` extended for `INVALID_FILTER_VALUE`.

---

## 8. Performance gates

Targets on dev hardware, **10k files** in SQLite, single-folder library, warm connection:

| Scenario | p95 budget |
|----------|------------|
| Initial page (`cursor=null`, default sort) | ≤ **150 ms** |
| Search page | ≤ **250 ms** |
| Sort change page | ≤ **250 ms** |

**Enforcement:**

- **Contract tests (blocking):** deterministic ordering, cursor math, filter/sort rejection, `*_key` parity, projection cardinality (one row per file), Python vs mock for small fixtures.
- **Perf smoke (G4 — non-blocking in CI):** scripted 10k insert + timed queries; **must** appear in plan local verification checklist; failures warn, do not weaken contract tests.

### 8.2 SQLite indexes (B4 — plan must apply)

On `files` (include `id` for tie-break seek):

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
```

On `file_review_projection`:

```sql
CREATE INDEX IF NOT EXISTS idx_file_review_folder_group_key_id
  ON file_review_projection(folder_path, duplicate_group_key, file_id);
```

**Join sort caveat:** `duplicateGroup` sort/filter uses `file_review_projection` LEFT JOIN. Simple `files` indexes alone do not guarantee join-sort budgets — **§8 p95 targets for `duplicateGroup` sort are validated by perf smoke, not assumed from files indexes alone.**

---

## 9. Tests (no new files without `TEST_ALLOWED`)

Extend existing:

| File | Coverage |
|------|----------|
| `tests/test_bridge_contract.py` | SQL path sort, filter, cursor, `INVALID_*`, 10k smoke optional |
| `web/src/bridge/bridgeParity.test.ts` | mock sort/filter parity |
| `web/e2e/smoke.spec.ts` | dock expanded → sort header → load more (minimal) |

Characterization of v1 empty-library shape must remain green.

---

## 10. Acceptance criteria

PR-29 is complete when:

1. Production `query_file_rows` uses SQL page query (no full-library materialization).
2. `ShellFileDock` is the only consumer; Work unchanged.
3. Sort whitelist enforced; invalid field rejected.
4. Offset cursor + LOCK-29-9 revision reset behavior tested.
5. `technical` preset available; v1 `basic`/`review` regression-free.
6. Load-more pagination works for 10k library without loading all rows into DOM.
7. `duplicateGroupId` / `isKeeper` populated when review state exists.
8. `verify_phase_completion.py` PASS; dock-related contract/E2E per plan.
9. mockBridge + Python parity on sort/filter/search for shared fixtures.

---

## 11. Grill-me resolutions (2026-06-02)

| # | Resolution |
|---|------------|
| **G1** | **Bridge-only for filters in UI** — contract + tests yes; ShellFileDock filter chips **deferred** (LOCK-29-16) |
| **G2** | Integrity sets locked in §5.5.1 (`ok` = utf-8/ascii; `unknown` = null/empty; else `issue`) |
| **G3** | Technical “속성” = silent `—` |
| **G4** | Perf smoke **non-blocking in CI**; **required** on plan local verification checklist |

### Grill blockers incorporated

| ID | Fix |
|----|-----|
| **B1** | LOCK-29-13 + §4.3 `NormalizedFileRowsQuery` |
| **B2** | LOCK-29-14 + `*_key` columns §4.2 |
| **B3** | LOCK-29-15 Option C + §5.4 projection |
| **B4** | §8.2 indexes + join-sort caveat |

---

## 12. PR-30 parallel work (roadmap + spec 018 note)

PR-30 may start in parallel **only if all** hold:

```text
- Characterization tests planned before extraction
- Facade skeleton only (no move/apply path moves)
- No JSON / pywebview method / semantic change
- No queryFileRows ownership change
- No BridgeApi surgery before PR-29 spec approval
```

Provider seam or Work file-grid consumer expansion is **out of PR-30** unless a new spec cycle opens.

---

## 13. References

- [013 Shell FileDock](013-2026-06-02-shell-filedock-design.md) — LOCK-B4, presets, PR-29 boundary
- [002 PR-26..30 roadmap](../roadmap/002-2026-06-02-pr26-pr30-platform-polish-roadmap.md)
- [015 Quality grid parity](015-2026-06-02-quality-grid-parity-design.md) — sort rejection pattern
- `src/infrastructure/sqlite_library_index.py` — existing `files` table
- `src/application/file_query.py` — v1 in-memory reference

---

## Changelog

| Date | Change |
|------|--------|
| 2026-06-02 | Initial draft from brainstorming; consumer scope A; SQL path; offset cursor; PR-30 parallel note |
| 2026-06-02 | Grill review: approved; LOCK-29-13..16; NormalizedFileRowsQuery; *_key columns; file_review_projection; integrity sets; index DDL; UI filter chips deferred |
