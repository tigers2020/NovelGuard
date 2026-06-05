# NOV-35: Preview Eligibility Near/Relation After Auto-Keeper — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Allow approved Near/Relation `move_duplicate` rows to enter move preview (and apply via preview token) after auto-keeper approval, by removing filter-level and selection-level type blocks while keeping row-level safety gates.

**Architecture:** Single row-level eligibility function in UI (`isExecutableMovePreviewRow`) drives preview enable/disable; Python preview/apply loops mirror the same rules (approved + move_duplicate + exact|near|relation + not conflict/excluded). Filter-level `reviewOnlyBlockedReasonForFilter` stays for bulk-exclude only, not preview.

**Tech Stack:** TypeScript (Vitest), Python 3.12 (pytest), React workspace, bridge contract tests, Playwright e2e smoke.

**Spec:** Linear NOV-35 `## Spec` comment (2026-06-05) + grill-me locked decisions below.

**Branch:** `ai/NOV-35-preview-eligibility-near-relation`

---

## Plan-locked decisions (grill-me APPROVED)

| Lock | Value |
|------|--------|
| Preview filter gate | **Remove** from `previewBlockedReason`; row-level only |
| Bulk exclude gate | **Keep** `reviewOnlyBlockedReasonForFilter` on `bulkQueryDisabled` |
| UI row eligibility | **Require** `status === "approved"` + `type in (exact, near, relation)` + existing action guards |
| Python preview loop | **Remove** lines 54–57 early throws; **Add** `status != "approved"` skip before building ops |
| Python apply | **Remove** per-op near/relation type throw (lines 55–58); preview token is gate |
| mockBridge | **Add** approved gate to match Python after change |
| DetailPanel banner | **Informational** — post-approve preview allowed; not hard block copy |
| Error codes | **Keep** in TS types; no longer thrown for approved near/relation |
| Docs/ADR | **Out of scope** unless copy contradicts merged behavior |
| PR scope | Preview + apply guard changes **same PR** |

---

## File map

| File | Action |
|------|--------|
| `web/src/features/work/resolve/previewEligibility.ts` | **Modify** — approved + type allowlist; optional rename guidance fn |
| `web/src/features/work/resolve/previewEligibility.test.ts` | **Modify** — row cases + filter fn guidance-only tests |
| `web/src/features/work/ResolveAndOrganizeWorkspace.tsx` | **Modify** — decouple preview from filter block; neutral fallback copy |
| `web/src/features/work/resolve/DetailPanel.tsx` | **Modify** — NOV-29 banner copy |
| `src/app/build_preview_plan.py` | **Modify** — remove selection throws; add approved gate |
| `src/app/apply_resolved_actions.py` | **Modify** — remove type throws |
| `web/src/bridge/mockBridge.ts` | **Modify** — approved gate in `buildMockPreviewPlan` |
| `web/src/bridge/mockData.ts` | **Modify** — fixture row for approved near/relation e2e |
| `tests/test_bridge_contract.py` | **Modify** — replace near/relation reject tests with approve-then-preview |
| `web/src/bridge/bridgeParity.test.ts` | **Modify** — near/relation approved preview parity |
| `web/e2e/smoke.spec.ts` | **Modify** — NOV-19/22 near/all scenarios after approve fixture |

---

### Task 1: Tighten UI row eligibility

**Files:**
- Modify: `web/src/features/work/resolve/previewEligibility.ts`
- Test: `web/src/features/work/resolve/previewEligibility.test.ts`

- [ ] **Step 1: Write failing tests**

Add to `previewEligibility.test.ts`:

```typescript
const ELIGIBLE_TYPES = ["exact", "near", "relation"] as const;

describe("isExecutableMovePreviewRow type and approval gates", () => {
  it.each(ELIGIBLE_TYPES)("accepts approved %s move_duplicate", (type) => {
    expect(isExecutableMovePreviewRow(fileRow({ type, status: "approved" }))).toBe(true);
  });

  it.each(ELIGIBLE_TYPES)("rejects unapproved %s move_duplicate", (type) => {
    expect(isExecutableMovePreviewRow(fileRow({ type, status: "unreviewed" }))).toBe(false);
  });

  it("rejects move_only even when approved", () => {
    expect(
      isExecutableMovePreviewRow(
        fileRow({ type: "move_only", status: "approved", proposedAction: "move_duplicate" }),
      ),
    ).toBe(false);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd web && npm run test -- src/features/work/resolve/previewEligibility.test.ts -v`
Expected: FAIL — unapproved near passes today

- [ ] **Step 3: Implement**

In `previewEligibility.ts`, update `isExecutableMovePreviewRow`:

```typescript
const PREVIEW_ELIGIBLE_TYPES: ReadonlySet<ReviewRow["type"]> = new Set([
  "exact",
  "near",
  "relation",
]);

export function isExecutableMovePreviewRow(row: ReviewRow): boolean {
  if (row.rowKind !== "file") return false;
  if (row.status !== "approved") return false;
  if (row.status === "excluded" || row.status === "conflict") return false;
  if (!PREVIEW_ELIGIBLE_TYPES.has(row.type)) return false;
  if (row.proposedAction === "keep" || row.proposedAction === "ignore") return false;
  if (row.proposedAction === "move_organized") return false;
  return row.proposedAction === "move_duplicate";
}
```

