# PR-18: Duplicate Group Detail Panel — Implementation Plan

> **For agentic workers:** Use superpowers:subagent-driven-development or superpowers:executing-plans. Track steps with `- [ ]` checkboxes.

**Goal:** Ship typed `getDuplicateGroupDetail` built from merged review state and wire Resolve `DetailPanel` to fetch members, evidence, and PR-17 review commands (`setKeeper`, `markConflict`, `reset`).

**Architecture:** `build_duplicate_group_detail` in `application/` assembles from `_review_rows_cache` + `FileRecord` + quality row join. Bridge validates outbound DTO. Web mirrors `QualityWorkspace` fetch pattern; workspace hoists detail state; `DetailPanel` stays mostly presentational.

**Tech Stack:** Python 3.12, React + TypeScript, existing PR-10 bridge validators, pytest + Vitest (extend existing files only).

**Spec:** [006-2026-06-01-duplicate-group-detail-design.md](../specs/006-2026-06-01-duplicate-group-detail-design.md) (**approved** 2026-06-01)

**Plan status:** **Implemented** (2026-06-01) — Tasks 1–9 complete; verification PASS

**Parent:** [000 master roadmap](../roadmap/000-2026-06-01-novelguard-master-roadmap.md) — Wave B PR-18

**Depends on:** PR-14b (duplicate rows), PR-17 (`updateReviewDecisions`, review merge)

**Test policy:** No new `test_*.py` / `*.test.tsx` without `TEST_ALLOWED`. Extend:

- `tests/test_bridge_contract.py`
- `web/src/contracts/bridgeParity.ts` + `bridgeParity.test.ts` (if shape assertions exist)
- `web/src/bridge/mockBridge.ts`

---

## Plan-locked decisions

| Lock | Value |
|------|--------|
| Detail source | `_review_rows_cache` file/group rows for `groupId` — **not** `find_exact_duplicate_groups` alone |
| Unknown `groupId` | `{ status: "not_found", groupId, members: [], message }` — no bridge throw |
| Member `integrity` | `{ status: "ok" \| "issue", label, issueCount }` per member |
| Post-mutation | `updateReviewDecisions` → `refreshSnapshot` → `queryReviewRows` → `getDuplicateGroupDetail`; clear client pending preview when `hasPendingApply === false` |
| Member sort | Keeper first, then `path` ascending |
| Fetch trigger | Group **or** file row selected |
| Commands | Existing `updateReviewDecisions` only — no new bridge methods |
| setKeeper from radio | `explicit_rows` + member `rowId` + `keeperFileId` |
| markConflict / reset | `explicit_rows` + **selected grid row** `id` |
| mockBridge | Remove `{ groupId, row }` stub; emit full `DuplicateGroupDetail` |

---

## File map

| File | Action |
|------|--------|
| `web/src/types/review.ts` | **Modify** — add `DuplicateGroupDetail`, `DuplicateGroupMemberDetail` |
| `web/src/bridge/NovelGuardBridge.ts` | **Modify** — typed `getDuplicateGroupDetail` |
| `web/src/bridge/pywebviewBridge.ts` | **Modify** — typed call |
| `web/src/bridge/mockBridge.ts` | **Modify** — PR-18 detail builder |
| `web/src/features/work/ResolveAndOrganizeWorkspace.tsx` | **Modify** — detail fetch + mutation refresh |
| `web/src/features/work/resolve/DetailPanel.tsx` | **Modify** — members, keeper radio, actions |
| `src/application/duplicate_group_detail.py` | **Create** — `build_duplicate_group_detail` |
| `src/application/library_session.py` | **Modify** — delegate + cache-based detail |
| `src/app/bridge_contract.py` | **Modify** — `validate_duplicate_group_detail` |
| `src/app/bridge_api.py` | **Modify** — validate on return |
| `tests/test_bridge_contract.py` | **Modify** — detail shape + setKeeper round-trip |

Optional (if contract module exists for review):

- `web/src/contracts/reviewDetailContract.ts` — **Create** only if team wants zod-style validate; **skip** if types + pytest sufficient (YAGNI default: **skip**).

---

## Task 1: TypeScript DTOs

**Files:** `web/src/types/review.ts`

- [ ] **Step 1:** Add types from spec § `DuplicateGroupDetail` union (`ok` \| `not_found`), `MemberIntegrity`, `DuplicateGroupMemberDetail`, `DuplicateMatchKind`.

- [ ] **Step 2:** Export helper `export function reviewRowGroupId(row: ReviewRow): string | null` — parse `group:{id}` or use `row.groupId`.

```typescript
export function reviewRowGroupId(row: ReviewRow): string | null {
  if (row.groupId) return row.groupId;
  if (row.id.startsWith("group:")) return row.id.slice("group:".length);
  if (row.id.startsWith("file:")) {
    const parts = row.id.split(":");
    return parts.length >= 3 ? parts[1] : null;
  }
  return null;
}
```

