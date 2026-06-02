# PR-19: Near Duplicate Detection — Implementation Plan

> **For agentic workers:** Use superpowers:subagent-driven-development or superpowers:executing-plans. Track steps with `- [ ]` checkboxes.

**Goal:** Ship deterministic near-duplicate candidate detection (post-scan), SQLite results-only persistence, merged `queryReviewRows` / `getDuplicateGroupDetail` for near groups, Resolve UI near filter/badge, and hard apply rejection — without changing exact duplicate or apply safety behavior.

**Architecture:** Pure detector in `domain/duplicate_near.py`. Application orchestrates text read (reuse scan read pattern from `quality_analyzer`), builds `exact_group_by_file_id` map from `find_exact_duplicate_groups`, runs detector, replaces SQLite near tables, merges near rows into `_review_rows_cache` via `build_near_review_rows` + PR-17 merge. Bridge validators extended; no new bridge methods. Near phase wrapped in try/except inside `LibrarySession._run_scan` success path — **non-fatal**.

**Tech Stack:** Python 3.12, SQLite (`SqliteLibraryIndex._SCHEMA`), React + TypeScript, pytest + Vitest (extend existing files only).

**Spec:** [007-2026-06-01-near-duplicate-detection-design.md](../specs/007-2026-06-01-near-duplicate-detection-design.md) (**approved** 2026-06-01)

**Plan status:** **Implemented** (2026-06-01) — Tasks 1–10 complete; verification PASS (64 pytest).

**Parent:** [000 master roadmap](../roadmap/000-2026-06-01-novelguard-master-roadmap.md) — Wave C PR-19

**Depends on:** PR-14b (exact rows), PR-17 (review state), PR-18 (detail panel), PR-15/16 (apply path — must remain exact-only)

**Test policy:** No new `test_*.py` / `*.test.tsx` without `TEST_ALLOWED`. Extend:

- `tests/test_bridge_contract.py`
- `web/src/bridge/bridgeParity.test.ts`
- `web/src/bridge/mockBridge.ts` (+ optional `mockNearDuplicate.ts` helper module **only if** mockBridge file size warrants split — prefer single file unless > ~80 lines added)

---

## Plan-locked decisions (from Spec 007 + grill-me)

| Lock | Value |
|------|--------|
| Scope | Near detection only — **no** PR-20 relation/filename-blocking |
| Scan timing | **Post-scan phase** after `_rebuild_review_index` + `_rebuild_quality_index` on successful scan |
| Near failure | **Non-fatal** — log; exact rows remain; near cache empty for failed run |
| Fingerprints | **Transient** in process memory only |
| SQLite | **Results-only** — groups, members, pairs; **no** fingerprint blob columns |
| `near_batch_id` | Namespace only — not general scan-session architecture |
| Group id | `near:<nearBatchId>:<clusterIndex>` |
| Row ids | `group:near:<nearBatchId>:<clusterIndex>`, `file:near:<nearBatchId>:<clusterIndex>:<fileId>` |
| Row type | `ReviewRow.type = "near"` (existing TS union) |
| Detail evidence | `evidence.matchKind = "near_ngram_v1"`; `DuplicateGroupDetailOk.type = "near"` |
| Algorithm constant | `ALGORITHM_VERSION = "near-ngram-v1"` |
| Threshold | `NEAR_DUP_THRESHOLD = 0.82` |
| Default query | **Exact-only** — fix `review_query._filter_rows` hard drop of non-exact |
| Type filter | `filters.types`: `["exact"]` → exact only; `["near"]` → near only; both → union |
| Exact edge skip | Skip near pair only when **both** files share same exact `dup-*` group |
| Apply | UI disable + backend **`PreviewApplyError("NEAR_DUPLICATE_APPLY_UNSUPPORTED")`** |
| Mixed selection | **Reject whole** preview/apply — no partial exact apply |
| Review DB | **Shared** `review_group_state` / `review_member_state` — prune includes near group ids |
| Near row actions | `proposedAction: "ignore"` on file rows; group header `proposedAction: "keep"` |
| APIs | Extend `queryReviewRows`, `getDuplicateGroupDetail` only |