Note: after `status !== "approved"`, excluded/conflict checks are redundant but kept for clarity matching spec.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd web && npm run test -- src/features/work/resolve/previewEligibility.test.ts -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add web/src/features/work/resolve/previewEligibility.ts web/src/features/work/resolve/previewEligibility.test.ts
git commit -m "feat(nov-35): require approved exact/near/relation for move preview rows"
```

---

### Task 2: Decouple preview from filter block

**Files:**
- Modify: `web/src/features/work/ResolveAndOrganizeWorkspace.tsx:271-285`

- [ ] **Step 1: Write failing test**

Add to `previewEligibility.test.ts` (documents expected workspace behavior):

```typescript
import { reviewOnlyBlockedReasonForFilter } from "./previewEligibility";

it("filter block reason exists for near but must not gate preview (workspace uses row check)", () => {
  expect(reviewOnlyBlockedReasonForFilter("near")).toBeDefined();
  // Workspace previewBlockedReason must NOT return this — verified in Task 2 integration via e2e
});
```

- [ ] **Step 2: Modify workspace**

In `ResolveAndOrganizeWorkspace.tsx`, change `previewBlockedReason`:

```typescript
const previewBlockedReason = useMemo(() => {
  if (filteredCount === 0) {
    return "현재 필터에 표시된 항목이 없습니다.";
  }
  if (!hasExecutableRows) {
    return "현재 필터에 이동 미리보기 가능한 항목이 없습니다. 승인된 이동 대상을 확인한 뒤 다시 시도하세요.";
  }
  return undefined;
}, [filteredCount, hasExecutableRows]);
```

Keep `reviewOnlyBlockedReason` + `bulkQueryDisabled` unchanged.

- [ ] **Step 3: Run vitest**

Run: `cd web && npm run test -- src/features/work/resolve/previewEligibility.test.ts -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add web/src/features/work/ResolveAndOrganizeWorkspace.tsx web/src/features/work/resolve/previewEligibility.test.ts
git commit -m "feat(nov-35): preview enable uses row eligibility not filter type"
```

---

### Task 3: Update DetailPanel guidance copy

**Files:**
- Modify: `web/src/features/work/resolve/DetailPanel.tsx:101-103`

- [ ] **Step 1: Update banner strings**

```typescript
{rowType === "near"
  ? "Near duplicate 그룹입니다. 승인 후 이동 미리보기·적용이 가능합니다."
  : "Relation 그룹입니다. 승인 후 이동 미리보기·적용이 가능합니다."}
```

- [ ] **Step 2: Lint**

Run: `cd web && npm run lint`
Expected: exit 0

- [ ] **Step 3: Commit**

```bash
git add web/src/features/work/resolve/DetailPanel.tsx
git commit -m "docs(nov-35): update near/relation detail banner for post-approve preview"
```

---

### Task 4: Python preview — remove selection throw, add approved gate

**Files:**
- Modify: `src/app/build_preview_plan.py:13-16,54-57,63-79`
- Test: `tests/test_bridge_contract.py`

- [ ] **Step 1: Write failing contract test**

Replace `test_preview_rejects_near_duplicate_rows` body:

```python
def test_preview_accepts_approved_near_duplicate_rows(tmp_path: Path) -> None:
    (tmp_path / "alpha.txt").write_text(_near_similar_body("alpha"), encoding="utf-8")
    (tmp_path / "beta.txt").write_text(_near_similar_body("beta"), encoding="utf-8")
    session = create_library_session(MemoryLibraryIndex())
    session.select_folder(str(tmp_path))
    api = create_bridge_api(session)
    api.start_scan()
    _scan_until_idle(api)
    near_page = api.query_review_rows(
        {"viewMode": "all", "limit": 50, "filters": {"types": ["near"]}}
    )
    file_row = next((row for row in near_page["rows"] if row["rowKind"] == "file"), None)
    if file_row is None:
        return
    api.update_review_decisions(
        {
            "selection": {"type": "explicit_rows", "rowIds": [file_row["id"]]},
            "command": "approve",
        }
    )
    preview = api.get_move_preview({"type": "explicit_rows", "rowIds": [file_row["id"]]})
    assert preview["rows"]
    assert preview["rows"][0]["action"] == "move_duplicate"
```

Replace `test_preview_rejects_relation_rows` similarly with approve + success.

Add unapproved still blocked test:

```python
def test_preview_skips_unapproved_near_duplicate_rows(tmp_path: Path) -> None:
    # ... same setup without approve ...
    preview = api.get_move_preview({"type": "explicit_rows", "rowIds": [file_row["id"]]})
    assert preview["rows"] == []
