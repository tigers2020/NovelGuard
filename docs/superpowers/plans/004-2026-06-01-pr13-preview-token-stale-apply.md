# PR-13: Preview Token & Stale Apply Contract — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enforce preview-token and stale-apply invariants on `getMovePreview` / `applyResolvedActions` / `discardMovePreview` across TS bridge, mock simulation, `ApplySubflowDialog`, and Python `BridgeApi` stubs — without real filesystem move/delete.

**Architecture:** `MovePreviewResult` carries `previewToken`, `libraryRevision`, and `selectionFingerprint` (SHA-256 of canonical normalized `SelectionScope`). Bridge holds a single `pendingPreview` slot. UI disables stale apply; bridge rejects with `BridgeCallError` (`code: "rejected"`, `reason: PreviewApplyErrorCode`). `discardMovePreview` is idempotent lifecycle cleanup on dialog close. `ResolveSnapshot.libraryRevision` is required for library stale detection.

**Tech Stack:** React 19, TypeScript, Vitest, Playwright, Python 3.12, pytest, pywebview bridge.

**Spec:** [01-2026-06-01-pr13-preview-token-stale-apply-design.md](../specs/01-2026-06-01-pr13-preview-token-stale-apply-design.md) (approved)

**Parent plans:** PR-0..12 done per `000` / `001` / `002` / `003` status tables.

**Test policy:** Extend **existing** test files only (`tests/test_bridge_contract.py`, `web/src/contracts/*.test.ts`, `web/src/bridge/bridgeParity.test.ts`, `web/src/types/selection.test.ts`, `web/e2e/smoke.spec.ts`). Do **not** add new `*.test.ts` / `test_*.py` without user `TEST_ALLOWED`.

**Non-goals (PR-13):** Real FS move/delete, Finalize apply, PR-14 packaging, AG Grid, DESIGN.md color tokens, changing PR-10 query page validators except move-preview/apply/discard shapes.

## Implementation status

| Item | Status |
|------|--------|
| PR-13 Tasks 1–12 | **Done** |

**Verification (2026-06-01):** `npm run build` PASS · `npm run test:contracts` 30/30 · `npm run test:e2e` 11/11 · `pytest` 17/17 · `python scripts/verify_phase_completion.py` PASS

---

## File map

| File | Responsibility |
|------|----------------|
| `web/src/types/movePreview.ts` | `MovePreviewResult`, requests, `PreviewApplyErrorCode` |
| `web/src/types/snapshot.ts` | `ResolveSnapshot.libraryRevision` required |
| `web/src/bridge/bridgeErrors.ts` | `BridgeCallError.reason?: PreviewApplyErrorCode` |
| `web/src/bridge/selectionFingerprint.ts` | Normalize + SHA-256 hex (Node `crypto`) |
| `web/src/bridge/NovelGuardBridge.ts` | Updated method signatures |
| `web/src/bridge/mockBridge.ts` | `pendingPreview`, revision bumps, invariant simulation |
| `web/src/bridge/pywebviewBridge.ts` | Wire new shapes + `discard_move_preview` |
| `web/src/bridge/testBridge.ts` | Pass-through discard; fail modes if needed |
| `web/src/contracts/movePreviewContract.ts` | Validate preview/apply/discard payloads |
| `web/src/contracts/snapshotContract.ts` | Require `work.resolve.libraryRevision` |
| `web/src/contracts/bridgeParity.ts` | Add `discardMovePreview` / `discard_move_preview` |
| `web/src/contracts/fixtures.ts` | `libraryRevision: 0` on resolve |
| `web/src/features/work/ApplySubflowDialog.tsx` | `PreviewState`, discard on close, stale UI |
| `src/app/selection_fingerprint.py` | Mirror TS fingerprint |
| `src/app/bridge_contract.py` | Extended validators + `PreviewApplyError` |
| `src/app/bridge_api.py` | Token guard, no-op apply, discard |
| `tests/fixtures/bridge_contract_fixtures.py` | `libraryRevision` on resolve |
| `tests/test_bridge_contract.py` | PR-13 pytest cases (extend) |
| `web/e2e/smoke.spec.ts` | Discard + stale selection paths |
| `docs/entry_points.md` | Bridge methods note |

---

## Acceptance criteria