---

## File map

| File | Action |
|------|--------|
| `src/domain/duplicate_near.py` | **Create** — normalization, fingerprint, score, cluster |
| `src/domain/near_duplicate_models.py` | **Create** (optional) — dataclasses if `duplicate_near.py` grows; else keep in same file |
| `src/application/near_batch_id.py` | **Create** — `make_near_batch_id`, `content_set_digest` |
| `src/application/near_text_reader.py` | **Create** — eligible extensions + UTF-8 read (mirror `quality_analyzer` `read_bytes`) |
| `src/application/near_duplicate_detect.py` | **Create** — orchestrate inputs → `find_near_duplicate_groups` |
| `src/application/near_review_rows_builder.py` | **Create** — `build_near_review_rows` |
| `src/application/near_group_detail.py` | **Create** — `build_near_group_detail` from SQLite + review cache |
| `src/application/duplicate_group_detail.py` | **Modify** — dispatch exact vs near by `groupId` prefix |
| `src/application/review_query.py` | **Modify** — type filter semantics; default exact-only |
| `src/application/library_session.py` | **Modify** — post-scan near phase; merge near rows into cache |
| `src/application/ports/library_index.py` | **Modify** — near table port methods |
| `src/infrastructure/sqlite_library_index.py` | **Modify** — schema + `replace_near_duplicate_results` / load helpers |
| `src/infrastructure/memory_library_index.py` | **Modify** — in-memory near store for tests |
| `src/app/build_preview_plan.py` | **Modify** — reject near rows early |
| `src/app/apply_resolved_actions.py` | **Modify** — defensive reject near in resolved selection |
| `src/app/bridge_contract.py` | **Modify** — near detail validation; `near_ngram_v1` |
| `src/app/bridge_api.py` | **Modify** — map `NEAR_DUPLICATE_APPLY_UNSUPPORTED` if needed |
| `web/src/types/review.ts` | **Modify** — `DuplicateMatchKind`, near detail variant |
| `web/src/types/movePreview.ts` | **Modify** — add `NEAR_DUPLICATE_APPLY_UNSUPPORTED` to `PreviewApplyErrorCode` |
| `web/src/features/work/ResolveAndOrganizeWorkspace.tsx` | **Modify** — type filter toggle; apply disabled |
| `web/src/features/work/resolve/FacetPanel.tsx` or new `TypeFilterBar.tsx` | **Modify** — exact / near / all filter (minimal) |
| `web/src/features/work/resolve/DetailPanel.tsx` | **Modify** — near evidence label |
| `web/src/features/work/ApplySubflowDialog.tsx` | **Modify** — respect disabled apply for near selection |
| `web/src/bridge/mockBridge.ts` | **Modify** — synthetic near rows + detail |
| `tests/test_bridge_contract.py` | **Modify** — domain, SQLite, query, detail, apply rejection |

---

## Task 0: Plan gate checklist

- [ ] Human approves this plan (status → **Approved**).
- [ ] Spec 007 remains **approved** — no open grill-me items.
- [ ] Do **not** start implementation until both gates pass.

---

## Task 1: Domain near detector

**Files:** `src/domain/duplicate_near.py`

- [ ] **Step 1:** Add constants:

```python
ALGORITHM_VERSION = "near-ngram-v1"
NEAR_DUP_THRESHOLD = 0.82
MIN_NORMALIZED_CHARS = 200
MAX_NORMALIZED_CHARS = 512 * 1024
LENGTH_RATIO_THRESHOLD = 0.60
WORD_NGRAM_SIZE = 5
CHAR_NGRAM_SIZE = 5
MAX_FINGERPRINTS_PER_FILE = 512
```

- [ ] **Step 2:** Implement `normalize_text_for_near_dup(text: str) -> str` (NFKC, lower, whitespace, LF).

- [ ] **Step 3:** Implement stable fingerprint id: SHA-256 gram → truncate 64-bit int or 16-char hex (document choice in module docstring).

