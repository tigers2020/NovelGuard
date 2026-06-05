# NOV-27: Resolve counts split — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expose `moveReadyCount` and `reviewSignalCount` on `work.resolve` and render them in Resolve toolbar instead of aggregate "Queue".

**Architecture:** Reuse `finalize_blockers` type-scoped row counters in `review_snapshot_counts`, cache in `library_session`, emit via `dto_mapper`, validate in Python + TS snapshot contracts, wire toolbar props from snapshot. Legacy `queueCount` unchanged for preflight/finalize.

**Tech Stack:** Python 3.12 (`src/`), React+TS (`web/`), pytest, vitest, bridge contract validators.

**Spec:** [2026-06-05-nov-27-resolve-counts-move-ready-vs-review-only-signals-design.md](../specs/2026-06-05-nov-27-resolve-counts-move-ready-vs-review-only-signals-design.md)

**Branch:** `ai/NOV-27-resolve-counts-split` from `main`

---

## File map

| File | Responsibility |
|------|----------------|
| `src/application/review_snapshot_counts.py` | `resolve_insight_counts()` delegating to finalize helpers |
| `src/application/library_session.py` | Cache `_move_ready_count`, `_review_signal_count`; pass to `build_snapshot` |
| `src/application/dto_mapper.py` | New snapshot fields under `work.resolve` |
| `src/app/bridge_contract.py` | Require `moveReadyCount`, `reviewSignalCount` ints |
| `tests/fixtures/bridge_contract_fixtures.py` | Default `0` for new fields |
| `tests/test_bridge_contract.py` | Split-count snapshot assertion after near scan |
| `web/src/types/snapshot.ts` | `ResolveSnapshot` type extension |
| `web/src/contracts/snapshotContract.ts` | Runtime validation for new ints |
| `web/src/contracts/fixtures.ts` | Fixture defaults |
| `web/src/bridge/mockReviewState.ts` | `resolveInsightCounts()` for mocks |
| `web/src/bridge/mockBridge.ts` | Emit new fields on snapshot |
| `web/src/features/work/resolve/ResolveGridToolbar.tsx` | KO chips; drop Queue |
| `web/src/features/work/ResolveAndOrganizeWorkspace.tsx` | Pass new props |
| `web/src/features/work/resolve/ResolveGridToolbar.test.tsx` | Toolbar label unit test |

---

### Task 1: Python — `resolve_insight_counts`

**Files:**
- Modify: `src/application/review_snapshot_counts.py`
- Test: `tests/test_bridge_contract.py`

- [ ] **Step 1: Write the failing unit-style assertion in bridge contract test**

Add near end of `tests/test_bridge_contract.py`:

```python
def test_resolve_snapshot_split_counts_with_near_rows(tmp_path: Path) -> None:
    (tmp_path / "alpha.txt").write_text(_near_similar_body("alpha"), encoding="utf-8")
    (tmp_path / "beta.txt").write_text(_near_similar_body("beta"), encoding="utf-8")
    session = create_library_session(MemoryLibraryIndex())
    session.select_folder(str(tmp_path))
    api = create_bridge_api(session)
    api.start_scan()
    _wait_deep_analysis_complete(api)
    snap = api.get_snapshot()
    validate_app_snapshot(snap)
    resolve = snap["work"]["resolve"]
    assert resolve["moveReadyCount"] >= 0
    assert resolve["reviewSignalCount"] >= 0
    assert resolve["moveReadyCount"] + resolve["reviewSignalCount"] == resolve["queueCount"]
    if resolve["reviewSignalCount"] > 0:
        assert resolve["moveReadyCount"] < resolve["queueCount"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_bridge_contract.py::test_resolve_snapshot_split_counts_with_near_rows -v`  
Expected: FAIL — `KeyError: 'moveReadyCount'` or contract validation error

- [ ] **Step 3: Implement `resolve_insight_counts`**

In `src/application/review_snapshot_counts.py`:

```python
from application.finalize_blockers import (
    exact_unresolved_queue_count,
    near_unresolved_file_row_count,
    relation_unresolved_file_row_count,
)


def resolve_insight_counts(rows: list[dict[str, Any]]) -> tuple[int, int]:
    """Return (move_ready_count, review_signal_count) for unresolved file rows."""
    move_ready = exact_unresolved_queue_count(rows)
    review_signal = near_unresolved_file_row_count(rows) + relation_unresolved_file_row_count(rows)
    return move_ready, review_signal
```

- [ ] **Step 4: Re-run test** — still fails until Task 2–4 wired; proceed to Task 2.

---

### Task 2: Python — session cache + dto_mapper

**Files:**
- Modify: `src/application/library_session.py`
- Modify: `src/application/dto_mapper.py`

