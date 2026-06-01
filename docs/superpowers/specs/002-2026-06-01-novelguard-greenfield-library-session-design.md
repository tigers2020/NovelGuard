---
title: PR-14 Greenfield Real Library Session v1
status: approved
date: 2026-06-01
authors: brainstorming (application architecture + bridge + UI)
parent_spec: docs/superpowers/specs/00-2026-06-01-novelguard-ui-overhaul-design.md
related_spec: docs/superpowers/specs/01-2026-06-01-pr13-preview-token-stale-apply-design.md
pr_label: PR-14
---

# PR-14 — Greenfield Real Library Session v1

## Status

**Approved** (2026-06-01) — B-Strict greenfield; B2 layer layout; 14a in-memory index, 14b+ SQLite. Implementation plan: `docs/superpowers/plans/` (to be written via `writing-plans`).

## Scope sentence

This cycle connects `pywebview` `BridgeApi` to a **new** Python library stack (`LibrarySession` + domain/application/infrastructure). It returns **real** scan summaries, review rows, and quality rows through the **existing** PR-10~13 React/Bridge DTO contracts. It does **not** restore or adapt legacy code from pre-reset commits, and it does **not** perform filesystem move/delete.

## Implementation authority

```text
The only implementation authority for this cycle is the current PR-10~13 React/Bridge DTO contract.

TypeScript sources of truth:
- web/src/types/snapshot.ts
- web/src/types/review.ts
- web/src/types/quality.ts
- web/src/types/selection.ts
- web/src/types/movePreview.ts
- web/src/contracts/*
- web/src/bridge/NovelGuardBridge.ts

Python validators:
- src/app/bridge_contract.py
```

## Non-authoritative legacy

The pre-reset commit `c6bda5f` is **not** an implementation source for this cycle.

- No files, schemas, DTOs, Qt view models, workers, repositories, or use cases may be **restored** from it.
- No legacy module may be **imported** or **adapted** as implementation.
- Legacy behavior may appear only in migration notes as **background**, not as acceptance criteria.

Historical inventories (WorkTab, `DuplicateViewModel`, `FileSystemScanner`, etc.) describe a **prior** architecture. They do not override this spec.

## Not in scope (naming)

- **PR-14 packaging** (installer, production `run.bat` polish) — deferred to a later cycle.
- **DESIGN.md** color/spacing tokens — unrelated.
- **Preview token** in this document means PR-13 **preview–apply correlation id**, not UI theme tokens.

## Summary

PR-0..13 delivered the React Work UI, bridge contracts, virtualized grids, E2E smoke, and preview-token/stale-apply guards. `BridgeApi` and `mockBridge` still serve **synthetic** library data.

PR-14 adds a **greenfield** backend read path:

| Capability | v1 behavior |
|------------|-------------|
| Folder selection | Real path persisted in session |
| Scan | Real filesystem walk + index build |
| Snapshot | Aggregates from real index |
| Review grid | Exact duplicate rows only |
| Quality grid | Analysis-only issues |
| Move preview / apply | PR-13 guards preserved; **apply remains no-op** |

`mockBridge` stays **browser dev-only**. `BridgeApi` delegates to `LibrarySession` only.

## Parent spec alignment

Extends [00-2026-06-01-novelguard-ui-overhaul-design.md](./00-2026-06-01-novelguard-ui-overhaul-design.md):

- Snapshot remains **summary-only** (no row arrays on `AppSnapshot`).
- Queries remain paginated (`limit` ≤ 200).
- Destructive UX path unchanged; **no real FS mutation** in PR-14.

Preserves [01-2026-06-01-pr13-preview-token-stale-apply-design.md](./01-2026-06-01-pr13-preview-token-stale-apply-design.md):

- `libraryRevision`, `previewToken`, `selectionFingerprint`, `discardMovePreview` semantics unchanged.
- `applyResolvedActions` stays **no-op** at filesystem level.

Does **not** change: React component layout, grid stack, `mockBridge` dev role, PR-10 validator rules (except data source behind valid payloads).

---

## PR-14a exception (bridge boundary)

```text
PR-14a exception:
PR-13 preview/apply guard state remains in app.BridgeApi temporarily because it is
bridge-lifecycle state, not domain scan/index logic. PR-14d will re-evaluate whether
to extract it into an app-layer helper.
```

`LibrarySession` owns scan, index, and snapshot mapping. `BridgeApi` still holds `_pending_apply` and preview-token validation for PR-13 compatibility.

---

## Locked decisions