```text
✓ getMovePreview returns previewToken, libraryRevision, selectionFingerprint, rows, summary
✓ applyResolvedActions({ selection, previewToken }) required; rejects all PreviewApplyErrorCode cases
✓ discardMovePreview idempotent on mismatch; clears hasPendingApply
✓ ResolveSnapshot.libraryRevision required in snapshot validators (TS + Python)
✓ selectionFingerprint identical for same scope in TS and Python (golden vectors in pytest/vitest)
✓ ApplySubflowDialog: cancel/close calls discard; stale selection disables apply
✓ npm run build && npm run test:contracts && npm run test:e2e pass
✓ pytest tests/test_bridge_contract.py pass
✓ python scripts/verify_phase_completion.py pass
✓ No filesystem move/delete in PR-13
```

---

### Task 1: Types + `BridgeCallError.reason`

**Files:**
- Create: `web/src/types/movePreview.ts`
- Modify: `web/src/bridge/bridgeErrors.ts`
- Modify: `web/src/bridge/NovelGuardBridge.ts`

- [ ] **Step 1: Create `movePreview.ts`**

```typescript
import type { SelectionScope } from "./selection";

export type PreviewApplyErrorCode =
  | "MISSING_PREVIEW_TOKEN"
  | "INVALID_PREVIEW_TOKEN"
  | "NO_PENDING_APPLY"
  | "STALE_PREVIEW"
  | "SELECTION_CHANGED";

export interface MovePreviewRow {
  id: string;
  action: string;
}

export interface MovePreviewSummary {
  rowCount: number;
  conflictCount?: number;
}

export interface MovePreviewResult {
  previewToken: string;
  libraryRevision: number;
  selectionFingerprint: string;
  hasPendingApply: true;
  rows: MovePreviewRow[];
  summary: MovePreviewSummary;
}

export interface ApplyResolvedActionsRequest {
  selection: SelectionScope;
  previewToken: string;
}

export interface DiscardMovePreviewRequest {
  previewToken: string;
}
```

- [ ] **Step 2: Extend `bridgeErrors.ts`**

```typescript
import type { PreviewApplyErrorCode } from "../types/movePreview";

export class BridgeCallError extends Error {
  readonly code: BridgeErrorCode;
  readonly method: string;
  readonly reason?: PreviewApplyErrorCode;
  // constructor: add optional reason?: PreviewApplyErrorCode to options
}
```

- [ ] **Step 3: Update `NovelGuardBridge.ts`**

```typescript
import type {
  ApplyResolvedActionsRequest,
  DiscardMovePreviewRequest,
  MovePreviewResult,
} from "../types/movePreview";

getMovePreview(selection: SelectionScope): Promise<MovePreviewResult>;
applyResolvedActions(request: ApplyResolvedActionsRequest): Promise<void>;
discardMovePreview(request: DiscardMovePreviewRequest): Promise<void>;
```

- [ ] **Step 4: Build**

```bash
cd f:/Python_Projects/NovelGuard/web && npm run build
```

Expected: FAIL until callers updated (Tasks 4–6).

- [ ] **Step 5: Commit**

```bash
git add web/src/types/movePreview.ts web/src/bridge/bridgeErrors.ts web/src/bridge/NovelGuardBridge.ts
git commit -m "[web] PR-13 move preview types and bridge interface"
```

---

### Task 2: `selectionFingerprint` (TS) + golden vectors

**Files:**
- Create: `web/src/bridge/selectionFingerprint.ts`
- Modify: `web/src/types/selection.test.ts`

- [ ] **Step 1: Implement normalization + hash**