- [ ] **Step 3:** Run `cd web && npm run lint` — expect PASS on types.

---

## Task 2: Python detail builder

**Files:** `src/application/duplicate_group_detail.py` (new), `src/application/library_session.py`

- [ ] **Step 1:** Create `build_duplicate_group_detail` per spec:

```python
def build_duplicate_group_detail(
    group_id: str,
    *,
    review_rows: list[dict[str, Any]],
    files_by_id: dict[str, FileRecord],
    quality_by_file_id: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    gid = group_id.strip()
    group_rows = [r for r in review_rows if r.get("groupId") == gid]
    file_rows = [r for r in group_rows if r.get("rowKind") == "file"]
    header = next((r for r in group_rows if r.get("rowKind") == "group"), None)
    if not file_rows:
        return {
            "status": "not_found",
            "groupId": gid,
            "members": [],
            "message": "Group not found. Refresh the review list.",
        }
    # build members from file_rows + files_by_id + quality_by_file_id
    # sort: keeper first (proposedAction == "keep"), then path
    ...
```

- [ ] **Step 2:** Replace `LibrarySession.get_duplicate_group_detail` body:

```python
def get_duplicate_group_detail(self, group_id: str) -> dict[str, Any]:
    with self._lock:
        quality_by_file = _quality_index_by_file_id(self._quality_rows_cache)
        return build_duplicate_group_detail(
            group_id,
            review_rows=self._review_rows_cache,
            files_by_id=self._files_by_id,
            quality_by_file_id=quality_by_file,
        )
```

Implement `_quality_index_by_file_id` locally in `library_session.py` or `duplicate_group_detail.py` (map quality row → `file_id` if encoded in row id; else match `path` to `FileRecord.relative_path`).

- [ ] **Step 3:** Run `pytest tests/test_bridge_contract.py -q -k duplicate` (add tests in Task 6 first if red).

---

## Task 3: Bridge contract validation

**Files:** `src/app/bridge_contract.py`, `src/app/bridge_api.py`

- [ ] **Step 1:** Add `validate_duplicate_group_detail(payload: dict[str, Any]) -> None` — discriminant `status` in `ok` \| `not_found`; `ok` requires `groupStatus`, `evidence`, `movePlan`, members with `integrity.issueCount`; `not_found` requires `message`, `members: []`.

- [ ] **Step 2:** In `BridgeApi.get_duplicate_group_detail`:

```python
def get_duplicate_group_detail(self, group_id: str) -> dict[str, Any]:
    result = self._session.get_duplicate_group_detail(group_id)
    validate_duplicate_group_detail(result)
    return result
```

- [ ] **Step 3:** `pytest tests/test_bridge_contract.py::test_bridge_api_get_duplicate_group_detail_valid -v` (Task 6).

---

## Task 4: mockBridge parity

**Files:** `web/src/bridge/mockBridge.ts`

- [ ] **Step 1:** Replace stub:

```typescript
async getDuplicateGroupDetail(groupId: string): Promise<DuplicateGroupDetail> {
  return buildMockDuplicateGroupDetail(groupId, mergedReviewRows(), reviewStore);
}
```

Port logic mirroring Python: filter rows by `groupId`, map members, evidence hash from row metadata or fixture constant.

- [ ] **Step 2:** `cd web && npm run lint` — PASS.

---

## Task 5: Web bridge typing

**Files:** `web/src/bridge/NovelGuardBridge.ts`, `web/src/bridge/pywebviewBridge.ts`

- [ ] **Step 1:** Import `DuplicateGroupDetail`; change method signature.

- [ ] **Step 2:** pywebview:

```typescript
getDuplicateGroupDetail: (groupId: string) =>
  callBridge(() => call<DuplicateGroupDetail>(api, "get_duplicate_group_detail", groupId), {
    method: "getDuplicateGroupDetail",
  }),
```

---

## Task 6: Contract tests (Python)

**Files:** `tests/test_bridge_contract.py`

- [ ] **Step 1:** Add fixture scan producing one duplicate pair (reuse existing temp-dir helpers from PR-14b tests in same file).

- [ ] **Step 2:** Test `get_duplicate_group_detail`:

```python
def test_get_duplicate_group_detail_members_and_keeper(tmp_path: Path) -> None:
    api = _api_with_duplicate_pair(tmp_path)
    page = api.query_review_rows({"viewMode": "groups", "limit": 50})
    group_row = next(r for r in page["rows"] if r["rowKind"] == "group")
    gid = group_row["groupId"]
    detail = api.get_duplicate_group_detail(gid)
    validate_duplicate_group_detail(detail)
    assert detail["status"] == "ok"
    assert len(detail["members"]) >= 2
    assert sum(1 for m in detail["members"] if m["isKeeper"]) == 1
    assert detail["members"][0]["integrity"]["issueCount"] >= 0
```

