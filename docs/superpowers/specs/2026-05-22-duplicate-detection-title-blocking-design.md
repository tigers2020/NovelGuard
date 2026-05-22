# Duplicate Detection: Title Blocking for Updated Anthologies

**Status:** Approved (2026-05-22)  
**Primary pain:** Missed duplicate groups (A) — especially **updated anthology** pairs (B: same series, different `range_end`)  
**Secondary constraint:** Avoid slowing detection (D) — no Near-by-default, no full-library hash expansion in v1

---

## Problem

Users collect text novels with **filename variants** for the same work:

- `던전 & 커맨더 1-2194` vs `던전  커맨더 1-2168` (`&`, spacing)
- `너네 스킬 다 내꺼 1-1308` vs `너네 스킬 다 내꺼！ 1-1310@김단풍 (1)` (fullwidth punctuation, author tag)

`BlockingService` keys primary groups by `(extension, series_title_norm)`. Current `_normalize_series_title` leaves `&`, `！`, etc., so variants land in **different blocking groups**. `RelationDetectionStage` (version/containment) never compares them.

NovelGuard already models **B** via:

- `ContainmentDetector.detect_version` — same `range_start`, different `range_end` → newer = larger end
- `ContainmentDetector.detect_containment` — strict range inclusion

The fix is **not** new relation logic in v1; it is **unifying the blocking key** so relation stages run on the right candidate sets.

---

## Goals (v1)

1. Filename variants above map to the **same** primary blocking key.
2. Pairs like `1-2168` vs `1-2194` (same `range_start=1`) produce **version** groups with keeper = newer (larger `range_end`).
3. No change to Exact/Near defaults; no scan-time hash index (deferred v2).
4. Regression-safe: existing parser/blocking tests updated with explicit golden cases.

## Non-goals (v1)

- Near duplicate enabled by default
- Content-only matching across unrelated titles
- Persisted fingerprint index at scan time (see layer-seams / future spec)
- Replacing keeper heuristics wholesale (version groups already set `recommended_keeper_id`)

---

## Design

### 1. Stronger series title normalization

Enhance `FilenameParser._normalize_series_title`:

| Step | Rule |
|------|------|
| 1 | Unicode **NFKC** on title substring |
| 2 | Remove `(…)`, `[…]`, `@author` (existing) |
| 3 | Remove complete/epilogue **words** (existing alternation list — do not use character classes) |
| 4 | Replace punctuation/symbols with space: `& ! ? . … · ,` and similar (ASCII + common CJK punctuation after NFKC) |
| 5 | Collapse whitespace, strip, **lower** (existing) |

Use the result as **`series_title_norm`** (blocking + `is_same_series`). No separate DTO field in v1 — update docstring to state it is blocking-oriented.

**Safety:** If normalized title length &lt; 2 after strip, keep raw lowered title from step 5 fallback path (avoid empty key collapsing unrelated files).

### 2. Blocking

`BlockingService._build_primary_groups` continues to use `(extension, parse_result.series_title_norm)` — no API change, stronger norm only.

Secondary/tertiary grouping (`range_start`, `range_unit`) unchanged.

### 3. Relation & keeper (unchanged logic)

Once blocking merges variants:

- **Version** handles B (e.g. 2168 vs 2194, 1308 vs 1310).
- **Containment** handles strict sub-ranges when applicable.
- **Keeper:** version → `newer_store_id`; containment → container; Union-Find normalizer preserves highest-confidence keeper among merged groups.

### 4. Performance guard (v1)

`RelationDetectionStage` (or blocking emit): if a blocking group has **&gt; 500** files, log `debug_step` warning and cap version pair enumeration to same-`range_start` buckets only (existing bucket logic); do not add cross-range Cartesian products. Document constant in `DetectionDefaults` as `MAX_FILES_PER_BLOCKING_GROUP_FOR_VERSION_PAIRS = 500`.

---

## Acceptance tests (golden)

| Input A | Input B | Expected |
|---------|---------|----------|
| `던전 & 커맨더 1-2194.txt` | `던전  커맨더 1-2168.txt` | Same `series_title_norm`; one blocking group; **version**; keeper end=2194 |
| `너네 스킬 다 내꺼 1-1308.txt` | `너네 스킬 다 내꺼！ 1-1310@김단풍 (1).txt` | Same norm; **version**; keeper end=1310 |
| `너네 스킬 다 내꺼 1-1308.txt` | `너네 스킬 다 내꺼 1-1308.txt` | Same norm; version or single-file (no false split) |

---

## Verification

- `pytest` narrow: new/updated tests under `tests/unit/` and `tests/application/use_cases/duplicate_detection/`
- Full gate: `python scripts/verify_phase_completion.py`

---

## v2 (out of scope)

- Scan-time content fingerprints in index DB
- Optional “deep scan” with Near on ungrouped files only
- Fuzzy title clustering beyond punctuation normalization
