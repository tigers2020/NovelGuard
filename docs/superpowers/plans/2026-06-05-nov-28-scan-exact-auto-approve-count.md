# NOV-28: Scan exact auto-approve count — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** After scan success, show scan-scoped count of exact non-keeper rows auto-approved this run (`work.scan.exactAutoApprovedCount`) in `ScanWorkspace` when N > 0.

**Architecture:** Capture `persist_exact_non_keeper_approvals` return in post-scan worker; store on session; emit via `build_snapshot`; render one informational line when `deriveScanSectionState === "success"` and count > 0. Mock bridge mirrors persist return. Do not reuse `work.resolve.approvedCount`.

**Tech Stack:** Python 3.12 (`src/`), React+TS (`web/`), pytest, vitest bridge parity.

**Spec:** Linear NOV-28 `## Spec` comment (2026-06-05)

**Branch:** `ai/NOV-28-scan-exact-auto-approve-count` from `main`

---

## File map

| File | Responsibility |
|------|----------------|
| `src/application/library_session.py` | `_exact_auto_approved_count`; capture persist return; reset on `start_scan` + `_clear_review_cache` |
| `src/application/dto_mapper.py` | `exactAutoApprovedCount` on `work.scan` |
| `src/app/bridge_contract.py` | Require int field on `work.scan` |
| `tests/fixtures/bridge_contract_fixtures.py` | Default `0` |
| `tests/test_bridge_contract.py` | Assert count ≥ 1 in `test_query_review_rows_exact_duplicate_pair` |
| `web/src/types/snapshot.ts` | `ScanSnapshot.exactAutoApprovedCount: number` |
| `web/src/contracts/fixtures.ts` | Fixture default `0` |
| `web/src/bridge/mockBridge.ts` | Module state + reset on `startScan`; set from persist return |
| `web/src/features/work/ScanWorkspace.tsx` | Summary line + `data-testid="scan-auto-approve-summary"` |
| `web/src/bridge/bridgeParity.test.ts` | Mock snapshot field after dup scan completes |

---

### Task 1: Python — session field + capture persist return

**Files:**
- Modify: `src/application/library_session.py`
- Test: `tests/test_bridge_contract.py`

- [ ] **Step 1: Write the failing assertion**

In `test_query_review_rows_exact_duplicate_pair`, after `assert snap["work"]["scan"]["state"] == "success"`:

```python
    assert snap["work"]["scan"]["exactAutoApprovedCount"] >= 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_bridge_contract.py::test_query_review_rows_exact_duplicate_pair -v`  
Expected: FAIL — `KeyError: 'exactAutoApprovedCount'` or contract `missing exactAutoApprovedCount`

- [ ] **Step 3: Add session field in `LibrarySession.__init__`**

After `self._scan_last_run: str | None = None`:

```python
        self._exact_auto_approved_count = 0
```

- [ ] **Step 4: Reset in `start_scan` (inside lock, before thread start)**

After `self._scan_state = "running"`:

```python
            self._exact_auto_approved_count = 0
```

- [ ] **Step 5: Reset in `_clear_review_cache`**

After `self._conflict_count = 0`:

```python
        self._exact_auto_approved_count = 0
```

- [ ] **Step 6: Capture persist return in post-scan worker (~line 1202)**

Replace:

```python
                    persist_exact_non_keeper_approvals(folder, files, self._index, stored)
```

With:

```python
                    approved_n = persist_exact_non_keeper_approvals(
                        folder, files, self._index, stored
                    )
                    self._exact_auto_approved_count = approved_n
```

(Inside the same `with self._lock` block as surrounding post-scan state updates, or assign before `_scan_state = "success"` under lock at lines 1215–1221.)

- [ ] **Step 7: Pass to `build_snapshot` in `get_snapshot`**

Add kwarg:

```python
                exact_auto_approved_count=self._exact_auto_approved_count,
```

- [ ] **Step 8: Re-run test** — still fails until Task 2–3; continue.

---

### Task 2: Python — dto_mapper + bridge contract

**Files:**
- Modify: `src/application/dto_mapper.py`
- Modify: `src/app/bridge_contract.py`
- Modify: `tests/fixtures/bridge_contract_fixtures.py`

- [ ] **Step 1: Extend `build_snapshot` signature and scan dict**

Add parameter:

```python
    exact_auto_approved_count: int = 0,
```

In `work.scan` dict:

```python
                "exactAutoApprovedCount": exact_auto_approved_count,
```

- [ ] **Step 2: Require field in `bridge_contract.py`**

Add `"exactAutoApprovedCount"` to the `for key in (...)` tuple under `work.scan` validation (after `"deepAnalysisError"`).

Add type check after the loop:

```python
    count = scan.get("exactAutoApprovedCount")
    if not isinstance(count, int) or count < 0:
        raise SnapshotContractError("invalid work.scan.exactAutoApprovedCount")
```

- [ ] **Step 3: Update `VALID_SNAPSHOT` fixture**

In `tests/fixtures/bridge_contract_fixtures.py` under `work.scan`:

```python
            "exactAutoApprovedCount": 0,
```

