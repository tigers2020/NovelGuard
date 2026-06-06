# Apply Preview Display Rows — Implementation Plan

> **Status:** `draft` / **not executed on main**
> **WIP code:** `wip/mixed-035-036-salvage` (commit `ee7b6aa7`) — after stabilization merges, use `git restore --source wip/mixed-035-036-salvage -- <036 code paths only>` on `feature/apply-preview-display-rows`. **Do not** `git cherry-pick ee7b6aa7` (mixed docs + code).
> **Do not run this plan on `main` until spec 036 is re-approved post-stabilization.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show filename and `sourcePath → destPath` in the Apply subflow confirm table instead of opaque row IDs.

**Architecture:** Enrich `get_move_preview` `rows[]` in `BuildPreviewPlanUseCase` with display fields already available on `PreviewOperation` / `FileRecord`. Validate on Python and TS contract layers. Update `PreviewRowsTable` only — apply token and `PreviewOperation` execution unchanged.

**Tech Stack:** Python 3.12 (`src/`), React 19 + TypeScript + Vitest (`web/`), pytest, Playwright e2e.

**Spec:** [036-2026-06-05-apply-preview-display-rows-design.md](../specs/036-2026-06-05-apply-preview-display-rows-design.md) (draft — re-approve after stabilization)

**Test policy:** Extend **existing** files only (`tests/test_bridge_contract.py`, `web/src/bridge/bridgeParity.test.ts`, `web/e2e/smoke.spec.ts`). Do **not** add new `*.test.ts` / `test_*.py` without user `TEST_ALLOWED`.

---

## File map

| File | Responsibility |
|------|----------------|
| `src/app/build_preview_plan.py` | Append `name`, `sourcePath`, `destPath` to each preview row |
| `src/app/bridge_contract.py` | `validate_move_preview` row field checks |
| `web/src/types/movePreview.ts` | Extend `MovePreviewRow` interface |
| `web/src/contracts/movePreviewContract.ts` | Validate display fields on each row |
| `web/src/bridge/mockBridge.ts` | Mock preview rows with display fields |
| `web/src/features/work/ApplySubflowDialog.tsx` | Confirm table columns + cell content |
| `tests/test_bridge_contract.py` | Python contract + integration assertions |
| `web/src/bridge/bridgeParity.test.ts` | Mock bridge display field assertions |
| `web/e2e/smoke.spec.ts` | Confirm step shows filename, not `file:` id prefix |

---

## Acceptance criteria

```text
✓ Preview rows include name, sourcePath, destPath (Python + mock bridge)
✓ validate_move_preview rejects rows missing display fields
✓ Confirm table headers: 파일 / 이동 경로 (not 행 ID / 동작)
✓ Table cells show name and sourcePath → destPath; row id not visible
✓ applyResolvedActions still succeeds with previewToken
✓ pytest tests/test_bridge_contract.py -q pass
✓ cd web && npm run test:contracts pass
✓ cd web && npm run lint pass (web touched)
```

---

### Task 1: Python contract — validate display fields on preview rows

**Files:**
- Modify: `src/app/bridge_contract.py` (after `validate_move_preview`)
- Modify: `tests/test_bridge_contract.py`

- [ ] **Step 1: Write failing test for missing display fields**

Add near other `validate_move_preview` tests in `tests/test_bridge_contract.py`:

```python
def test_validate_move_preview_requires_display_fields() -> None:
    payload = {
        "previewToken": "preview-1",
        "libraryRevision": 0,
        "selectionFingerprint": "abc",
        "hasPendingApply": True,
        "rows": [{"id": "file:x", "action": "move_duplicate"}],
        "summary": {"rowCount": 1, "operationCount": 1},
    }
    with pytest.raises(PageContractError, match="name"):
        validate_move_preview(payload)


def test_validate_move_preview_accepts_display_fields() -> None:
    payload = {
        "previewToken": "preview-1",
        "libraryRevision": 0,
        "selectionFingerprint": "abc",
        "hasPendingApply": True,
        "rows": [
            {
                "id": "file:x",
                "action": "move_duplicate",
                "name": "novel-a.txt",
                "sourcePath": "folder/novel-a.txt",
                "destPath": "duplicate/novel-a.txt",
            }
        ],
        "summary": {"rowCount": 1, "operationCount": 1},
    }
    validate_move_preview(payload)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_bridge_contract.py::test_validate_move_preview_requires_display_fields tests/test_bridge_contract.py::test_validate_move_preview_accepts_display_fields -v`

Expected: FAIL — `test_validate_move_preview_requires_display_fields` does not raise (validation not implemented yet).

- [ ] **Step 3: Implement row validation in `validate_move_preview`**

In `src/app/bridge_contract.py`, after the `rows` list type check:

```python
    rows = payload.get("rows")
    if not isinstance(rows, list):
        raise PageContractError("Move preview rows must be an array")
    for row in rows:
        if not isinstance(row, dict):
            raise PageContractError("Move preview row must be a dict")
        for key in ("id", "action", "name", "sourcePath", "destPath"):
            value = row.get(key)
            if not isinstance(value, str) or not value:
                raise PageContractError(f"Move preview row missing or empty {key}")
```

Remove duplicate `if not isinstance(payload.get("rows"), list)` if present — keep single check.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_bridge_contract.py::test_validate_move_preview_requires_display_fields tests/test_bridge_contract.py::test_validate_move_preview_accepts_display_fields -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/app/bridge_contract.py tests/test_bridge_contract.py
git commit -m "feat(bridge): require move preview row display fields"
```

---

### Task 2: Python preview builder — emit display fields

**Files:**
- Modify: `src/app/build_preview_plan.py:94`
- Modify: `tests/test_bridge_contract.py` (`test_real_move_preview_lists_duplicate_member`)

- [ ] **Step 1: Write failing integration assertion**

Extend `test_real_move_preview_lists_duplicate_member` in `tests/test_bridge_contract.py`:

```python
    row = preview["rows"][0]
    assert row["name"]
    assert row["sourcePath"]
    assert row["destPath"]
    assert "→" not in row["sourcePath"]  # paths are separate fields
    assert row["destPath"].endswith(row["name"]) or row["name"] in row["destPath"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_bridge_contract.py::test_real_move_preview_lists_duplicate_member -v`

Expected: FAIL — `KeyError: 'name'` or missing key assertion.

- [ ] **Step 3: Enrich preview row dict in `build_preview_plan.py`**

Replace line 94:

```python
            preview_rows.append({
                "id": op.row_id,
                "action": "move_duplicate",
                "name": file_record.name,
                "sourcePath": op.source_path,
                "destPath": op.dest_path,
            })
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_bridge_contract.py::test_real_move_preview_lists_duplicate_member -v`

Expected: PASS

- [ ] **Step 5: Run full bridge contract suite**

Run: `pytest tests/test_bridge_contract.py -q`

Expected: PASS (fix any other preview tests that now fail validation if mock payloads exist in tests).

- [ ] **Step 6: Commit**

```bash
git add src/app/build_preview_plan.py tests/test_bridge_contract.py
git commit -m "feat(apply): include filename and paths in move preview rows"
```

---

### Task 3: TypeScript types + contract validation

**Files:**
- Modify: `web/src/types/movePreview.ts`
- Modify: `web/src/contracts/movePreviewContract.ts`
- Modify: `web/src/bridge/bridgeParity.test.ts`

- [ ] **Step 1: Extend `MovePreviewRow` type**

In `web/src/types/movePreview.ts`:

```typescript
export interface MovePreviewRow {
  id: string;
  action: string;
  name: string;
  sourcePath: string;
  destPath: string;
}
```

- [ ] **Step 2: Write failing parity test for display fields**

Add to `web/src/bridge/bridgeParity.test.ts` inside the existing `getMovePreview includes approved move_duplicate rows` test (or new `it` block after it):

```typescript
  it("getMovePreview rows include display fields", async () => {
    await mockBridge.updateReviewDecisions({
      selection: { type: "explicit_rows", rowIds: ["row-2"] },
      command: "approve",
    });
    const preview = await mockBridge.getMovePreview({
      type: "explicit_rows",
      rowIds: ["row-2"],
    });
    const row = preview.rows.find((r) => r.id === "row-2");
    expect(row).toBeDefined();
    expect(row!.name.length).toBeGreaterThan(0);
    expect(row!.sourcePath.length).toBeGreaterThan(0);
    expect(row!.destPath.length).toBeGreaterThan(0);
  });
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd web && npm run test:contracts -- src/bridge/bridgeParity.test.ts -t "display fields"`

Expected: FAIL — `name` undefined or type error until mock + contract updated.

- [ ] **Step 4: Validate rows in `movePreviewContract.ts`**

After the `rows` array check in `validateMovePreviewResult`:

```typescript
  for (const row of p.rows) {
    if (typeof row !== "object" || row === null) {
      throw new MovePreviewContractError("row must be an object");
    }
    const r = row as Record<string, unknown>;
    for (const key of ["id", "action", "name", "sourcePath", "destPath"] as const) {
      if (typeof r[key] !== "string" || (r[key] as string).length === 0) {
        throw new MovePreviewContractError(`row missing or empty ${key}`);
      }
    }
  }
```

- [ ] **Step 5: Commit types + contract (mock still failing)**

```bash
git add web/src/types/movePreview.ts web/src/contracts/movePreviewContract.ts web/src/bridge/bridgeParity.test.ts
git commit -m "feat(web): extend move preview row contract with display fields"
```

---

### Task 4: Mock bridge — populate display fields

**Files:**
- Modify: `web/src/bridge/mockBridge.ts` (`buildMockPreviewPlan`)

- [ ] **Step 1: Add dest path helper (mirror Python)**

Above `buildMockPreviewPlan` in `mockBridge.ts`:

```typescript
function buildMoveDuplicateDestRelative(targetFolder: string, basename: string): string {
  const folder = targetFolder.trim().replace(/\\/g, "/").replace(/^\/|\/$/g, "");
  if (!folder) return basename;
  return `${folder}/${basename}`;
}
```

- [ ] **Step 2: Enrich mock preview rows**

Replace the `rows.push` line inside `buildMockPreviewPlan`:

```typescript
    const targetFolder = row.targetFolder ?? "duplicate/";
    const sourcePath = row.path ?? row.name;
  rows.push({
    id: row.id,
    action: "move_duplicate",
    name: row.name,
    sourcePath,
    destPath: buildMoveDuplicateDestRelative(targetFolder, row.name),
  });
```

- [ ] **Step 3: Run parity test**

Run: `cd web && npm run test:contracts -- src/bridge/bridgeParity.test.ts -t "display fields"`

Expected: PASS

- [ ] **Step 4: Run full contract tests**

Run: `cd web && npm run test:contracts`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add web/src/bridge/mockBridge.ts
git commit -m "feat(mock): populate move preview display fields"
```

---

### Task 5: UI — confirm table columns

**Files:**
- Modify: `web/src/features/work/ApplySubflowDialog.tsx` (`PreviewRowsTable`)

- [ ] **Step 1: Update table headers and cells**

Replace `PreviewRowsTable` thead/tbody in `ApplySubflowDialog.tsx`:

```tsx
        <thead className="sticky top-0 bg-surface-elevated text-on-surface-variant">
          <tr>
            <th className="px-3 py-2 font-semibold">파일</th>
            <th className="px-3 py-2 font-semibold">이동 경로</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr
              key={row.id}
              className="border-t border-outline"
              data-testid={`apply-preview-row-${row.id}`}
            >
              <td
                className="max-w-[12rem] truncate px-3 py-2 text-on-surface"
                title={row.name}
              >
                {row.name}
              </td>
              <td className="px-3 py-2 font-mono text-xs text-on-surface">
                {row.sourcePath} → {row.destPath}
              </td>
            </tr>
          ))}
        </tbody>
```

- [ ] **Step 2: Lint**

Run: `cd web && npm run lint`

Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add web/src/features/work/ApplySubflowDialog.tsx
git commit -m "feat(ui): show filename and move path in apply confirm table"
```

---

### Task 6: E2E — confirm step shows human-readable content

**Files:**
- Modify: `web/e2e/smoke.spec.ts`

- [ ] **Step 1: Add assertion after preview run**

In an existing apply flow test (e.g. after `clickApplyPreviewRun` or where `apply-preview-table` is visible), add:

```typescript
    const table = page.getByTestId("apply-preview-table");
    await expect(table).toBeVisible();
    await expect(table.getByRole("columnheader", { name: "파일" })).toBeVisible();
    await expect(table.getByRole("columnheader", { name: "이동 경로" })).toBeVisible();
    await expect(table.getByRole("columnheader", { name: "행 ID" })).toHaveCount(0);
    await expect(table.locator("tbody td").first()).not.toContainText(/^file:/);
```

Pick a test that already reaches confirm step with `operationCount > 0` (e.g. batch preview / apply smoke path using mock bridge).

- [ ] **Step 2: Run e2e**

Run: `cd web && npm run test:e2e -- -g "apply"`

Or the specific test name you extended.

Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add web/e2e/smoke.spec.ts
git commit -m "test(e2e): assert apply confirm table shows filename not row id"
```

---

### Task 7: Final verification

- [ ] **Step 1: Python bridge contracts**

Run: `pytest tests/test_bridge_contract.py -q`

Expected: exit 0

- [ ] **Step 2: Web contracts + lint**

Run: `cd web && npm run test:contracts && npm run lint`

Expected: exit 0

- [ ] **Step 3: Optional phase verify**

Run: `python scripts/verify_phase_completion.py`

Expected: exit 0

- [ ] **Step 4: Manual smoke (operator)**

1. Resolve → approved move_duplicate rows → 이동 계획 미리보기 → 미리보기
2. Confirm step lists **파일** names and `source → dest` paths
3. Apply succeeds

---

## Plan self-review (vs spec 036)

| Spec requirement | Task |
|------------------|------|
| Enrich `get_move_preview` rows | Task 2 |
| Python `validate_move_preview` | Task 1 |
| TS `validateMovePreviewResult` | Task 3 |
| Mock bridge display fields | Task 4 |
| UI columns 파일 / 이동 경로 | Task 5 |
| Row id hidden from primary UI | Task 5 |
| Apply path unchanged | No tasks touch apply use case |
| Contract + e2e tests | Tasks 1, 6, 7 |
| Summary chips unchanged | No task modifies `SummaryChips` |

No placeholders. Types consistent: `name`, `sourcePath`, `destPath` everywhere.