```typescript
import { createHash } from "node:crypto";
import type { ReviewRowsQuery } from "../types/review";
import type { SelectionScope } from "../types/selection";

function normalizeReviewRowsQuery(query: ReviewRowsQuery): ReviewRowsQuery {
  return {
    viewMode: query.viewMode,
    filters: query.filters ?? {},
    cursor: query.cursor ?? null,
    limit: query.limit ?? 100,
    ...(query.sort ? { sort: query.sort } : {}),
  };
}

export function normalizeSelectionScope(selection: SelectionScope): SelectionScope {
  if (selection.type === "explicit_rows") {
    return { type: "explicit_rows", rowIds: [...selection.rowIds].sort() };
  }
  return {
    type: "current_query",
    query: normalizeReviewRowsQuery(selection.query),
    excludeRowIds: [...selection.excludeRowIds].sort(),
  };
}

function canonicalJson(value: unknown): string {
  if (value === null || typeof value !== "object") {
    return JSON.stringify(value);
  }
  if (Array.isArray(value)) {
    return `[${value.map((v) => canonicalJson(v)).join(",")}]`;
  }
  const obj = value as Record<string, unknown>;
  const keys = Object.keys(obj).sort();
  const pairs = keys
    .filter((k) => obj[k] !== undefined)
    .map((k) => `${JSON.stringify(k)}:${canonicalJson(obj[k])}`);
  return `{${pairs.join(",")}}`;
}

export function selectionFingerprint(selection: SelectionScope): string {
  const normalized = normalizeSelectionScope(selection);
  const payload = canonicalJson(normalized);
  return createHash("sha256").update(payload, "utf8").digest("hex");
}
```

- [ ] **Step 2: Add golden tests to `selection.test.ts`**

```typescript
import { describe, expect, it } from "vitest";
import { selectionFingerprint } from "../bridge/selectionFingerprint";

describe("selectionFingerprint", () => {
  it("matches stable hex for explicit_rows", () => {
    const fp = selectionFingerprint({ type: "explicit_rows", rowIds: ["b", "a"] });
    expect(fp).toMatch(/^[a-f0-9]{64}$/);
    expect(selectionFingerprint({ type: "explicit_rows", rowIds: ["a", "b"] })).toBe(fp);
  });

  it("differs when viewMode changes", () => {
    const a = selectionFingerprint({
      type: "current_query",
      query: { viewMode: "action" },
      excludeRowIds: [],
    });
    const b = selectionFingerprint({
      type: "current_query",
      query: { viewMode: "conflicts" },
      excludeRowIds: [],
    });
    expect(a).not.toBe(b);
  });
});
```

- [ ] **Step 3: Run**

```bash
cd web && npm run test:contracts
```

- [ ] **Step 4: Commit**

```bash
git commit -m "[web] PR-13 selectionFingerprint SHA-256 util"
```

---

### Task 3: `ResolveSnapshot.libraryRevision` + snapshot validators

**Files:**
- Modify: `web/src/types/snapshot.ts`
- Modify: `web/src/contracts/snapshotContract.ts`
- Modify: `web/src/contracts/fixtures.ts`
- Modify: `web/src/bridge/mockBridge.ts` (`buildSnapshot` only — `libraryRevision: 0` initial)
- Modify: `tests/fixtures/bridge_contract_fixtures.py`
- Modify: `src/app/bridge_contract.py` (if snapshot validation exists; else `bridge_api.get_snapshot` payload)

- [ ] **Step 1: Add field to `ResolveSnapshot`**

```typescript
export interface ResolveSnapshot {
  queueCount: number;
  groupCount: number;
  conflictCount: number;
  approvedCount: number;
  hasPendingApply: boolean;
  libraryRevision: number;
}
```

- [ ] **Step 2: Validate in `snapshotContract.ts`**

After `work` object check:

```typescript
const resolve = (snapshot.work as Record<string, unknown>).resolve;
if (!isRecord(resolve) || typeof resolve.libraryRevision !== "number") {
  throw new SnapshotContractError("ResolveSnapshot.libraryRevision must be a number");
}
```

- [ ] **Step 3: Fixtures — TS + Python**

Add `libraryRevision: 0` to `validAppSnapshot.work.resolve` and `VALID_SNAPSHOT["work"]["resolve"]`.

- [ ] **Step 4: mockBridge `state.libraryRevision = 0` and include in `resolve` block**

- [ ] **Step 5: Python `get_snapshot` return dict includes `"libraryRevision": 0`**

- [ ] **Step 6: Commit**

```bash
git commit -m "[web] PR-13 required ResolveSnapshot.libraryRevision"
```

---

### Task 4: Move preview contract + bridge parity

**Files:**
- Create: `web/src/contracts/movePreviewContract.ts`
- Modify: `web/src/contracts/bridgeParity.ts`
- Modify: `web/src/contracts/bridgeParity.test.ts` (if exists) or extend `bridgeParity` usage in tests

- [ ] **Step 1: `movePreviewContract.ts`**