| Decision | Value |
|----------|--------|
| Strategy | **B-Strict greenfield** — no legacy restore/adapt |
| Layer layout | **B2** — `domain` / `application` / `infrastructure` / `app` |
| Orchestration | `application.library_session.LibrarySession` |
| Bridge surface | `app.bridge_api.BridgeApi` — **thin delegation only** |
| Scan command name | **`startScan` / `start_scan` only** — `startPipeline` forbidden |
| Dev bridge | `mockBridge` — browser-only; unchanged contract |
| Duplicate v1 | **Exact only** (size → SHA-256 → groups) |
| Near/relation duplicate | **Out of scope** |
| Quality v1 | **Analysis only** — no UTF-8 conversion |
| Apply | PR-13 token guards + **no-op** FS |
| FS move/delete | **Forbidden** this cycle |
| 14a storage | **In-memory** `LibraryIndex` (implementation detail) |
| 14b+ storage | **SQLite** behind same port interface |
| Storage abstraction | Public Bridge DTOs **must not** expose in-memory vs SQLite |
| PR split | **Phased greenfield** 14a → 14b → 14c → 14d (not phased restore) |
| Tests | Extend **existing** files; no new test files without `TEST_ALLOWED` |

### Storage contract note

```text
14a may use an in-memory LibraryIndex only as an implementation detail.
The public Bridge DTO contract must not expose whether the backing index is in-memory or SQLite.
```

`application` depends on a port (e.g. `LibraryIndexPort`), not on SQLite directly. `infrastructure.library_index` provides in-memory (14a) and SQLite (14b) implementations.

---

## Architecture

### Layer responsibilities

```text
src/
  domain/
    models.py                 # FileRecord, DuplicateGroup, QualityIssue (pure data)
    duplicate_exact.py        # size bucket + sha256 grouping (pure)
    quality_rules.py          # empty / small / unreadable / decode rules (pure)
  application/
    library_session.py        # scan lifecycle, revision, orchestration
    dto_mapper.py             # internal models → PR-10 bridge dicts
    ports/
      library_index.py        # protocol: load/save/query aggregates
  infrastructure/
    filesystem_scanner.py     # walk folder, hash files (I/O)
    memory_library_index.py   # PR-14a
    sqlite_library_index.py   # PR-14b+
  app/
    bridge_api.py             # pywebview js_api — validate + delegate
    bridge_contract.py        # existing validators (unchanged rules)
    selection_fingerprint.py  # PR-13 (unchanged)
```

### Dependency rules (AGENTS.md)

- `domain` — no I/O, no imports from `application` / `infrastructure` / `app`.
- `application` — orchestrates domain + ports; no pywebview, no SQLite imports.
- `infrastructure` — implements ports; no business policy beyond adapters.
- `app` — wires session + `BridgeApi`; no duplicate-detection logic in `bridge_api.py`.

### `LibrarySession` (application)

Single session per `BridgeApi` instance (desktop process lifetime).

```text
LibrarySession
├── select_folder(path: str | None = None)   # native picker when path omitted
├── start_scan(options: dict | None = None)
├── cancel_run()
├── set_work_mode(mode: str)
├── get_snapshot() -> dict                     # AppSnapshot-shaped
├── query_review_rows(query: dict) -> dict     # ReviewRowsPage-shaped
├── query_quality_rows(query: dict) -> dict
├── get_duplicate_group_detail(group_id: str) -> dict
├── get_quality_issue_detail(issue_id: str) -> dict
├── get_move_preview(selection: dict) -> dict  # delegates PR-13 logic + real row ids
├── apply_resolved_actions(payload: dict) -> None
└── discard_move_preview(payload: dict) -> None
```

`BridgeApi` methods call `LibrarySession`, then `bridge_contract.validate_*` on responses (same as today).

### Scan lifecycle

1. **`select_folder`** — persist `library.folderPath`; reset or mark index stale; bump `libraryRevision` when folder changes.
2. **`start_scan`** — set `pipeline.phase = "scan"`, `work.scan.state = "running"`; run scan on **background thread** (do not block pywebview UI thread).
3. **Progress** — update `pipeline.percent` / `label` during scan; UI polls `get_snapshot()` (~1 Hz while running, per parent spec).
4. **Complete** — rebuild index; run exact duplicate detection; run quality analysis; set `work.scan.state = "success"`; `pipeline.phase = "idle"`; bump `libraryRevision`.
5. **`cancel_run`** — cooperative cancel flag; return pipeline to idle; partial index discarded or marked incomplete (implementation choice — must not return inconsistent duplicate counts).

### `libraryRevision`

Monotonic `number` on `ResolveSnapshot`:

- Increment on: folder change, scan success, duplicate recompute (if ever triggered without full scan).
- PR-13 stale preview / selection fingerprint behavior unchanged.

---

## Scanner v1 (`infrastructure/filesystem_scanner.py`)