- [ ] **Step 4: Run contract test**

Run: `pytest tests/test_bridge_contract.py::test_query_review_rows_exact_duplicate_pair -v`  
Expected: PASS

- [ ] **Step 5: Run broader contract slice**

Run: `pytest tests/test_bridge_contract.py -k exact_duplicate -v`  
Expected: PASS

---

### Task 3: Web — types, fixtures, ScanWorkspace UI

**Files:**
- Modify: `web/src/types/snapshot.ts`
- Modify: `web/src/contracts/fixtures.ts`
- Modify: `web/src/features/work/ScanWorkspace.tsx`

- [ ] **Step 1: Extend `ScanSnapshot`**

```typescript
export interface ScanSnapshot {
  state: "empty" | "ready" | "running" | "success" | "error";
  lastRun: string | null;
  indexReady: boolean;
  deepAnalysisComplete: boolean;
  deepAnalysisStatus: DeepAnalysisStatus;
  deepAnalysisError: string | null;
  exactAutoApprovedCount: number;
}
```

- [ ] **Step 2: Add to `validAppSnapshot` in `fixtures.ts`**

```typescript
      exactAutoApprovedCount: 0,
```

- [ ] **Step 3: Render summary in `ScanWorkspace.tsx`**

After deep-analysis error block, before the primary action `<div className="mt-2 flex...">`:

```tsx
        {sectionState === "success" && scan.exactAutoApprovedCount > 0 && (
          <p
            className="mt-2 text-sm text-on-surface-variant"
            data-testid="scan-auto-approve-summary"
          >
            Exact 중복 {scan.exactAutoApprovedCount}건 non-keeper 자동 승인 — 검토·정리에서 이동 계획 미리보기 가능
          </p>
        )}
```

- [ ] **Step 4: Lint**

Run: `cd web && npm run lint`  
Expected: exit 0

---

### Task 4: Mock bridge parity

**Files:**
- Modify: `web/src/bridge/mockBridge.ts`
- Test: `web/src/bridge/bridgeParity.test.ts`

- [ ] **Step 1: Add module-level mock count**

Near other module state (`let libraryRevision = 0`):

```typescript
let exactAutoApprovedCount = 0;
```

- [ ] **Step 2: Reset on `startScan` entry**

At start of `async startScan()` after `stopScanSimulation()`:

```typescript
    exactAutoApprovedCount = 0;
```

- [ ] **Step 3: Capture persist return when scan completes**

Replace:

```typescript
        persistMockExactNonKeeperApprovals(getAllReviewRows());
```

With:

```typescript
        exactAutoApprovedCount = persistMockExactNonKeeperApprovals(getAllReviewRows());
```

- [ ] **Step 4: Emit in `buildSnapshot` scan object**

```typescript
        exactAutoApprovedCount,
```

- [ ] **Step 5: Write failing parity test**

Extend `mockBridge startScan completes` test or add:

```typescript
  it("mockBridge exposes exactAutoApprovedCount after scan with exact dupes", async () => {
    vi.useFakeTimers();
    await mockBridge.startScan();
    await vi.advanceTimersByTimeAsync(3_500);
    const snap = await mockBridge.getSnapshot();
    expect(snap.work.scan.exactAutoApprovedCount).toBeGreaterThanOrEqual(0);
    vi.useRealTimers();
  });
```

(If mock seed data has exact dupes, assert `>= 1`; else document mock fixture expectation.)

- [ ] **Step 6: Run parity test**

Run: `cd web && npm run test:contracts -- bridgeParity`  
Expected: PASS

---

### Task 5: Verification gate

- [ ] **Step 1: Python verify**

```bash
pytest tests/test_bridge_contract.py::test_query_review_rows_exact_duplicate_pair -v
pytest tests/test_bridge_contract.py -k exact_duplicate -v
python scripts/verify_phase_completion.py
```

Expected: all exit 0

- [ ] **Step 2: Web verify**

```bash
cd web && npm run lint
cd web && npm run test:contracts
```

Expected: all exit 0

- [ ] **Step 3: Commit (impl job only — when `commit: true`)**

```bash
git add src/application/library_session.py src/application/dto_mapper.py src/app/bridge_contract.py tests/fixtures/bridge_contract_fixtures.py tests/test_bridge_contract.py web/src/types/snapshot.ts web/src/contracts/fixtures.ts web/src/features/work/ScanWorkspace.tsx web/src/bridge/mockBridge.ts web/src/bridge/bridgeParity.test.ts
git commit -m "feat(NOV-28): show exact auto-approve count on scan success"
```

---

## Grill resolutions (locked for impl)

| Topic | Decision |
|-------|----------|
| Field name | `exactAutoApprovedCount` (camelCase snapshot) |
| Source | `persist_exact_non_keeper_approvals` return only |
| Reset | `start_scan` + `_clear_review_cache` → 0 |
| Cancel mid-scan | Next `start_scan` reset; UI hidden when not success |
| `approvedCount` | Do not use for this message |
| UI gate | `sectionState === "success"` AND count > 0 |
| E2E | Optional; contract + parity required |