- [ ] **Step 4:** Implement `fingerprint_set(normalized: str) -> frozenset[str]` with word n-gram + char fallback.

- [ ] **Step 5:** Implement `jaccard_similarity(a: frozenset[str], b: frozenset[str]) -> float`.

- [ ] **Step 6:** Implement blocking helpers: extension family, length bucket, length ratio, fingerprint band intersection.

- [ ] **Step 7:** Implement `find_near_duplicate_groups(...)` per spec:

```python
def find_near_duplicate_groups(
    files: Sequence[NearDuplicateInput],
    *,
    exact_group_by_file_id: Mapping[str, str],
    near_batch_id: str,
    threshold: float = NEAR_DUP_THRESHOLD,
) -> NearDuplicateResult:
```

- [ ] **Step 8:** Skip pair when same `content_hash` or same `exact_group_by_file_id[file_id]`.

- [ ] **Step 9:** Union-find clustering; deterministic `group_id = f"near:{near_batch_id}:{index}"`.

- [ ] **Step 10:** Return `NearDuplicateStats` including `candidate_pair_count` for blocking proof tests.

- [ ] **Step 11:** Run `python -m pytest tests/test_bridge_contract.py -k near_dup -q` (tests added in Task 9 first — TDD: write failing tests in Task 1 Step 12 if preferred).

- [ ] **Step 12:** Add domain-focused tests at bottom of `tests/test_bridge_contract.py` (no new file):

  - normalization stable
  - hash stable across processes
  - threshold accept/reject
  - same exact-group pair skipped
  - cross-group pair allowed
  - synthetic 100-file fixture: candidate pairs &lt;&lt; n(n-1)/2

---

## Task 2: Near batch id

**Files:** `src/application/near_batch_id.py`

- [ ] **Step 1:** Implement `content_set_digest(files: list[FileRecord]) -> str` — SHA-256 of sorted `f"{id}:{content_sha256}"` lines, first 16 hex.

- [ ] **Step 2:** Implement `make_near_batch_id(*, library_revision: int, folder_path: str, content_set_digest: str, scan_completed_at: str | None = None) -> str`:

```text
{nearBatchId} = "{library_revision}:{scan_completed_at or utc_now_iso}:{content_set_digest[:16]}"
```

- [ ] **Step 3:** Unit test: same inputs → same id; revision change → different id.

---

## Task 3: SQLite near persistence

**Files:** `src/infrastructure/sqlite_library_index.py`, `src/infrastructure/memory_library_index.py`, `src/application/ports/library_index.py`

- [ ] **Step 1:** Extend `_SCHEMA` with `near_duplicate_groups`, `near_duplicate_group_members`, `near_duplicate_pairs` per spec 007 (`near_batch_id` column name).

- [ ] **Step 2:** Add port methods:

```python
def replace_near_duplicate_results(
    self, folder_path: str, batch: NearDuplicatePersistBatch
) -> None: ...

def load_near_groups_for_folder(self, folder_path: str, near_batch_id: str) -> ...: ...

def clear_near_duplicate_results(self, folder_path: str) -> None: ...
```

- [ ] **Step 3:** Implement replace in transaction: `DELETE` all near rows for `folder_path` → `INSERT` new batch.

- [ ] **Step 4:** `clear()` also clears near tables.

- [ ] **Step 5:** Memory index mirrors for unit tests.

- [ ] **Step 6:** Tests in `test_bridge_contract.py`: round-trip replace; no blob columns (assert column list or insert payload keys).

---

## Task 4: Text read + application orchestration

**Files:** `src/application/near_text_reader.py`, `src/application/near_duplicate_detect.py`

- [ ] **Step 1:** `read_text_for_near_dup(root: Path, record: FileRecord) -> str | None` — extension allowlist; UTF-8 decode; size cap; return `None` on skip.

- [ ] **Step 2:** `run_near_duplicate_detection(session, files, *, near_batch_id, exact_group_by_file_id) -> NearDuplicateResult` — build inputs, call domain, return result.