```typescript
import type { MovePreviewResult } from "../types/movePreview";
import { SnapshotContractError } from "./snapshotContract";

export class MovePreviewContractError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "MovePreviewContractError";
  }
}

export function validateMovePreviewResult(payload: unknown): asserts payload is MovePreviewResult {
  if (typeof payload !== "object" || payload === null) {
    throw new MovePreviewContractError("MovePreviewResult must be an object");
  }
  const p = payload as Record<string, unknown>;
  for (const key of [
    "previewToken",
    "libraryRevision",
    "selectionFingerprint",
    "hasPendingApply",
    "rows",
    "summary",
  ]) {
    if (!(key in p)) throw new MovePreviewContractError(`missing ${key}`);
  }
  if (typeof p.previewToken !== "string" || p.previewToken.length === 0) {
    throw new MovePreviewContractError("previewToken invalid");
  }
  if (typeof p.libraryRevision !== "number") {
    throw new MovePreviewContractError("libraryRevision must be number");
  }
  if (p.hasPendingApply !== true) {
    throw new MovePreviewContractError("hasPendingApply must be true on preview");
  }
  if (!Array.isArray(p.rows)) {
    throw new MovePreviewContractError("rows must be array");
  }
}
```

- [ ] **Step 2: Update parity lists**

```typescript
"discardMovePreview",
// PYWEBVIEW:
"discard_move_preview",
```

- [ ] **Step 3: Extend `bridgeParity.test.ts`**

```typescript
expect(NOVEL_GUARD_BRIDGE_METHODS).toContain("discardMovePreview");
expect(PYWEBVIEW_API_METHODS).toContain("discard_move_preview");
```

- [ ] **Step 4: Run `npm run test:contracts`**

- [ ] **Step 5: Commit**

---

### Task 5: `mockBridge` pending preview simulation

**Files:**
- Modify: `web/src/bridge/mockBridge.ts`

- [ ] **Step 1: Bridge state**

```typescript
import { selectionFingerprint } from "./selectionFingerprint";
import { validateMovePreviewResult } from "../contracts/movePreviewContract";
import type { ApplyResolvedActionsRequest, MovePreviewResult } from "../types/movePreview";
import { BridgeCallError } from "./bridgeErrors";

let libraryRevision = 0;
let pendingPreview: {
  token: string;
  libraryRevision: number;
  selectionFingerprint: string;
  rows: MovePreviewRow[];
} | null = null;

function rejectApply(method: string, reason: PreviewApplyErrorCode): never {
  throw new BridgeCallError(`Apply rejected: ${reason}`, {
    code: "rejected",
    method,
    reason,
  });
}

function makePreviewToken(): string {
  return `preview-${crypto.randomUUID()}`;
}
```

(`crypto.randomUUID()` in browser; use `import { randomUUID } from "node:crypto"` in mock if needed.)

- [ ] **Step 2: `getMovePreview`**

- `validateSelectionScope(selection)`
- Compute `fp = selectionFingerprint(selection)`
- `const token = makePreviewToken()`
- `pendingPreview = { token, libraryRevision, selectionFingerprint: fp, rows }`
- `state.hasPendingApply = true`
- Build `MovePreviewResult` with `libraryRevision` from module var
- `validateMovePreviewResult(result)` before return

- [ ] **Step 3: `applyResolvedActions(request)`**

Validate order per spec; on success: `pendingPreview = null`, `state.hasPendingApply = false`.

- [ ] **Step 4: `discardMovePreview` — idempotent cleanup**

```typescript
async discardMovePreview(request: DiscardMovePreviewRequest): Promise<void> {
  if (pendingPreview && request.previewToken === pendingPreview.token) {
    pendingPreview = null;
  }
  state.hasPendingApply = false;
  // mismatch: no throw
}
```

Document in code comment: lifecycle cleanup, not mutation auth.

- [ ] **Step 5: Revision bump**

In `startScan` completion path (when mock sets pipeline idle success), `libraryRevision += 1` and invalidate: `pendingPreview = null`, `hasPendingApply = false`.

Optional E2E hook in `main.tsx` or mock:

```typescript
(window as unknown as { __NOVELGUARD_TEST_BUMP_REVISION__?: () => void }).__NOVELGUARD_TEST_BUMP_REVISION__ =
  () => { libraryRevision += 1; pendingPreview = null; state.hasPendingApply = false; };
```

