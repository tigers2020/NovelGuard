# PR-50: Relation Detection v2 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans.

**Goal:** Add `title_prefix_overlap` relation kind with false-positive guards; bump algorithm version to `relation-filename-v2`; update types and DetailPanel copy; keep relation apply read-only.

**Architecture:** Extend [filename_relation.py](../../../src/domain/filename_relation.py) with a second-pass prefix clustering after v1 bucket groups; wire `RELATION_KINDS` + `ALGORITHM_VERSION`; extend bridge/TS unions and contract validators; minimal DetailPanel KO helper line.

**Spec:** [032-2026-06-03-domain-relation-v2-design.md](../specs/032-2026-06-03-domain-relation-v2-design.md)

**Branch:** `feat/pr50-relation-v2`

---

## File map

| File | Action |
|------|--------|
| `src/domain/filename_relation.py` | Modify — v2 kind, prefix pass, constants |
| `src/app/bridge_contract.py` | Modify — allow `title_prefix_overlap` in relationKind |
| `web/src/types/review.ts` | Modify — `RelationKind` union |
| `web/src/features/work/resolve/DetailPanel.tsx` | Modify — prefix overlap evidence copy |
| `tests/test_bridge_contract.py` | Modify — positive/negative fixtures + whitelist |
| `web/src/bridge/mockDuplicateGroupDetail.ts` | Modify — optional mock kind (if tests use it) |

**No changes:** `selection_guards.py`, apply paths, SQLite, `matchKind` string.

---

### Task 1: Domain — constants and v1 regression safety

**Files:**
- Modify: `src/domain/filename_relation.py`

- [ ] **Step 1:** Set `ALGORITHM_VERSION = "relation-filename-v2"`.
- [ ] **Step 2:** Add `title_prefix_overlap` to kinds frozenset; extend `_RELATION_KIND_PRIORITY` (priority 3).
- [ ] **Step 3:** Export `RELATION_KINDS_V2` or expand `RELATION_KINDS_V1` → `RELATION_KINDS` (update tests importing `RELATION_KINDS_V1`).
- [ ] **Step 4:** Run existing relation tests — expect batch id change only; fix imports if renamed.

Run: `pytest tests/test_bridge_contract.py -k relation -v`

---

### Task 2: Domain — prefix overlap detection

**Files:**
- Modify: `src/domain/filename_relation.py`

- [ ] **Step 1:** Add constants: `MIN_PREFIX_CHARS = 12`, `MIN_PREFIX_TOKENS = 2`, `MAX_PREFIX_SUFFIX_TOKENS = 4`.
- [ ] **Step 2:** Implement `_is_valid_prefix_pair(shorter, longer) -> bool` per spec LOCK-REL-50-1..3.
- [ ] **Step 3:** Implement `_prefix_overlap_components(prepared) -> list[list[_PreparedFile]]` using strengthening partitions (parent-dir buckets + token components).
- [ ] **Step 4:** After v1 `raw_groups` built, run prefix pass; skip sets already covered by v1 groups (same `member_file_ids` frozenset).
- [ ] **Step 5:** Assign `confidence_label="low"`, `confidence=0.4`; merge into sort key `(priority, stem, min file id, digest)`.
- [ ] **Step 6:** Re-sort all groups and reassign `clusterIndex` 0..n-1 deterministically.

Run: `pytest tests/test_bridge_contract.py -k relation -v`

---

### Task 3: Bridge contract + types

**Files:**
- Modify: `src/app/bridge_contract.py`
- Modify: `web/src/types/review.ts`

- [ ] **Step 1:** Allow `relationKind` value `title_prefix_overlap` in page/detail validators.
- [ ] **Step 2:** Extend TS `RelationKind` union.

Run: `pytest tests/test_bridge_contract.py -k "relation or duplicate_group_detail" -v --tb=short`

---

### Task 4: Tests (contract)

**Files:**
- Modify: `tests/test_bridge_contract.py`

- [ ] **Step 1:** Positive: same-folder `Alpha Chronicle` + `Alpha Chronicle Side Story` → kind `title_prefix_overlap`, label low.
- [ ] **Step 2:** Negative: cross-folder generic prefix without strengthening → no group.
- [ ] **Step 3:** Negative: short prefix (&lt; 12 chars) → no group.
- [ ] **Step 4:** Update `test_query_review_rows_relation_after_enabled_scan` whitelist to include fourth kind.
- [ ] **Step 5:** Assert `algorithm_version` / batch id uses v2 when wired through session (optional session test).

Run: `pytest tests/test_bridge_contract.py -k relation -v`

---

### Task 5: UI — DetailPanel copy

**Files:**
- Modify: `web/src/features/work/resolve/DetailPanel.tsx`

- [ ] **Step 1:** When `detail.evidence.relationKind === "title_prefix_overlap"`, add KO helper under evidence: shared title prefix, low confidence, review-only (align with existing apply disclaimer).

Run: `cd web && npm run lint`

---

### Task 6: Verification matrix

- [ ] `python scripts/verify_phase_completion.py`
- [ ] `pytest tests/test_bridge_contract.py -q`
- [ ] `cd web && npm run lint`
- [ ] `cd web && npm run test:contracts` (if relation types affect contract package)

---

## Verification log

| Command | Status | Date |
|---------|--------|------|
| `python scripts/verify_phase_completion.py` | PASS (9/9) | 2026-06-03 |
| `pytest tests/test_bridge_contract.py -k relation` | PASS 11 | 2026-06-03 |
| `cd web && npm run lint` | PASS | 2026-06-03 |

## Implementation status

**Done** (2026-06-03) on `feat/pr50-relation-v2` — merge + roadmap **Done** pending PR.