- [ ] **Step 3:** Map domain groups → `NearDuplicatePersistBatch` for SQLite.

- [ ] **Step 4:** Do **not** add EPUB/parser unless already in repo scan path.

---

## Task 5: Post-scan integration

**Files:** `src/application/library_session.py`, `src/application/near_review_rows_builder.py`

- [ ] **Step 1:** After successful scan block in `_run_scan` (after `_rebuild_quality_index`, before setting idle):

```python
try:
    self._run_near_duplicate_phase(folder, collected)
except Exception:
    logger.exception("near duplicate detection failed")
    # leave near cache empty; exact cache already built
```

- [ ] **Step 2:** `_run_near_duplicate_phase`:

  1. Build `exact_group_by_file_id` from `find_exact_duplicate_groups`.
  2. `near_batch_id = make_near_batch_id(...)`.
  3. Run detector + `replace_near_duplicate_results`.
  4. Build near review rows; append to `_review_rows_cache` (exact rows already present).
  5. `prune_review_state` with valid near + exact group ids.

- [ ] **Step 3:** `build_near_review_rows(groups, files_by_id) -> list[dict]` — mirror `build_review_rows` field names; `type: "near"`.

- [ ] **Step 4:** On `refresh_index_from_disk` / rescan — near tables replaced; near cache rebuilt.

- [ ] **Step 5:** Bridge test: after scan fixture with similar texts, `filters.types: ["near"]` returns rows (Task 7).

---

## Task 6: Review query filters

**Files:** `src/application/review_query.py`

- [ ] **Step 1:** Replace unconditional `if row.get("type") != "exact": continue` with:

| `filters.types` | Include |
|-----------------|--------|
| absent / empty | `exact` only (default) |
| `["exact"]` | exact |
| `["near"]` | near |
| `["exact","near"]` or contains both | both |

- [ ] **Step 2:** Keep `_types_yield_empty` behavior for relation/move_only-only filters.

- [ ] **Step 3:** Tests:

  - default query → exact only (existing tests pass)
  - `test_query_review_rows_near_filter_empty` → **update** to expect rows when near data exists
  - new test: `types: ["exact","near"]` returns both

---

## Task 7: Near group detail

**Files:** `src/application/near_group_detail.py`, `src/application/duplicate_group_detail.py`, `src/application/library_session.py`, `src/app/bridge_contract.py`

- [ ] **Step 1:** `build_near_group_detail(group_id, *, near_tables, review_rows, files_by_id, quality_by_path)`.

- [ ] **Step 2:** Dispatch in `get_duplicate_group_detail`:

```python
if group_id.startswith("near:"):
    return build_near_group_detail(...)
return build_duplicate_group_detail(...)  # exact path unchanged
```

- [ ] **Step 3:** Near ok payload:

```python
{
  "status": "ok",
  "type": "near",
  "groupId": group_id,
  "evidence": {
    "matchKind": "near_ngram_v1",
    "maxSimilarity": ...,
    "threshold": 0.82,
    "memberCount": ...,
    "comparisonMethod": "text n-gram overlap",
  },
  "movePlan": null or omitted,  # plan lock: no move plan for near
}
```

- [ ] **Step 4:** Relax `validate_duplicate_group_detail` — allow `type: "near"`, `matchKind: "near_ngram_v1"`; movePlan optional for near.

- [ ] **Step 5:** Tests: near detail ok; exact detail unchanged.

---

## Task 8: Apply blocking

**Files:** `src/app/build_preview_plan.py`, `src/app/apply_resolved_actions.py`, `web/src/types/movePreview.ts`, `web/src/bridge/callBridge.ts` (if reason mapping)

- [ ] **Step 1:** Add helper `selection_includes_near_rows(rows) -> bool` in `selection_resolve.py` or `build_preview_plan.py`.

- [ ] **Step 2:** At start of `BuildPreviewPlanUseCase.execute`:

```python
if selection_includes_near_rows(selected_rows):
    raise PreviewApplyError("NEAR_DUPLICATE_APPLY_UNSUPPORTED")
```

- [ ] **Step 3:** Same guard in `ApplyResolvedActionsUseCase.execute` before applying.

- [ ] **Step 4:** Extend TS `PreviewApplyErrorCode` with `NEAR_DUPLICATE_APPLY_UNSUPPORTED`.

- [ ] **Step 5:** Tests:

  - near-only preview raises
  - mixed exact+near preview raises
  - exact-only preview still passes existing tests

---

## Task 9: Resolve UI

**Files:** `ResolveAndOrganizeWorkspace.tsx`, `FacetPanel.tsx` or small type filter control, `DetailPanel.tsx`, `ApplySubflowDialog.tsx`, `mockBridge.ts`

- [ ] **Step 1:** Add UI state `rowTypeFilter: "exact" | "near" | "all"` default **`exact`**.

- [ ] **Step 2:** Pass `filters: { types: [...] }` into `queryReviewRows` per filter.

- [ ] **Step 3:** Render **Near** badge on `row.type === "near"` (column or name suffix).

- [ ] **Step 4:** Show `confidence` / max similarity when present.

- [ ] **Step 5:** `canApply = selection.every(row => row.type === "exact")` (file rows only) — disable Apply / open subflow with tooltip.

- [ ] **Step 6:** DetailPanel: when `detail.type === "near"`, show near evidence strings; hide move plan section.

- [ ] **Step 7:** mockBridge: generate 1–2 near groups on scan for dev.

- [ ] **Step 8:** `cd web && npm run lint` PASS.

---

## Task 10: Verification and docs

- [ ] **Step 1:** `python scripts/verify_phase_completion.py` — record pass/fail in plan status.

- [ ] **Step 2:** Optional: `cd web && npm test` if project has unit tests beyond lint.

- [ ] **Step 3:** Update plan status → **Implemented** with date.

- [ ] **Step 4:** Roadmap PR-19 row → Done (separate docs commit).

- [ ] **Step 5:** Plan scope freeze — no PR-20 relation work, no near apply, no fingerprint blobs.

---

## Verification commands

```bash
python scripts/verify_phase_completion.py
```

```bash
cd web && npm run lint
```

Optional:

```bash
cd web && npm test
```

```bash
python -m pytest tests/test_bridge_contract.py -q
```

---

## Risk register

| Risk | Mitigation |
|------|------------|
| Scan latency | Post-scan phase; blocking; stats logging |
| Exact workflow pollution | Default exact-only filter; namespaced ids |
| Unsafe near apply | UI disable + `PreviewApplyError` + tests |
| Stale near rows | Replace-all per folder; `near_batch_id` + algorithm version |
| Schema creep | No fingerprint blobs; no near review table |
| Colon-heavy group ids | Parse `groupId` by prefix `near:` not naive split |

---

## Commit plan (after implementation)

```text
feat(domain): add deterministic near-duplicate detector
feat(db): persist near duplicate result batches
feat(review): surface near duplicate rows and detail
fix(apply): reject near duplicate preview and apply
feat(ui): show near duplicate candidates in resolve workspace
test(duplicates): cover near detection and review flow
docs(superpowers): mark PR-19 implemented
```

---

## Acceptance criteria

PR-19 matches spec 007 when all are true:

- [ ] Post-scan near phase; failure does not fail main scan
- [ ] Domain detector deterministic; blocking reduces pair count (tested)
- [ ] SQLite stores groups/members/pairs only
- [ ] Default `queryReviewRows` exact-only; near filter works
- [ ] `getDuplicateGroupDetail` supports near groups
- [ ] Apply/preview reject near and mixed selections
- [ ] Resolve UI: filter, badge, disabled apply, near detail
- [ ] Exact duplicate + apply tests unchanged
- [ ] `verify_phase_completion.py` PASS

---

## Changelog

| Date | Change |
|------|--------|
| 2026-06-01 | Initial plan 013 from approved spec 007 + codebase file map |