- [ ] **Step 1: Add instance fields in `LibrarySession.__init__`**

```python
self._move_ready_count = 0
self._review_signal_count = 0
```

Also reset in folder-clear path alongside `_queue_count = 0` (~line 814).

- [ ] **Step 2: Update `_refresh_resolve_counts`**

```python
from application.review_snapshot_counts import file_row_status_counts, resolve_insight_counts

def _refresh_resolve_counts(self) -> None:
    queue, approved, conflict = file_row_status_counts(self._review_rows_cache)
    move_ready, review_signal = resolve_insight_counts(self._review_rows_cache)
    self._queue_count = queue
    self._approved_count = approved
    self._conflict_count = conflict
    self._move_ready_count = move_ready
    self._review_signal_count = review_signal
```

- [ ] **Step 3: Extend `build_snapshot` signature and resolve dict**

In `dto_mapper.py` add params `move_ready_count: int = 0`, `review_signal_count: int = 0` and emit:

```python
"moveReadyCount": move_ready_count,
"reviewSignalCount": review_signal_count,
```

- [ ] **Step 4: Pass new args from `get_snapshot`**

In `library_session.get_snapshot()` `build_snapshot(...)` call add:

```python
move_ready_count=self._move_ready_count,
review_signal_count=self._review_signal_count,
```

- [ ] **Step 5: Run split test**

Run: `pytest tests/test_bridge_contract.py::test_resolve_snapshot_split_counts_with_near_rows -v`  
Expected: may still fail on contract validation — Task 3.

---

### Task 3: Contract validation + fixtures (Python)

**Files:**
- Modify: `src/app/bridge_contract.py`
- Modify: `tests/fixtures/bridge_contract_fixtures.py`

- [ ] **Step 1: Add validation after resolve `libraryRevision` check**

In `validate_app_snapshot`:

```python
for key in ("moveReadyCount", "reviewSignalCount"):
    value = resolve.get(key)
    if not isinstance(value, int) or value < 0:
        raise SnapshotContractError(f"ResolveSnapshot.{key} must be a non-negative int")
```

- [ ] **Step 2: Update `VALID_SNAPSHOT` fixture**

```python
"moveReadyCount": 0,
"reviewSignalCount": 0,
```

- [ ] **Step 3: Run tests**

Run: `pytest tests/test_bridge_contract.py::test_resolve_snapshot_split_counts_with_near_rows tests/test_bridge_contract.py::test_validate_app_snapshot_accepts_valid -v`  
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add src/application/review_snapshot_counts.py src/application/library_session.py src/application/dto_mapper.py src/app/bridge_contract.py tests/fixtures/bridge_contract_fixtures.py tests/test_bridge_contract.py
git commit -m "feat(NOV-27): expose move-ready and review-signal resolve counts"
```

---

### Task 4: Web types + contract + fixtures

**Files:**
- Modify: `web/src/types/snapshot.ts`
- Modify: `web/src/contracts/snapshotContract.ts`
- Modify: `web/src/contracts/fixtures.ts`
- Test: `web/src/contracts/snapshotContract.test.ts`

- [ ] **Step 1: Extend `ResolveSnapshot`**

```typescript
export interface ResolveSnapshot {
  queueCount: number;
  moveReadyCount: number;
  reviewSignalCount: number;
  groupCount: number;
  conflictCount: number;
  approvedCount: number;
  hasPendingApply: boolean;
  libraryRevision: number;
}
```

- [ ] **Step 2: Validate in `snapshotContract.ts`**

After `libraryRevision` check:

```typescript
for (const key of ["moveReadyCount", "reviewSignalCount"] as const) {
  const value = resolve[key];
  if (typeof value !== "number" || value < 0 || !Number.isInteger(value)) {
    throw new SnapshotContractError(`ResolveSnapshot.${key} must be a non-negative int`);
  }
}
```

- [ ] **Step 3: Update `validAppSnapshot` fixture**

```typescript
moveReadyCount: 0,
reviewSignalCount: 0,
```

- [ ] **Step 4: Run contract tests**

Run: `cd web && npm run test:contracts`  
Expected: PASS (or fail on mocks — Task 5)

---

### Task 5: Web mocks

**Files:**
- Modify: `web/src/bridge/mockReviewState.ts`
- Modify: `web/src/bridge/mockBridge.ts`

- [ ] **Step 1: Add `resolveInsightCounts` in `mockReviewState.ts`**

```typescript
export function resolveInsightCounts(rows: ReviewRow[]): {
  moveReadyCount: number;
  reviewSignalCount: number;
} {
  let moveReadyCount = 0;
  let reviewSignalCount = 0;
  for (const row of rows) {
    if (row.rowKind !== "file") continue;
    if (row.status !== "unreviewed" && row.status !== "conflict") continue;
    if (row.type === "exact") moveReadyCount += 1;
    else if (row.type === "near" || row.type === "relation") reviewSignalCount += 1;
  }
  return { moveReadyCount, reviewSignalCount };
}
```

- [ ] **Step 2: Emit in `mockBridge.ts` snapshot builder**

Where `counts = fileRowStatusCounts(...)`:

```typescript
const insight = resolveInsightCounts(reviewRows);
// resolve block:
moveReadyCount: insight.moveReadyCount,
reviewSignalCount: insight.reviewSignalCount,
```

Update both snapshot build sites (~lines 276 and 452).

- [ ] **Step 3: Run contract tests**

Run: `cd web && npm run test:contracts`  
Expected: PASS

---

### Task 6: Toolbar UI + unit test

**Files:**
- Modify: `web/src/features/work/resolve/ResolveGridToolbar.tsx`
- Modify: `web/src/features/work/ResolveAndOrganizeWorkspace.tsx`
- Create: `web/src/features/work/resolve/ResolveGridToolbar.test.tsx`

- [ ] **Step 1: Write failing toolbar test**

```typescript
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ResolveGridToolbar } from "./ResolveGridToolbar";