- [ ] **Step 6: `npm run build`**

- [ ] **Step 7: Commit**

---

### Task 6: `ApplySubflowDialog` + App close wiring

**Files:**
- Modify: `web/src/features/work/ApplySubflowDialog.tsx`
- Modify: `web/src/app/App.tsx` (pass `libraryRevision` from snapshot if needed)

- [ ] **Step 1: Props**

```typescript
export function ApplySubflowDialog({
  open,
  selection,
  snapshotLibraryRevision,
  onClose,
}: {
  open: boolean;
  selection: SelectionScope | null;
  snapshotLibraryRevision: number;
  onClose: () => void;
}) {
```

- [ ] **Step 2: `PreviewState` + effects**

- On `selection` change while `ready`: compare `selectionFingerprint(selection)` to stored → `stale(selection_changed)`
- On `snapshotLibraryRevision !== ready.libraryRevision` while `ready` → `stale(library_changed)`
- `runApply`: `applyResolvedActions({ selection, previewToken: ready.token })`
- Catch `BridgeCallError` → show `apply-bridge-error`, map `reason` to Korean copy in plan table:

| reason | Message (ko) |
|--------|----------------|
| `STALE_PREVIEW` | 라이브러리가 변경되었습니다. 다시 미리보기하세요. |
| `SELECTION_CHANGED` | 선택이 변경되었습니다. 다시 미리보기하세요. |
| `NO_PENDING_APPLY` | 적용 가능한 미리보기가 없습니다. |
| default | 적용에 실패했습니다. |

- [ ] **Step 3: Close handler**

```typescript
const handleClose = async () => {
  if (previewState.status === "ready") {
    try {
      await bridge.discardMovePreview({ previewToken: previewState.token });
    } catch {
      // still close UI
    }
  }
  setPreviewState({ status: "idle" });
  onClose();
};
```

Wire Cancel and backdrop close to `handleClose`.

- [ ] **Step 4: Stale banner**

```tsx
{previewState.status === "stale" && (
  <p data-testid="apply-stale-banner" className="mt-3 text-sm text-warning" role="status">
    미리보기가 오래되었습니다. 다시 미리보기가 필요합니다.
  </p>
)}
```

Confirm apply button only when `previewState.status === "ready"`.

- [ ] **Step 5: `App.tsx`**

```tsx
<ApplySubflowDialog
  snapshotLibraryRevision={snapshot.work.resolve.libraryRevision}
  ...
/>
```

- [ ] **Step 6: Manual smoke + commit**

---

### Task 7: `pywebviewBridge` + `testBridge`

**Files:**
- Modify: `web/src/bridge/pywebviewBridge.ts`
- Modify: `web/src/bridge/testBridge.ts`

- [ ] **Step 1: Map methods**

```typescript
getMovePreview: (selection) =>
  callBridge(() => call<MovePreviewResult>(api, "get_move_preview", selection), {
    method: "get_move_preview",
  }),
applyResolvedActions: (request) =>
  callBridge(() => call<void>(api, "apply_resolved_actions", request), {
    method: "apply_resolved_actions",
  }),
discardMovePreview: (request) =>
  callBridge(() => call<void>(api, "discard_move_preview", request), {
    method: "discard_move_preview",
  }),
```

Parse Python errors into `BridgeCallError` with `reason` when payload includes `reason` field (extend `callBridge` or local wrapper).

- [ ] **Step 2: `testBridge` delegates discard to base**

- [ ] **Step 3: `npm run build`**

- [ ] **Step 4: Commit**

---

### Task 8: Python fingerprint + `BridgeApi` guards

**Files:**
- Create: `src/app/selection_fingerprint.py`
- Modify: `src/app/bridge_contract.py`
- Modify: `src/app/bridge_api.py`

- [ ] **Step 1: `selection_fingerprint.py`**

```python
import hashlib
import json
from typing import Any

def normalize_selection_scope(selection: dict[str, Any]) -> dict[str, Any]:
    # mirror TS: explicit_rows sorted rowIds; current_query normalized query
    ...

def selection_fingerprint(selection: dict[str, Any]) -> str:
    normalized = normalize_selection_scope(selection)
    payload = json.dumps(normalized, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
```

- [ ] **Step 2: `PreviewApplyError` in `bridge_contract.py`**

