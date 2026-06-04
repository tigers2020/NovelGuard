---
title: PR-50 Relation detection v2 (title_prefix_overlap)
status: approved
risk: safe
grill_me: 2026-06-03
approved: 2026-06-03
date: 2026-06-03
pr_label: PR-50
parent_spec: docs/superpowers/specs/008-2026-06-02-relation-filename-blocking-design.md
plan: docs/superpowers/plans/050-2026-06-03-domain-relation-pr50-relation-v2.md
roadmap: docs/superpowers/roadmap/007-2026-06-03-pr48-pr57-post-beta-roadmap.md
---

# 032 — Relation Detection v2 (`title_prefix_overlap`)

## Scope sentence

PR-50 adds the deferred **`title_prefix_overlap`** relation kind to filename-based relation detection, with **false-positive guards** stricter than PR-20 v1 kinds, **bumps `algorithm_version` to `relation-filename-v2`**, and **locks relation groups as review-only** (no apply/preview changes). It extends domain + application + bridge types + Resolve detail copy. It does **not** add SQLite tables, semantic/body inference, or relation move/apply execution.

---

## Problem

[008 § Relation kinds (deferred)](008-2026-06-02-relation-filename-blocking-design.md#relation-kinds-deferred) excluded `title_prefix_overlap` (B5) due to false-positive risk. Operators still see related files whose **normalized stems differ** but share a **long title prefix** (e.g. base novel vs side-story / sequel arc filenames). PR-20 kinds require **identical** normalized stems within a bucket; prefix-only siblings never surface.

---

## Grill-me resolutions (self, 2026-06-03)

| Question | Decision |
|----------|----------|
| Relation apply policy | **LOCK-REL-50-APPLY:** Unchanged — `RELATION_APPLY_UNSUPPORTED`, selection guards, mixed-selection disable, DetailPanel “검토 전용” copy. **No** guarded preview or move targets in PR-50. |
| `matchKind` bridge field | **Unchanged** `relation_filename_v1` — new behavior discriminated by `relationKind` + `algorithm_version` only. |
| Algorithm version | **`relation-filename-v2`** — included in `relationBatchId` digest (008 B2); expect review-state remap on rescan. |
| Confidence for prefix overlap | **Always `low`** (`confidence` 0.4) — never medium/high for this kind. |
| Detection gate | Same as PR-20: `SETTINGS_KEY_INCLUDE_RELATION` materializes; `filters.types` controls visibility. |
| Cross-kind priority | `chapter_sequence` > `same_title_series` > `version_variant` > **`title_prefix_overlap`** (lowest). |
| Bucket vs prefix pass | **Second pass** after v1 bucket groups: pair/cluster prefix candidates **not** already covered by an emitted v1 group on the same member set. |
| Strengthening | Reuse 008 B4 rules (same parent dir, shared non-generic token ≥4 chars, or parent path overlap ≥2 tokens) for prefix groups. |
| MIN prefix length | **`MIN_PREFIX_CHARS = 12`** on shared character prefix (after normalization). |
| Suffix bound | Longer stem may add **1–4** non-generic suffix tokens beyond shared prefix; suffix must not be numeric-only. |
| Generic-only prefix | Reject if shared prefix tokens are **all** in `GENERIC_STEM_DENYLIST`. |
| TEST_ALLOWED | Extend **`tests/test_bridge_contract.py`** only unless fixture count forces split (008 N5). |

---

## LOCKs

| ID | LOCK |
|----|------|
| **LOCK-REL-50-1** | `title_prefix_overlap` only when normalized stems **differ** and shorter stem is a **word-boundary prefix** of longer (`shorter + " "` prefix of longer). |
| **LOCK-REL-50-2** | Shared prefix length ≥ `MIN_PREFIX_CHARS` (12) and ≥ **2** shared prefix tokens, none generic-only. |
| **LOCK-REL-50-3** | Suffix on longer stem: 1–4 tokens, not all numeric, not all generic denylist. |
| **LOCK-REL-50-4** | Strengthening required (008 B4) — no cross-folder weak prefix pairs. |
| **LOCK-REL-50-5** | `confidence_label` = **`low`** only for `title_prefix_overlap`. |
| **LOCK-REL-50-6** | Apply/preview/guards **unchanged** — review-only. |
| **LOCK-REL-50-7** | `algorithm_version` = `relation-filename-v2`; bump on merge to main. |
| **LOCK-REL-50-8** | No new SQLite tables; no file body reads. |

---

## Position in program

| PR | Delivers |
|----|----------|
| PR-20 | Filename relation v1 kinds + read-only apply lock |
| PR-48/49 | Scan UX + shell dock (no relation algorithm change) |
| **PR-50** | **`title_prefix_overlap` + v2 algorithm version + detail copy** |
| PR-51+ | Grid prefs, migration, settings — unrelated |

---

## Current baseline (code truth)

| Item | Today |
|------|--------|
| Detector | [filename_relation.py](../../../src/domain/filename_relation.py) — `ALGORITHM_VERSION = relation-filename-v1` |
| Kinds | `RELATION_KINDS_V1` — three kinds only |
| Session | `_run_relation_phase` in [library_session.py](../../../src/application/library_session.py) |
| Apply | [selection_guards.py](../../../src/app/selection_guards.py) — `RELATION_APPLY_UNSUPPORTED` |
| TS | `RelationKind` union — three literals ([review.ts](../../../web/src/types/review.ts)) |
| Detail | [DetailPanel.tsx](../../../web/src/features/work/resolve/DetailPanel.tsx) — generic relation evidence lines |

---

## `title_prefix_overlap` definition

**Intent:** Files in the same library that appear to belong to one **title family** where one filename’s normalized stem extends another’s (sequel, side story, extra arc), without sharing the **exact** normalized stem required for PR-20 bucket kinds.

### Eligibility (all required)

1. **≥ 2** files after parse; each passes 008 eligibility (non-empty name, stem length ≥ `MIN_STEM_CHARS` unless strengthened).
2. Normalized stems **A ≠ B** (character-wise).
3. Let **shorter** = lexicographically smaller stem by length then text; **longer** extends shorter: `longer.startswith(shorter + " ")`.
4. `len(shorter) >= MIN_PREFIX_CHARS` (12).
5. Shared prefix token count ≥ **2**; at least one shared token ∉ `GENERIC_STEM_DENYLIST`.
6. Suffix tokens on longer stem = `longer[len(shorter):].strip().split()` — count **1–4**, not all digits, not all generic denylist.
7. **Strengthening** (008 B4): same parent directory **or** shared non-generic token (len ≥ 4) across pair **or** parent path overlap (≥ 2 significant tokens).
8. **Not** a subset of members already emitted in a v1 relation group with the **same** `member_file_ids` set (dedupe).

### Clustering (prefix pass)

- Build undirected edges between eligible pairs in a strengthened set (same parent dir batch, or union via shared non-generic token component).
- Emit connected components with ≥ `MIN_GROUP_MEMBERS` (2).
- Primary kind = `title_prefix_overlap` only when v1 classifier returns **none** for that member set; if v1 would classify, **v1 wins** (higher priority).

### Evidence payload

| Field | Prefix overlap behavior |
|-------|-------------------------|
| `matched_tokens` | Tokens of shared prefix (shorter stem tokens) |
| `differing_tokens` | Suffix tokens on longer stems (union) |
| `normalized_names` | Member basenames (unchanged) |
| `confidenceLabel` | `"low"` |
| `confidence` | `0.4` |

Optional detail-only string (bridge/UI): `sharedPrefix` = shorter stem text (no new contract requirement if matched_tokens suffices).

---

## Kind priority (updated)

| Priority | `relation_kind` |
|----------|-----------------|
| 0 | `chapter_sequence` |
| 1 | `same_title_series` |
| 2 | `version_variant` |
| 3 | `title_prefix_overlap` |

---

## Duplicate interaction

Unchanged from 008:

- Suppress when all members share same exact or near `groupId`.
- Cross-type membership allowed across different signals.

---

## Apply behavior (hard lock)

**LOCK-REL-50-APPLY** — no changes:

| Selection | Backend | UI |
|-----------|---------|-----|
| Relation (any kind) | `RELATION_APPLY_UNSUPPORTED` | Apply disabled; existing KO tooltip |
| Mixed exact + relation | Reject entire request | Disabled + type tooltip |

**Out of scope PR-50:** guarded move preview, keeper recommendation, partial apply.

---

## Bridge / API

| Surface | Change |
|---------|--------|
| `queryReviewRows` | Rows may include `relationKind: "title_prefix_overlap"` |
| `getDuplicateGroupDetail` | Same `matchKind: "relation_filename_v1"`; evidence includes new kind |
| `bridge_contract.py` | Allow `relationKind` fourth literal in validators |
| `RelationKind` (TS/Python) | Add `title_prefix_overlap` |

No new bridge methods.

---

## UI (Resolve)

| Area | Change |
|------|--------|
| DetailPanel | When `relationKind === "title_prefix_overlap"`, show helper line: shared-prefix relation, **low confidence**, review-only (KO copy in plan). |
| Grid badge/filter | No new filter control — existing relation type filter covers kind. |

---

## Performance

Prefix pass is **O(n²) within strengthened partitions only** (parent-dir buckets + token-indexed components), not global O(n²). Target: add **&lt; 500ms** to relation phase for 10k files on desktop (measure in plan verification).

---

## Testing requirements

Extend **existing** `tests/test_bridge_contract.py` (and contract validators if needed):

### Must pass (positive)

- `Alpha Chronicle.txt` + `Alpha Chronicle Side Story.txt` (same parent) → `title_prefix_overlap`, `confidenceLabel` low.
- Three-file star: base + two extensions in same folder → one prefix group.

### Must not group (negative)

- `FolderA/Chapter 01.txt` + `FolderB/Chapter 01 Extra.txt` (no strengthening).
- `ab` + `ab cd` (prefix &lt; 12 chars).
- `Novel 01.txt` + `Novel 02.txt` (identical stem after numeric strip → **v1** `same_title_series`, not prefix).
- Unrelated `01.txt` / `02.txt` (008 G1).
- Members already in exact-only duplicate group (suppression).

### Regression

- Existing PR-20 relation tests unchanged in behavior for v1 kinds.
- `include_relation = false` → no rows.
- Apply rejection codes unchanged.

---

## Acceptance criteria

PR-50 is **done** when:

- [ ] `title_prefix_overlap` emitted under guards with `confidence_label` low only
- [ ] `algorithm_version` `relation-filename-v2` in detector + batch id
- [ ] False-positive fixtures pass (§ Testing)
- [ ] TS/Python `RelationKind` includes fourth literal; contract validation updated
- [ ] DetailPanel copy for prefix overlap kind
- [ ] Apply still rejects relation with `RELATION_APPLY_UNSUPPORTED`
- [ ] `python scripts/verify_phase_completion.py` PASS recorded in plan
- [ ] Roadmap PR-50 → **Done** after merge

---

## Out of scope

| Item | Notes |
|------|--------|
| Semantic / body relation | — |
| Relation apply / move | Later product decision only |
| `matchKind` version bump to v2 | Locked unchanged |
| Settings UI for prefix thresholds | PR-53 expert slice at earliest |
| New test files | Without `TEST_ALLOWED` |

---

## Changelog

| Date | Change |
|------|--------|
| 2026-06-03 | Initial spec; grill-me locks REL-50-APPLY + prefix guards; **approved** |