```

- [ ] **Step 2: Run test — expect FAIL**

Run: `pytest tests/test_bridge_contract.py::test_preview_accepts_approved_near_duplicate_rows -v`
Expected: FAIL with `NEAR_DUPLICATE_APPLY_UNSUPPORTED`

- [ ] **Step 3: Implement**

Remove imports and early throws:

```python
# Delete selection_includes_near_rows, selection_includes_relation_rows imports
# Delete lines 54-57
```

In per-row loop, after conflict skip, add:

```python
if status != "approved":
    blocked_count += 1
    continue
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_bridge_contract.py -k "preview_accepts_approved_near or preview_accepts_approved_relation or preview_skips_unapproved_near" -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/app/build_preview_plan.py tests/test_bridge_contract.py
git commit -m "feat(nov-35): allow approved near/relation in preview plan build"
```

---

### Task 5: Python apply — remove type guard

**Files:**
- Modify: `src/app/apply_resolved_actions.py:53-58`
- Test: extend bridge contract apply test for near/relation

- [ ] **Step 1: Write failing apply test**

Add after near preview success test pattern:

```python
def test_apply_succeeds_for_approved_near_after_preview(tmp_path: Path) -> None:
    # setup + approve + get_move_preview + apply_resolved_actions
    # assert no NEAR_DUPLICATE_APPLY_UNSUPPORTED
```

Reuse existing exact apply test structure from `test_apply_resolved_actions_*` in same file.

- [ ] **Step 2: Run — expect FAIL if near type in plan**

Run: `pytest tests/test_bridge_contract.py::test_apply_succeeds_for_approved_near_after_preview -v`

- [ ] **Step 3: Remove type throws**

Delete lines 55-58 in `apply_resolved_actions.py` (the `row.get("type") == "near"` / `"relation"` checks).

- [ ] **Step 4: Run test — PASS**

- [ ] **Step 5: Commit**

```bash
git add src/app/apply_resolved_actions.py tests/test_bridge_contract.py
git commit -m "feat(nov-35): allow apply for near/relation rows from valid preview"
```

---

### Task 6: mockBridge parity

**Files:**
- Modify: `web/src/bridge/mockBridge.ts:331-350`
- Test: `web/src/bridge/bridgeParity.test.ts`

- [ ] **Step 1: Add approved gate to buildMockPreviewPlan**

After conflict skip:

```typescript
if (row.status !== "approved") {
  blockedCount += 1;
  continue;
}
if (!["exact", "near", "relation"].includes(row.type)) {
  blockedCount += 1;
  continue;
}
```

- [ ] **Step 2: Add parity test**

```typescript
it("mockBridge getMovePreview includes approved near move_duplicate rows", async () => {
  const nearRow = getAllReviewRows().find(
    (r) => r.type === "near" && r.rowKind === "file" && r.proposedAction === "move_duplicate",
  );
  // mutate or seed approved near row fixture if needed
  // assert preview.rows.length >= 1
});
```

Update `mockData.ts` comment + ensure at least one deterministic approved near/relation `move_duplicate` file row (e.g. dedicated index like row-2 pattern).

- [ ] **Step 3: Run**

Run: `cd web && npm run test -- src/bridge/bridgeParity.test.ts -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add web/src/bridge/mockBridge.ts web/src/bridge/mockData.ts web/src/bridge/bridgeParity.test.ts
git commit -m "feat(nov-35): mockBridge preview parity for approved near/relation"
```

---

### Task 7: E2E smoke updates

**Files:**
- Modify: `web/e2e/smoke.spec.ts:253-282`

- [ ] **Step 1: Replace disabled-only near test**

Change `NOV-19 preview disabled when filter has no executable rows`:
- Near filter with **no approved** rows → preview disabled with new neutral message (no executable rows)
- Add sibling test: near filter + approved fixture → preview **enabled**

- [ ] **Step 2: Replace all-types disabled test**

`NOV-22 verify all types filter disables preview` → split:
- Unapproved mixed → disabled (no executable rows message)
- Approved near/relation in mock → enabled

- [ ] **Step 3: Run e2e**

Run: `cd web && npm run test:e2e -- smoke.spec.ts -g "NOV-19|NOV-22"`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add web/e2e/smoke.spec.ts
git commit -m "test(nov-35): e2e near/all preview after approve fixture"
```

---

### Task 8: Full verification

- [ ] **Step 1: Scoped tests**

```bash
cd web && npm run test -- src/features/work/resolve/previewEligibility.test.ts src/bridge/bridgeParity.test.ts -v
pytest tests/test_bridge_contract.py -k "preview or apply_succeeds_for_approved_near" -v
cd web && npm run lint
cd web && npm run test:contracts
```

Expected: all exit 0

- [ ] **Step 2: Phase script**

```bash
python scripts/verify_phase_completion.py
```

Expected: exit 0

---

## Spec coverage checklist

| Requirement | Task |
|-------------|------|
| R1 UI preview row-level | Task 2 |
| R2 isExecutableMovePreviewRow | Task 1 |
| R3 BuildPreviewPlanUseCase | Task 4 |
| R4 ApplyResolvedActionsUseCase | Task 5 |
| R5 Copy/guidance | Task 3 |
| R6 Tests | Tasks 1,4,5,6,7 |
| Same PR preview+apply | Tasks 4+5 |