```python
class PreviewApplyError(Exception):
    def __init__(self, reason: str, message: str | None = None) -> None:
        self.reason = reason
        super().__init__(message or reason)
```

Extend `validate_move_preview` for new fields.

- [ ] **Step 3: `BridgeApi`**

```python
class BridgeApi:
    def __init__(self) -> None:
        self._library_revision = 0
        self._pending_apply: dict[str, Any] | None = None

    def get_move_preview(self, selection: dict[str, Any]) -> dict[str, Any]:
        validate_selection_scope(selection)
        token = f"preview-{uuid4()}"
        fp = selection_fingerprint(selection)
        rev = self._library_revision
        self._pending_apply = {"token": token, "fingerprint": fp, "library_revision": rev}
        payload = {
            "previewToken": token,
            "libraryRevision": rev,
            "selectionFingerprint": fp,
            "hasPendingApply": True,
            "rows": [{"id": "row-1", "action": "move_organized"}],
            "summary": {"rowCount": 1},
        }
        validate_move_preview(payload)
        return payload

    def apply_resolved_actions(self, payload: dict[str, Any]) -> None:
        # extract previewToken + selection; validate; no-op; clear _pending_apply

    def discard_move_preview(self, payload: dict[str, Any]) -> None:
        token = payload.get("previewToken")
        if self._pending_apply and self._pending_apply.get("token") == token:
            self._pending_apply = None
        # idempotent: never raise on mismatch
```

Ensure `get_snapshot()` resolve block includes `"libraryRevision": self._library_revision`.

- [ ] **Step 4: Golden vector test TS vs Python**

In `tests/test_bridge_contract.py`:

```python
from app.selection_fingerprint import selection_fingerprint

def test_selection_fingerprint_explicit_rows_stable() -> None:
    sel = {"type": "explicit_rows", "rowIds": ["a", "b"]}
    fp = selection_fingerprint(sel)
    assert len(fp) == 64
```

Add comment with TS-generated golden hex once Task 2 runs (paste value in both tests).

- [ ] **Step 5: Commit**

---

### Task 9: Vitest contract extensions

**Files:**
- Modify: `web/src/bridge/bridgeParity.test.ts`
- Modify: `web/src/types/selection.test.ts` (if not done Task 2)
- Optional: add cases to `web/src/contracts/snapshotContract.test.ts` if file exists, else extend nearest contract test

- [ ] **Step 1: Mock bridge invariant tests in `bridgeParity.test.ts`**

```typescript
import { mockBridge } from "./mockBridge";

it("apply without previewToken rejects", async () => {
  await expect(
    mockBridge.applyResolvedActions({
      selection: { type: "explicit_rows", rowIds: ["row-1"] },
      previewToken: "",
    }),
  ).rejects.toMatchObject({ reason: "MISSING_PREVIEW_TOKEN" });
});

it("apply after discard rejects NO_PENDING_APPLY", async () => {
  const sel = { type: "explicit_rows" as const, rowIds: ["row-1"] };
  const preview = await mockBridge.getMovePreview(sel);
  await mockBridge.discardMovePreview({ previewToken: preview.previewToken });
  await expect(mockBridge.applyResolvedActions({ selection: sel, previewToken: preview.previewToken })).rejects.toMatchObject({
    reason: "NO_PENDING_APPLY",
  });
});
```

Add stale fingerprint test: preview then apply with different `rowIds` → `SELECTION_CHANGED`.

- [ ] **Step 2: `npm run test:contracts`**

- [ ] **Step 3: Commit**

---

### Task 10: Pytest extensions

**Files:**
- Modify: `tests/test_bridge_contract.py`

- [ ] **Step 1: Add tests**

```python
def test_get_move_preview_returns_token_fields() -> None:
    api = BridgeApi()
    preview = api.get_move_preview({"type": "explicit_rows", "rowIds": ["row-1"]})
    assert "previewToken" in preview
    assert preview["hasPendingApply"] is True
    assert isinstance(preview["libraryRevision"], int)

def test_apply_missing_token_raises() -> None:
    api = BridgeApi()
    with pytest.raises(PreviewApplyError) as exc:
        api.apply_resolved_actions(
            {"selection": {"type": "explicit_rows", "rowIds": ["row-1"]}, "previewToken": ""}
        )
    assert exc.value.reason == "MISSING_PREVIEW_TOKEN"

def test_discard_idempotent_on_mismatch() -> None:
    api = BridgeApi()
    api.discard_move_preview({"previewToken": "unknown"})
```

