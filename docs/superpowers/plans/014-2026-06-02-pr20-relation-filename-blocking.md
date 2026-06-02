# PR-20: Relation / Filename-Blocking Signals — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship filename-only relation candidate detection (opt-in via `SETTINGS_KEY_INCLUDE_RELATION`), deterministic relation batch/group ids, merged `queryReviewRows` / `getDuplicateGroupDetail` for relation groups, Resolve UI relation filter/badge, and hard apply rejection — without SQLite relation tables, without weakening exact/near/apply safety.

**Architecture:** Pure detector in `src/domain/filename_relation.py`. Application builds exact/near membership maps, computes deterministic `relationBatchId`, runs detector when setting enabled, stores groups in session memory (`_relation_groups_by_id`), merges relation rows into `_review_rows_cache` via `build_relation_review_rows` + PR-17 merge. No new bridge query methods. Relation phase wrapped in try/except after near phase — **non-fatal**.

**Tech Stack:** Python 3.12, React + TypeScript, pytest + Vitest (extend existing files first).

**Spec:** [008-2026-06-02-relation-filename-blocking-design.md](../specs/008-2026-06-02-relation-filename-blocking-design.md) (**approved** 2026-06-02)

**Plan status:** **Closed** (2026-06-02) — implemented + verification PASS. See [Plan closure](#plan-closure-pr-20-slice).

**Parent:** [001 PR-20..25 roadmap](../roadmap/001-2026-06-02-pr20-pr25-development-roadmap.md) — Wave C PR-20

**Depends on:** PR-19 (near phase + apply guard pattern), PR-17 (review state), PR-18 (detail panel), PR-15/16 (apply — exact-only)

**Test policy:** Extend existing files first. Request `TEST_ALLOWED` for `tests/domain/test_filename_relation_detector.py` if domain fixtures exceed ~15 cases in `test_bridge_contract.py`.

---

## Plan-locked decisions (Spec 008 + gate review)

| Lock | Value |
|------|--------|
| Detection gate | `SETTINGS_KEY_INCLUDE_RELATION` — default **`false`**; skip relation phase when off |
| Grid visibility | `queryReviewRows.filters.types` — relation rows hidden until filter includes `"relation"` |
| Relation kinds v1 | **`same_title_series`**, **`chapter_sequence`**, **`version_variant` only** — no `title_prefix_overlap` |
| Batch id | `sha256(algorithmVersion + ":" + libraryRevision + ":" + shortFilenameSetDigest)[:16]` — **no UUID**, no `scanCompletedAtIso` |
| Group id | `relation:<relationBatchId>:<clusterIndex>` |
| Row ids | `group:relation:…`, `file:relation:…` |
| Token precedence | `v\d+` → `version_markers` only; never `numeric_tokens` |
| Generic stem | `GENERIC_STEM_DENYLIST` + path/parent/token strengthening (B4) |
| Apply | `RELATION_APPLY_UNSUPPORTED`; mixed exact+near+relation → reject whole request |
| Mixed UX | Any non-exact selection → apply disabled; tooltip names first blocking type (`near` before `relation`) |
| Persistence | **No** `relation_*` SQLite tables — session memory only |
| APIs | Extend `queryReviewRows`, `getDuplicateGroupDetail`, `getAppSetting` / `setAppSetting` only |

---

## File map

| File | Action |
|------|--------|
| `src/domain/settings_keys.py` | **Create** — `SETTINGS_KEY_INCLUDE_RELATION` |
| `src/domain/filename_relation.py` | **Create** — parse, bucket, cluster, `detect_filename_relations` |
| `src/application/relation_batch_id.py` | **Create** — `filename_set_digest`, `make_relation_batch_id` |
| `src/application/relation_membership.py` | **Create** — `build_exact_membership_by_file_id`, `build_near_membership_by_file_id` |
| `src/application/relation_review_rows_builder.py` | **Create** — `build_relation_review_rows` |
| `src/application/relation_group_detail.py` | **Create** — `build_relation_group_detail` |
| `src/application/app_settings.py` | **Create** — in-memory bool store (default false) |
| `src/application/library_session.py` | **Modify** — settings read; `_run_relation_phase`; strip relation rows; detail dispatch |
| `src/application/review_query.py` | **Modify** — relation in type filter union (already non-exact aware) |
| `src/app/selection_guards.py` | **Modify** — `selection_includes_relation_rows`, `first_blocking_review_row_type` |
| `src/app/build_preview_plan.py` | **Modify** — reject relation rows |
| `src/app/apply_resolved_actions.py` | **Modify** — reject relation rows |
| `src/app/bridge_contract.py` | **Modify** — relation detail validation; `relation_filename_v1` |
| `src/app/bridge_api.py` | **Modify** — `get_app_setting` / `set_app_setting` |
| `web/src/types/review.ts` | **Modify** — relation detail variant; row fields `relationKind`, `confidenceLabel` |
| `web/src/types/movePreview.ts` | **Modify** — `RELATION_APPLY_UNSUPPORTED` |
| `web/src/types/settings.ts` | **Create** — setting key constant mirror |
| `web/src/features/work/ResolveAndOrganizeWorkspace.tsx` | **Modify** — relation filter; apply disable helper |
| `web/src/features/work/resolve/DetailPanel.tsx` | **Modify** — relation evidence label |
| `web/src/features/work/resolve/reviewGridColumns.tsx` | **Modify** — relation badge |
| `web/src/bridge/mockBridge.ts` | **Modify** — settings + synthetic relation rows |
| `web/src/contracts/bridgeParity.ts` | **Modify** — new methods if listed |
| `tests/test_bridge_contract.py` | **Modify** — domain, settings gate, bridge, apply, **5 gate fixtures** |

---

## Task 0: Plan gate checklist

- [ ] Human approves this plan (status → **Approved**).
- [ ] Spec 008 remains **approved** — no open grill-me / gate items.
- [ ] Do **not** start implementation until both gates pass.

---

## Task 1: Settings constant + scan-time read path (gate lock #1)

**Files:** `src/domain/settings_keys.py`, `src/application/app_settings.py`, `src/application/library_session.py`, `src/app/bridge_api.py`, `web/src/types/settings.ts`, `web/src/bridge/mockBridge.ts`

- [ ] **Step 1:** Create settings keys:

```python
# src/domain/settings_keys.py
SETTINGS_KEY_INCLUDE_RELATION = "include_relation"
```

- [ ] **Step 2:** Create minimal store:

```python
# src/application/app_settings.py
from domain.settings_keys import SETTINGS_KEY_INCLUDE_RELATION

_DEFAULTS: dict[str, bool] = {SETTINGS_KEY_INCLUDE_RELATION: False}

class AppSettings:
    def __init__(self) -> None:
        self._bools = dict(_DEFAULTS)

    def get_bool(self, key: str, default: bool = False) -> bool:
        return self._bools.get(key, default)

    def set_bool(self, key: str, value: bool) -> None:
        self._bools[key] = value
```

- [ ] **Step 3:** Wire `AppSettings` into `LibrarySession.__init__`; expose `get_app_setting(key) -> bool`, `set_app_setting(key, value: bool) -> None`.

- [ ] **Step 4:** In `_run_relation_phase` entry (Task 4), guard:

```python
if not self._settings.get_bool(SETTINGS_KEY_INCLUDE_RELATION):
    self._strip_relation_rows()
    self._relation_groups_by_id = {}
    return
```

- [ ] **Step 5:** Bridge API:

```python
def get_app_setting(self, key: str) -> bool:
    return self._session.get_app_setting(key)

def set_app_setting(self, key: str, value: bool) -> None:
    self._session.set_app_setting(key, value)
```

- [ ] **Step 6:** mockBridge parity — default `include_relation: false`; `setAppSetting` updates in-memory flag used by synthetic relation materialization in tests.

- [ ] **Step 7:** Contract test — `include_relation` false → after scan, `filters.types: ["relation"]` returns empty page.

Run: `python -m pytest tests/test_bridge_contract.py -k include_relation -v`

---

## Task 2: Domain filename relation detector

**Files:** `src/domain/filename_relation.py`

- [ ] **Step 1:** Constants:

```python
ALGORITHM_VERSION = "relation-filename-v1"
MIN_STEM_CHARS = 4
MIN_GROUP_MEMBERS = 2
MAX_CHAPTER_GAP = 50
RELATION_KINDS_V1 = frozenset({
    "same_title_series",
    "chapter_sequence",
    "version_variant",
})
GENERIC_STEM_DENYLIST = frozenset({
    "chapter", "chap", "ch", "episode", "ep", "part", "volume", "vol",
    "book", "text", "novel", "raw", "번역", "완결",
})
```

- [ ] **Step 2:** Implement `normalize_filename_for_relation(name: str, *, relative_path: str) -> FilenameRelationParse` per spec § Filename normalization + § Token precedence.

- [ ] **Step 3:** Implement generic stem eligibility + strengthening (spec § Generic title suppression).

- [ ] **Step 4:** Implement `title_stem_key(normalized_stem: str) -> str | None`.

- [ ] **Step 5:** Implement kind classifiers inside stem bucket — **whitelist `RELATION_KINDS_V1` only** (gate lock #5).

- [ ] **Step 6:** Implement `detect_filename_relations(...)` signature from spec § Domain detector signature (N3):

```python
def detect_filename_relations(
    files: Sequence[FileRecord],
    *,
    exact_membership_by_file_id: Mapping[str, str],
    near_membership_by_file_id: Mapping[str, str],
    relation_batch_id: str,
    algorithm_version: str = ALGORITHM_VERSION,
) -> RelationDetectionResult:
```

- [ ] **Step 7:** Suppress edges when both files share same exact or near group id.

- [ ] **Step 8:** Deterministic `clusterIndex` sort (spec § Clustering step 6).

- [ ] **Step 9:** Emit `RelationGroup` with `group_id = f"relation:{relation_batch_id}:{cluster_index}"`, `relation_kind`, `confidence`, `confidence_label`, evidence tokens.

**Gate lock tests (add to `tests/test_bridge_contract.py` or domain file with TEST_ALLOWED):**

```python
def test_relation_token_precedence_v2_is_version_not_numeric() -> None:
    from domain.filename_relation import normalize_filename_for_relation

    parsed = normalize_filename_for_relation("Novel v2.txt", relative_path="Novel v2.txt")
    assert parsed.version_markers == ("v2",)
    assert parsed.numeric_tokens == ()

    parsed_v10 = normalize_filename_for_relation("Title v10.txt", relative_path="Title v10.txt")
    assert parsed_v10.version_markers == ("v10",)
    assert 10 not in parsed_v10.numeric_tokens

    parsed_v01 = normalize_filename_for_relation("Story v01.txt", relative_path="Story v01.txt")
    assert parsed_v01.version_markers == ("v01",)
    assert 1 not in parsed_v01.numeric_tokens
```

---

## Task 3: Deterministic relation batch id (gate lock #2)

**Files:** `src/application/relation_batch_id.py`

- [ ] **Step 1:** Implement digest:

```python
def filename_set_digest(files: list[FileRecord]) -> str:
    lines = sorted(
        f"{record.id}|{record.name}|{record.size_bytes}|{record.modified_at_ns}"
        for record in files
    )
    payload = "\n".join(lines)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
```

- [ ] **Step 2:** Implement batch id:

```python
def make_relation_batch_id(
    *,
    library_revision: int,
    filename_set_digest_value: str,
    algorithm_version: str = "relation-filename-v1",
) -> str:
    payload = f"{algorithm_version}:{library_revision}:{filename_set_digest_value[:16]}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
```

- [ ] **Step 3:** **Gate lock test** — same inputs → same batch id and cluster indices:

```python
def test_relation_batch_and_cluster_ids_are_deterministic() -> None:
    from application.relation_batch_id import filename_set_digest, make_relation_batch_id
    from domain.filename_relation import detect_filename_relations
    from domain.models import FileRecord

    files = [
        FileRecord(id="a" * 64, relative_path="Series/Novel 01.txt", name="Novel 01.txt",
                   size_bytes=100, modified_at_ns=1, extension=".txt", content_sha256="h1"),
        FileRecord(id="b" * 64, relative_path="Series/Novel 02.txt", name="Novel 02.txt",
                   size_bytes=100, modified_at_ns=2, extension=".txt", content_sha256="h2"),
    ]
    digest = filename_set_digest(files)
    batch_a = make_relation_batch_id(library_revision=3, filename_set_digest_value=digest)
    batch_b = make_relation_batch_id(library_revision=3, filename_set_digest_value=digest)
    assert batch_a == batch_b

    result_a = detect_filename_relations(
        files, exact_membership_by_file_id={}, near_membership_by_file_id={},
        relation_batch_id=batch_a,
    )
    result_b = detect_filename_relations(
        files, exact_membership_by_file_id={}, near_membership_by_file_id={},
        relation_batch_id=batch_b,
    )
    assert [g.group_id for g in result_a.groups] == [g.group_id for g in result_b.groups]
```

Run: `python -m pytest tests/test_bridge_contract.py -k relation_batch -v`

---

## Task 4: Library session relation phase

**Files:** `src/application/library_session.py`, `src/application/relation_membership.py`, `src/application/relation_review_rows_builder.py`

- [ ] **Step 1:** Add session fields: `_relation_groups_by_id: dict[str, RelationGroup] = {}`.

- [ ] **Step 2:** Implement `_strip_relation_rows()` mirroring `_strip_near_rows`.

- [ ] **Step 3:** Implement `_run_relation_phase(folder, files)`:

  1. Return early if `SETTINGS_KEY_INCLUDE_RELATION` is false.
  2. `_strip_relation_rows()`; clear `_relation_groups_by_id`.
  3. Compute `relation_batch_id` via Task 3 helpers.
  4. Build membership maps from exact groups + `_near_groups_by_id`.
  5. Call `detect_filename_relations`.
  6. `build_relation_review_rows` → `merge_review_state` → extend cache.
  7. Prune review state with valid relation group ids.
  8. `_refresh_resolve_counts()`.

- [ ] **Step 4:** Call `_run_relation_phase` in `_run_scan` success path **after** `_run_near_duplicate_phase`, inside try/except (log, non-fatal).

- [ ] **Step 5:** Include relation group ids in `valid_group_ids` for prune (mirror near).

- [ ] **Step 6:** `_clear_review_cache` clears `_relation_groups_by_id`.

Run: `python -m pytest tests/test_bridge_contract.py -k relation_phase -v`

---

## Task 5: Relation review rows + detail DTOs

**Files:** `src/application/relation_review_rows_builder.py`, `src/application/relation_group_detail.py`, `src/application/library_session.py`

- [ ] **Step 1:** `build_relation_review_rows` — mirror near builder; include required fields:

```python
{
    "type": "relation",
    "relationKind": group.relation_kind,
    "confidence": group.confidence,
    "confidenceLabel": group.confidence_label,
    "proposedAction": "ignore",  # file rows
}
```

- [ ] **Step 2:** `build_relation_group_detail` — `type: "relation"`, `evidence.matchKind: "relation_filename_v1"`, evidence payload from spec.

- [ ] **Step 3:** `get_duplicate_group_detail` dispatch:

```python
if group_id.startswith("relation:"):
    return build_relation_group_detail(...)
```

---

## Task 6: Apply guards + bridge contract

**Files:** `src/app/selection_guards.py`, `src/app/build_preview_plan.py`, `src/app/apply_resolved_actions.py`, `src/app/bridge_contract.py`

- [ ] **Step 1:** Extend guards:

```python
def selection_includes_relation_rows(rows: list[dict[str, Any]]) -> bool:
    return any(row.get("type") == "relation" for row in rows)

def first_blocking_review_row_type(rows: list[dict[str, Any]]) -> str | None:
    if any(row.get("type") == "near" for row in rows):
        return "near"
    if any(row.get("type") == "relation" for row in rows):
        return "relation"
    return None
```

- [ ] **Step 2:** `build_preview_plan` — after near check, reject relation:

```python
if selection_includes_relation_rows(selected_rows):
    raise PreviewApplyError("RELATION_APPLY_UNSUPPORTED")
```

- [ ] **Step 3:** Same in `apply_resolved_actions`.

- [ ] **Step 4:** `validate_duplicate_group_detail` — allow `type: "relation"`, `matchKind: "relation_filename_v1"`.

- [ ] **Step 5:** Contract tests — relation-only and mixed exact+relation preview/apply raise `RELATION_APPLY_UNSUPPORTED`.

Run: `python -m pytest tests/test_bridge_contract.py -k relation_apply -v`

---

## Task 7: False-positive fixtures (gate locks #3, #4)

**Files:** `tests/test_bridge_contract.py` (or `tests/domain/test_filename_relation_detector.py` with TEST_ALLOWED)

- [ ] **Step 1:** Numeric-only (G1):

```python
def test_relation_does_not_group_numeric_only_filenames() -> None:
    # 01.txt + 02.txt → zero groups
```

- [ ] **Step 2:** Generic cross-folder (B4 / gate lock #4):

```python
def test_relation_does_not_group_generic_chapter_across_folders() -> None:
    files = [
        FileRecord(..., relative_path="FolderA/Chapter 01.txt", name="Chapter 01.txt", ...),
        FileRecord(..., relative_path="FolderB/Chapter 02.txt", name="Chapter 02.txt", ...),
    ]
    result = detect_filename_relations(files, ...)
    assert result.groups == []
```

- [ ] **Step 3:** Same-parent generic may group:

```python
def test_relation_groups_generic_chapter_in_same_parent() -> None:
    files = [
        FileRecord(..., relative_path="Series/Chapter 01.txt", ...),
        FileRecord(..., relative_path="Series/Chapter 02.txt", ...),
    ]
    assert len(result.groups) == 1
    assert result.groups[0].relation_kind in RELATION_KINDS_V1
```

- [ ] **Step 4:** Positive series fixture — `Novel 01.txt` + `Novel 02.txt` groups as `same_title_series` or `chapter_sequence`.

- [ ] **Step 5:** Relation kind whitelist — assert no group has `relation_kind == "title_prefix_overlap"`.

Run: `python -m pytest tests/test_bridge_contract.py -k "relation_does_not or relation_groups" -v`

---

## Task 8: Web types + Resolve UI

**Files:** `web/src/types/review.ts`, `web/src/types/movePreview.ts`, `web/src/features/work/ResolveAndOrganizeWorkspace.tsx`, `web/src/features/work/resolve/DetailPanel.tsx`, `web/src/features/work/resolve/reviewGridColumns.tsx`

- [ ] **Step 1:** Add types:

```typescript
export type RelationKind = "same_title_series" | "chapter_sequence" | "version_variant";
export type ConfidenceLabel = "low" | "medium" | "high";

// ReviewRow — add optional fields used when type === "relation"
relationKind?: RelationKind;
confidenceLabel?: ConfidenceLabel;

export type DuplicateMatchKind = "exact_content_hash" | "near_ngram_v1" | "relation_filename_v1";

export interface DuplicateGroupDetailRelationOk extends DuplicateGroupDetailOkBase {
  type: "relation";
  evidence: {
    matchKind: "relation_filename_v1";
    relationKind: RelationKind;
    confidenceLabel: ConfidenceLabel;
    normalizedNames: string[];
    matchedTokens: string[];
    differingTokens: string[];
    memberCount: number;
  };
}
```

- [ ] **Step 2:** Extend `rowTypeFilter` union: `"exact" | "near" | "relation" | "all"`.

- [ ] **Step 3:** Filter chips — add Relation option; map to `filters.types: ["relation"]`.

- [ ] **Step 4:** Apply disable — use `first_blocking_review_row_type` logic client-side:

```typescript
const applyBlockedReason = useMemo(() => {
  const selected = rows.filter((r) => explicitIds.includes(r.id));
  if (selected.some((r) => r.type === "near")) return "near";
  if (selected.some((r) => r.type === "relation")) return "relation";
  if (rowTypeFilter !== "exact") return rowTypeFilter;
  return null;
}, [explicitIds, rows, rowTypeFilter]);
```

- [ ] **Step 5:** Tooltip strings — near vs relation specific (G5).

- [ ] **Step 6:** DetailPanel — relation evidence block (kind + confidence + token lists).

- [ ] **Step 7:** Grid badge — `relation` type chip (mirror near styling).

Run: `cd web && npm run lint`

---

## Task 9: Bridge integration tests

**Files:** `tests/test_bridge_contract.py`, `web/src/bridge/bridgeParity.test.ts`

- [ ] **Step 1:** End-to-end with `set_app_setting(SETTINGS_KEY_INCLUDE_RELATION, True)` → scan fixture folder → `queryReviewRows` with `types: ["relation"]` returns rows.

- [ ] **Step 2:** Default query still exact-only (no relation rows).

- [ ] **Step 3:** `getDuplicateGroupDetail(relationGroupId)` returns `type: "relation"`.

- [ ] **Step 4:** Setting off → relation filter empty after scan.

- [ ] **Step 5:** bridgeParity — register `getAppSetting` / `setAppSetting` if added to method list.

Run: `python -m pytest tests/test_bridge_contract.py -q`

---

## Task 10: Verification + docs

- [ ] **Step 1:** `python scripts/verify_phase_completion.py` — record pass/fail in plan status.

- [ ] **Step 2:** `cd web && npm run lint`

- [ ] **Step 3:** Update plan status → **Implemented** with date + pytest count.

- [ ] **Step 4:** Roadmap 001 — PR-20 row → Done.

- [ ] **Step 5:** Plan scope freeze — no `title_prefix_overlap`, no relation SQLite, no relation apply, no quality track work.

---

## Verification commands

```bash
python scripts/verify_phase_completion.py
```

```bash
python -m pytest tests/test_bridge_contract.py -q
```

```bash
cd web && npm run lint
```

---

## Risk register

| Risk | Mitigation |
|------|------------|
| False positive noise | Generic denylist + path guard; opt-in setting default false |
| Review state orphan | Deterministic batch id; no UUID fallback |
| Apply safety regression | Separate error code + UI disable + contract tests |
| Near/exact pollution | Namespaced ids; strip/replace relation rows each phase |
| Settings UI missing | Bridge get/set + mockBridge; dev/tests enable explicitly |
| Test file bloat | TEST_ALLOWED gate for domain module split |

---

## Gate reviewer fixture checklist (must pass)

| # | Fixture | Task |
|---|---------|------|
| 1 | Settings constant + scan-time read | Task 1 |
| 2 | Same input → same `relationBatchId`, `clusterIndex` | Task 3 |
| 3 | `v01`, `v2`, `v10` not in `numeric_tokens` | Task 2 |
| 4 | `FolderA/Chapter 01` + `FolderB/Chapter 02` → no group | Task 7 |
| 5 | Relation kind whitelist (3 kinds only) | Task 2, 7 |

---

## Commit plan (after implementation)

```text
feat(domain): add filename relation detector v1
feat(settings): wire include_relation scan gate
feat(review): surface relation rows and detail
fix(apply): reject relation preview and apply
feat(ui): relation filter badge and apply disable
test(relations): cover false positives and deterministic ids
docs(superpowers): mark PR-20 implemented
```

---

## Acceptance criteria

PR-20 matches spec 008 when all are true:

- [ ] `include_relation` default false; true enables post-scan relation phase
- [ ] Domain detector deterministic; 3 relation kinds only
- [ ] No relation SQLite tables
- [ ] Default `queryReviewRows` exact-only; relation filter works
- [ ] `getDuplicateGroupDetail` supports relation groups
- [ ] Apply/preview reject relation and mixed selections
- [ ] Resolve UI: relation filter, badge, disabled apply, relation detail
- [ ] Gate fixtures 1–5 pass
- [ ] Exact/near duplicate + apply tests unchanged
- [ ] `verify_phase_completion.py` PASS

---

## Plan closure (PR-20 slice)

**Closed:** 2026-06-02  
**Spec:** [008 relation filename blocking](../specs/008-2026-06-02-relation-filename-blocking-design.md) (approved)  
**Scope freeze:** honored — no `title_prefix_overlap`, no relation SQLite, no relation apply, no quality-track work in this slice.

### Verification evidence

| Command | Result |
|---------|--------|
| `python -m pytest tests/test_bridge_contract.py -q` | **72 passed** (2026-06-02) |
| `python scripts/verify_phase_completion.py` | PASS (noted in plan header at implement time) |
| `cd web && npm run lint` | PASS (implement time) |

### Delivered (code truth)

| Area | Delivered |
|------|-----------|
| Domain | `filename_relation.py` — 3 kinds, token precedence, generic stem guard |
| Settings | `SETTINGS_KEY_INCLUDE_RELATION` default false; scan-time gate |
| Session | `_run_relation_phase` post-near, non-fatal try/except; session memory groups |
| Review | Relation rows in cache; `queryReviewRows` filter `relation`; detail `relation_filename_v1` |
| Apply | `RELATION_APPLY_UNSUPPORTED`; mixed selection guards |
| Web | Relation filter/badge; apply disable tooltip; relation detail panel fields |
| Tests | Gate fixtures in `test_bridge_contract.py` (settings, batch id, token precedence, false positives) |

### Acceptance criteria (plan §)

All plan-locked items shipped: opt-in detection, deterministic ids, no relation DB, apply rejection, UI filter/badge/disable, gate fixtures 1–5 covered by contract tests. Exact/near safety preserved.

### Known gaps (intentional — out of scope)

- Settings UI screen for `include_relation` (bridge get/set only; tests/dev enable explicitly)
- Dedicated `tests/domain/test_filename_relation_detector.py` (deferred unless `TEST_ALLOWED`)
- `title_prefix_overlap` relation kind

### Handoff

**Next:** PR-21 — [009 quality issue detail spec](../specs/009-2026-06-02-quality-issue-detail-design.md) → grill-me → [015 plan](./015-2026-06-02-pr21-quality-issue-detail.md).

---

## Changelog

| Date | Change |
|------|--------|
| 2026-06-02 | Initial plan 014 from approved spec 008 + gate reviewer locks |
| 2026-06-02 | Plan closure note; status **Closed**; pytest count corrected to 72 |