const baseProps = {
  moveReadyCount: 3,
  reviewSignalCount: 2,
  groupCount: 1,
  conflictCount: 0,
  approvedCount: 4,
  rowTypeFilter: "all" as const,
  onRowTypeFilterChange: vi.fn(),
  search: "",
  onSearchChange: vi.fn(),
  loading: false,
  queryError: null,
  onRetry: vi.fn(),
  onOpenFinalize: vi.fn(),
};

describe("ResolveGridToolbar", () => {
  afterEach(() => cleanup());

  it("renders move-ready and review-signal KO chips", () => {
    render(<ResolveGridToolbar {...baseProps} />);
    expect(screen.getByText("이동 대기")).toBeTruthy();
    expect(screen.getByText("참고 신호")).toBeTruthy();
    expect(screen.queryByText("Queue")).toBeNull();
  });
});
```

- [ ] **Step 2: Run test — expect FAIL**

Run: `cd web && npx vitest run src/features/work/resolve/ResolveGridToolbar.test.tsx`  
Expected: FAIL — missing props / Queue still present

- [ ] **Step 3: Update `ResolveGridToolbar`**

Replace `queueCount` prop with `moveReadyCount`, `reviewSignalCount`. Replace Queue chip:

```tsx
<StatChip label="이동 대기" value={moveReadyCount} tone="warn" />
<StatChip label="참고 신호" value={reviewSignalCount} />
```

- [ ] **Step 4: Wire workspace**

In `ResolveAndOrganizeWorkspace.tsx`:

```tsx
moveReadyCount={resolve.moveReadyCount}
reviewSignalCount={resolve.reviewSignalCount}
```

Remove `queueCount={resolve.queueCount}` from toolbar only (preflight still uses `resolve.queueCount` elsewhere).

- [ ] **Step 5: Run toolbar test + lint**

Run: `cd web && npx vitest run src/features/work/resolve/ResolveGridToolbar.test.tsx && npm run lint`  
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add web/src/types/snapshot.ts web/src/contracts/snapshotContract.ts web/src/contracts/fixtures.ts web/src/bridge/mockReviewState.ts web/src/bridge/mockBridge.ts web/src/features/work/resolve/ResolveGridToolbar.tsx web/src/features/work/ResolveAndOrganizeWorkspace.tsx web/src/features/work/resolve/ResolveGridToolbar.test.tsx
git commit -m "feat(NOV-27): show move-ready and review-signal chips in Resolve toolbar"
```

---

### Task 7: Verification matrix

- [ ] `pytest tests/test_bridge_contract.py::test_resolve_snapshot_split_counts_with_near_rows -v`
- [ ] `pytest tests/test_bridge_contract.py::test_validate_app_snapshot_accepts_valid -v`
- [ ] `cd web && npm run test:contracts`
- [ ] `cd web && npm run lint`
- [ ] `cd web && npx vitest run src/features/work/resolve/ResolveGridToolbar.test.tsx`
- [ ] `python scripts/verify_phase_completion.py` (if job allows full gate)

---

## Self-review (plan vs spec)

| Spec requirement | Task |
|------------------|------|
| R1 snapshot fields + invariant | Tasks 1–4 |
| R1 TS contract validation | Task 4 |
| R2 Python aggregation | Tasks 1–2 |
| R3 web consumption | Tasks 4–6 |
| R4 tests | Tasks 1, 3, 6, 7 |
| Non-goals respected | No preflight/row-badge changes |

No placeholders remain.