### Target extensions

| Extension | Default |
|-----------|---------|
| `.txt` | **Included** |
| `.md` | **Included** |
| `.csv`, `.json` | Optional via `start_scan` options (e.g. `includeStructured: true`) |

Respect `scanOptions` strings on snapshot when UI passes them (mirror mock labels where possible: subfolders, hidden files — implement incrementally in 14a if costly; **minimum 14a**: recursive walk, skip hidden dotfiles).

### `FileRecord` (domain)

```python
# conceptual — exact field names may use snake_case internally; DTO mapper owns camelCase bridge output
FileRecord:
  id: str              # stable uuid or hash-based id for session
  path: str            # absolute or library-relative (pick one; document in plan)
  name: str
  size_bytes: int
  modified_at: str     # ISO-8601 local or UTC — consistent in mapper
  extension: str
  sha256: str | None   # None until hashed; required before duplicate grouping
  encoding_status: str | None  # e.g. "utf-8", "unknown", "error"
```

### Hashing

- SHA-256 file content for duplicate grouping (14b; may defer hashing to post-walk batch in 14a if needed for perf — plan must state).
- Large files: stream hash; no full-file load into memory.

---

## Duplicate detection v1 (`domain/duplicate_exact.py`)

**Exact duplicate only.**

```text
1. Group files by size_bytes
2. Within size groups, group by sha256
3. Keep groups with count >= 2
4. Emit ReviewRow list (see mapping below)
```

**Out of scope:** near duplicate, relation/containment, filename blocking, keeper scoring policies from legacy stack.

### Review row mapping

Map each duplicate group to one or more `ReviewRow` objects compatible with `web/src/types/review.ts`:

| Row | Fields |
|-----|--------|
| Group header | `rowKind: "group"`, `hasChildren: true`, `groupId`, `type: "exact"`, `status: "unreviewed"`, `name` = representative filename, `proposedAction: "keep"` |
| Member file | `rowKind: "file"`, `groupId`, `type: "exact"`, `status: "unreviewed"`, `name`, `path`, `sizeBytes`, `keeperLabel` = chosen keeper candidate name, `proposedAction: "keep"` \| `"move_duplicate"` |

**Keeper v1:** largest file in group, tie-break by lexicographic path.

**v1 user review state:** all rows `"unreviewed"`; `approved` / `conflict` counts in page summary may be zero until a future PR.

**Filtered types:** If query `filters.types` includes only `near` / `relation` / `move_only`, return **empty** `rows` with valid `pageInfo` (not an error).

### Query semantics

Reimplement filter/sort/pagination semantics compatible with browser `mockBridge` / `mockData.ts` behavior:

- `viewMode`: `action` \| `groups` \| `move` \| `all` \| `conflicts`
- `filters.status`, `filters.types`, `filters.search`
- `sort.field`, `sort.direction`
- `cursor`: opaque offset string (`"0"`, `"100"`, …) — same convention as mock
- `limit`: default 100, max 200 (`bridge_contract.clamp_query_limit`)

**Do not copy** legacy `duplicate_page_builder` code; behavior is defined by this spec + TS contract tests.

---

## Quality analysis v1 (`domain/quality_rules.py`)

Analysis only — **no** repair, conversion, or delete.

| Internal rule | Maps to `QualityIssueType` | Typical `severity` |
|---------------|---------------------------|-------------------|
| `empty_file` (size 0) | `small_file` | `error` |
| `very_small_file` (< threshold, e.g. 512 bytes) | `small_file` | `warning` |
| `decode_error` | `encoding` | `error` |
| `unreadable_file` (IO/OS) | `integrity` | `error` |

`QualityRow` fields per `web/src/types/quality.ts`. `suggestedAction` is descriptive text only (e.g. `"Review manually"`).

`get_quality_issue_detail` returns `QualityIssueDetail` with optional `evidence` dict (paths, sizes, exception message).

---

## Bridge methods (unchanged surface)

| TS (camelCase) | Python (snake_case) | PR-14 deliverable |
|----------------|---------------------|-------------------|
| `getSnapshot` | `get_snapshot` | Real aggregates (14a+) |
| `selectFolder` | `select_folder` | Real picker + path (14a) |
| `startScan` | `start_scan` | Real scan (14a) — **`startPipeline` forbidden** |
| `cancelRun` | `cancel_run` | Cooperative cancel (14a) |
| `setWorkMode` | `set_work_mode` | Session mode (14a) |
| `queryReviewRows` | `query_review_rows` | Real exact duplicates (14b) |
| `queryQualityRows` | `query_quality_rows` | Real issues (14c) |
| `getDuplicateGroupDetail` | `get_duplicate_group_detail` | Minimal real detail (14b) |
| `getQualityIssueDetail` | `get_quality_issue_detail` | Real detail (14c) |
| `getMovePreview` | `get_move_preview` | PR-13 + real row ids (14d) |
| `applyResolvedActions` | `apply_resolved_actions` | PR-13 guards; **no-op** (14d) |
| `discardMovePreview` | `discard_move_preview` | PR-13 idempotent (14d) |