Adjust assert keys to match final validator naming (`evidence.memberCount` vs top-level — **follow spec**, not this sketch, when implementing).

- [ ] **Step 3:** Test setKeeper round-trip:

```python
def test_detail_keeper_follows_set_keeper(tmp_path: Path) -> None:
    ...
    file_row = next(r for r in page["rows"] if r["rowKind"] == "file" and r["proposedAction"] == "move_duplicate")
    api.update_review_decisions({
        "selection": {"type": "explicit_rows", "rowIds": [file_row["id"]]},
        "command": "setKeeper",
        "keeperFileId": file_row["id"].split(":")[-1],
    })
    detail = api.get_duplicate_group_detail(gid)
    assert detail["status"] == "ok"
    assert detail["keeperFileId"] == file_row["id"].split(":")[-1]

- [ ] **Step 4:** Test `not_found`:

```python
def test_get_duplicate_group_detail_not_found(tmp_path: Path) -> None:
    api = _api_with_duplicate_pair(tmp_path)
    detail = api.get_duplicate_group_detail("dup-nonexistent")
    validate_duplicate_group_detail(detail)
    assert detail["status"] == "not_found"
    assert detail["members"] == []
```

- [ ] **Step 5:** `pytest tests/test_bridge_contract.py -q` — PASS.

---

## Task 7: DetailPanel UI

**Files:** `web/src/features/work/resolve/DetailPanel.tsx`, `web/src/features/work/ResolveAndOrganizeWorkspace.tsx`

- [ ] **Step 1:** Workspace — state `detail`, `detailLoading`, `detailError`; `loadDetail(selectedRow)`:

```typescript
const loadDetail = useCallback(async (row: ReviewRow | null) => {
  const gid = row ? reviewRowGroupId(row) : null;
  if (!gid) { setDetail(null); return; }
  setDetailLoading(true);
  try {
    setDetailError(null);
    setDetail(await bridge.getDuplicateGroupDetail(gid));
  } catch (e) {
    setDetailError(e instanceof Error ? e.message : "Failed to load group detail");
    setDetail(null);
  } finally {
    setDetailLoading(false);
  }
}, [bridge]);
```

Call from `toggleSelect` / initial load when `selectedRow` changes.

- [ ] **Step 2:** `runDetailReviewCommand(...)` — **mandatory sequence** (spec § Post-mutation refresh):

```typescript
async function runDetailReviewCommand(...) {
  await bridge.updateReviewDecisions({ selection, command, keeperFileId });
  await refreshSnapshot();
  await loadPage(null, false);
  const gid = selectedRow ? reviewRowGroupId(selectedRow) : null;
  if (gid) await loadDetail(selectedRow);
  // snapshot.hasPendingApply false → Apply subflow / local preview cleared
}
```

- [ ] **Step 2b:** `DetailPanel` — if `detail.status === "not_found"`, render empty state (Korean copy from spec); `data-testid="detail-not-found"`. No error toast.

- [ ] **Step 3:** `DetailPanel` props:

```typescript
export function DetailPanel({
  selectedRow,
  detail,
  loading,
  error,
  onSetKeeper,
  onMarkConflict,
  onReset,
}: { ... });
```

Render: status badge, keeper radios, member table, action buttons, evidence block, JSON `<details>`.

- [ ] **Step 4:** `data-testid` hooks: `detail-panel`, `detail-member-count`, `detail-keeper-radio-{fileId}`, `detail-mark-conflict`, `detail-reset`.

- [ ] **Step 5:** `cd web && npm run lint` — PASS.

---

## Task 8: Manual smoke

- [ ] **Step 1:** `python src/main.py` — scan folder with 2+ identical files.

- [ ] **Step 2:** Resolve → select group → detail shows ≥2 members, keeper radio matches grid.

- [ ] **Step 3:** Change keeper in detail → grid `keeperLabel` updates after refresh.

- [ ] **Step 4:** **충돌 표시** on file row → status `conflict`; **되돌리기** → `unreviewed`.

- [ ] **Step 5:** Browser dev: `npm run dev` + mockBridge — same flows.

---

## Task 9: Verification gate

- [ ] **Step 1:** `python scripts/verify_phase_completion.py` — all stages PASS.

- [ ] **Step 2:** Report counts in PR / handoff.

---

## Risks

| Risk | Mitigation |
|------|------------|
| Quality row → file join ambiguous | Prefer `file_id` on quality issue if present; else path match; document in code comment |
| mockBridge diverges from Python | Shared field list in spec; contract test + manual smoke |
| PR-18 scope creep (approve in detail) | Batch bar only per spec out-of-scope |
| Large groups perf | PR-18 exact groups typically small; no virtualization required |

---

## Completion checklist

- [x] Spec `006` approved (2026-06-01)
- [x] Plan approved (2026-06-01)
- [x] Tasks 1–9 done
- [x] Roadmap PR-18 row updated to Done
- [ ] Plan scope freeze — no PR-19 work in this slice