- [ ] **Step 2: Run**

```bash
pytest tests/test_bridge_contract.py -v
```

- [ ] **Step 3: Commit**

---

### Task 11: E2E smoke paths

**Files:**
- Modify: `web/e2e/smoke.spec.ts`

- [ ] **Step 1: Keep existing `preview failure blocks apply`**

- [ ] **Step 2: Discard on close**

```typescript
test("closing apply dialog discards pending preview", async ({ page }) => {
  await page.goto("/");
  await page.getByTestId("work-mode-tab-resolve").click();
  await page.getByTestId("batch-preview-open").click();
  await page.getByTestId("apply-preview-run").click();
  await expect(page.getByTestId("apply-confirm-run")).toBeVisible();
  await page.getByRole("button", { name: "취소" }).click();
  // reopen preflight or snapshot-driven UI: hasPendingApply should not block orphan
  // optional: re-open dialog and confirm preview step again required
});
```

- [ ] **Step 3: Stale selection (change selection while dialog open)**

If hard in E2E: open dialog with explicit selection, then change grid selection via test hook — expect `apply-stale-banner` and no `apply-confirm-run`.

Simpler path: use `page.addInitScript` to call bump revision after preview, expect stale banner.

```typescript
test("library revision bump shows stale banner", async ({ page }) => {
  await page.goto("/");
  await page.getByTestId("work-mode-tab-resolve").click();
  await page.getByTestId("batch-preview-open").click();
  await page.getByTestId("apply-preview-run").click();
  await page.evaluate(() => (window as any).__NOVELGUARD_TEST_BUMP_REVISION__?.());
  await expect(page.getByTestId("apply-stale-banner")).toBeVisible();
  await expect(page.getByTestId("apply-confirm-run")).toHaveCount(0);
});
```

- [ ] **Step 4: Run**

```bash
cd web && npm run test:e2e
```

- [ ] **Step 5: Commit**

---

### Task 12: Docs + full verification

**Files:**
- Modify: `docs/entry_points.md`
- Modify: `docs/superpowers/plans/000-2026-06-01-novelguard-ui-overhaul.md` (status line PR-13 planned)

- [ ] **Step 1: `entry_points.md`**

Document:

- `get_move_preview` / `apply_resolved_actions` / `discard_move_preview`
- Note: PR-13 “token” = preview correlation id, not DESIGN.md color tokens

- [ ] **Step 2: Full verify**

```bash
cd f:/Python_Projects/NovelGuard/web && npm run lint && npm run build && npm run test:contracts && npm run test:e2e
pip install -e ".[dev]"
python scripts/verify_phase_completion.py
```

- [ ] **Step 3: Update plan status table at top of this file when done**

- [ ] **Step 4: Commit**

```bash
git commit -m "[docs] PR-13 entry points and verification"
```

---

## Spec coverage self-review

| Spec requirement | Plan task |
|------------------|-----------|
| `MovePreviewResult` fields | 1, 4, 5, 8 |
| `applyResolvedActions` request object | 1, 5, 6, 7, 8 |
| `discardMovePreview` idempotent cleanup | 5, 6, 8, 10 |
| Required `libraryRevision` on snapshot | 3, 6, 8 |
| SHA-256 fingerprint algorithm | 2, 8, 9, 10 |
| Invariant error codes | 5, 8, 9, 10 |
| UI dual guard + discard on close | 6, 11 |
| No FS mutation | Non-goals |
| Extend existing tests only | Test policy header |
| Not DESIGN color tokens | Task 12 |

---

## Plan changelog

| Date | Note |
|------|------|
| 2026-06-01 | Initial PR-13 plan from approved spec + reviewer hard locks |

---

## Execution handoff

Plan complete and saved to `docs/superpowers/plans/004-2026-06-01-pr13-preview-token-stale-apply.md`.

**Two execution options:**

1. **Subagent-Driven (recommended)** — fresh subagent per task, spec compliance review between tasks (`subagent-driven-development`).

2. **Inline Execution** — run tasks in this session with checkpoints (`executing-plans`).

Which approach?