`connection` string on snapshot should distinguish real session, e.g. `"Library session (Python)"` vs mock `"Bridge ready (mock)"`.

### Folder picker (14a)

Use a native dialog when `select_folder()` is called without a path:

- Preferred: `tkinter.filedialog` on Windows (pywebview desktop target).
- Test/CI: allow injecting path via `LibrarySession.select_folder(path)` from pytest.

Cancel picker → no-op (folder unchanged).

---

## PR-14 phased delivery (greenfield, not restore)

| Phase | Scope | FS mutation |
|-------|--------|-------------|
| **PR-14a** | `LibrarySession` + in-memory index + real `select_folder` / `start_scan` / `cancel_run` / `get_snapshot` | No |
| **PR-14b** | SQLite `LibraryIndex` + exact duplicate + `query_review_rows` + `get_duplicate_group_detail` | No |
| **PR-14c** | Quality analyzer + `query_quality_rows` + `get_quality_issue_detail` | No |
| **PR-14d** | Contract parity, pytest on real temp dirs, E2E hooks for revision bump; PR-13 apply no-op verified against real ids | No |

Each phase must pass `python scripts/verify_phase_completion.py` before merge.

**Plan scope freeze:** Complete 14a–14d only. No packaging PR, no real apply, no near-duplicate, no FileDock.

---

## Preview / apply (PR-13 carry-forward)

- `get_move_preview` must reference **real** `ReviewRow.id` values when session has data.
- `apply_resolved_actions` clears pending state per PR-13 but performs **no** filesystem move/delete.
- `discard_move_preview` remains idempotent lifecycle cleanup.
- All `PreviewApplyErrorCode` paths remain test-covered.

---

## Testing policy

| Layer | Approach |
|-------|----------|
| Python | Extend `tests/test_bridge_contract.py` with temp-dir fixtures (small `.txt` sets) |
| TS contracts | Unchanged validators; optional fixture tweaks for real-shaped payloads |
| E2E | `mockBridge` remains default for CI; real-bridge E2E optional behind env flag in **plan** only |
| New files | Require user `TEST_ALLOWED` — prefer extending existing modules |

Minimum contract tests for 14b:

- Scan folder → `fileCount` > 0
- Duplicate fixture → `query_review_rows` returns `type: "exact"` only
- `libraryRevision` increases after scan

---

## Acceptance criteria

```text
✓ No imports from c6bda5f-restored modules
✓ domain / application / infrastructure / app layer boundaries respected
✓ BridgeApi contains no business logic (delegation + validate only)
✓ get_snapshot returns validated AppSnapshot from real index (14a+)
✓ start_scan performs real filesystem walk (14a)
✓ query_review_rows returns exact duplicate rows only (14b)
✓ query_quality_rows returns mapped QualityRow issues (14c)
✓ limit ≤ 200 enforced; no unbounded arrays on snapshot
✓ mockBridge unchanged for browser dev
✓ applyResolvedActions remains no-op at FS level
✓ PR-13 preview token / stale / discard behavior preserved (14d)
✓ verify_phase_completion.py passes at each phase merge
```

---

## Out of scope (explicit)

- Restoring or adapting `c6bda5f` code
- Near / relation duplicate detection
- Real move / delete / organize-by-chosung apply
- UTF-8 batch conversion
- Finalize / repair pipeline
- PR-14 **packaging** (installer, signed build)
- FileDock v2, column persist, Python bridge sort optimization
- `queryFileRows` / all-files grid (unless already in bridge parity — defer unless UI requires)
- AG Grid migration
- UI layout / DESIGN token sweep

---

## Approval checklist

- [x] B-Strict greenfield (no legacy restore)
- [x] B2 layer layout (`domain` / `application` / `infrastructure`)
- [x] 14a in-memory → 14b SQLite; storage not exposed in DTOs
- [x] `LibrarySession` orchestration; thin `BridgeApi`
- [x] Exact duplicate only; quality analysis only
- [x] PR-13 apply no-op preserved
- [x] `startScan` naming; `mockBridge` dev-only
- [x] Phased 14a–14d greenfield split

---

## Changelog

| Date | Change |
|------|--------|
| 2026-06-01 | Initial spec from brainstorming; B-Strict + B2 + storage note approved |
