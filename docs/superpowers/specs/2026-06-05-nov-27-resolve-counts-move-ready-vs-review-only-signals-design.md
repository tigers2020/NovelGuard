# NOV-27: Resolve counts — move-ready vs review-only signals

**Linear:** [NOV-27](https://linear.app/zkaufman/issue/NOV-27/resolve-counts-move-ready-vs-review-only-signals)  
**Parent:** NOV-25 — Resolve UX clarity

## Summary (caveman)

- Add `work.resolve.moveReadyCount` + `work.resolve.reviewSignalCount` to AppSnapshot bridge contract.
- Aggregate via existing `finalize_blockers` helpers (or thin wrapper in `review_snapshot_counts`).
- Resolve toolbar shows `이동 대기` + `참고 신호` instead of misleading "Queue".
- `queueCount`, `approvedCount`, `conflictCount`, `groupCount` behavior unchanged.
- Contract test + toolbar unit test + lint/contracts green.

## Goal

Users on Resolve must see **move pipeline backlog** separate from **review-only near/relation signals**, without changing approval/conflict/group stats or finalize blocking rules.

## Non-goals

- Post-scan stripping of near/relation rows (NOV-26 mutation path).
- Row-level review-only badges or filter UX (NOV-29/30).
- Changing `FinalizeSummary` field names or preflight dialog copy (optional follow-up).

## Requirements

### R1 — Snapshot contract

`work.resolve` MUST include:

| Field | Type | Semantics |
|-------|------|-----------|
| `moveReadyCount` | `int` | Exact duplicate file rows with `status ∈ {unreviewed, conflict}` |
| `reviewSignalCount` | `int` | Sum of near + relation file rows with same unresolved statuses |
| `queueCount` | `int` | Unchanged: all file rows `unreviewed\|conflict` (exact+near+relation) |
| `approvedCount`, `conflictCount`, `groupCount`, `hasPendingApply`, `libraryRevision` | unchanged | Regression guard |

**Invariant (when all unresolved file rows have `type ∈ {exact, near, relation}`):**  
`moveReadyCount + reviewSignalCount === queueCount`.

Validation in `bridge_contract.py` and `web/src/contracts/snapshotContract.ts` MUST require both new fields as non-negative integers.

### R2 — Python aggregation

1. Add counting functions in `review_snapshot_counts.py` delegating to `finalize_blockers.exact_unresolved_queue_count`, `near_unresolved_file_row_count`, `relation_unresolved_file_row_count`.
2. `library_session._refresh_resolve_counts()` caches `_move_ready_count`, `_review_signal_count` alongside existing counts.
3. `dto_mapper.build_snapshot` emits new keys under `work.resolve`.

### R3 — Web consumption

1. Extend `ResolveSnapshot` in `web/src/types/snapshot.ts`.
2. Update mocks (`mockReviewState.ts`, `mockBridge.ts`) and contract fixtures (`contracts/fixtures.ts`, `tests/fixtures/bridge_contract_fixtures.py`) with defaults `0`.
3. `ResolveGridToolbar`: props `moveReadyCount`, `reviewSignalCount`; render `StatChip` labels `이동 대기` (warn tone) and `참고 신호` (default); **remove** standalone "Queue" chip.
4. `ResolveAndOrganizeWorkspace`: pass snapshot fields.

### R4 — Tests

| Test | Assert |
|------|--------|
| Python bridge contract | Snapshot with near/relation unreviewed rows: `moveReadyCount < queueCount`, `reviewSignalCount > 0`, split sums to `queueCount`, approved/conflict/group unchanged |
| Web unit | Toolbar renders both KO labels with provided values |
| Verify gates | `pytest tests/test_bridge_contract.py -k resolve`, `npm run test:contracts`, `npm run lint` exit 0 |

## Acceptance criteria (from issue)

- [ ] Snapshot exposes move-ready vs review-signal counts (R1)
- [ ] Toolbar shows `이동 대기` / `참고 신호` (R3)
- [ ] Approved / Conflicts / Groups unchanged (R1 regression)
- [ ] Bridge contract + web unit tests pass (R4)

## File touch list

| Action | Path |
|--------|------|
| Modify | `src/application/review_snapshot_counts.py` |
| Modify | `src/application/library_session.py` |
| Modify | `src/application/dto_mapper.py` |
| Modify | `src/app/bridge_contract.py` |
| Modify | `tests/fixtures/bridge_contract_fixtures.py` |
| Modify | `tests/test_bridge_contract.py` |
| Modify | `web/src/types/snapshot.ts` |
| Modify | `web/src/bridge/mockReviewState.ts` |
| Modify | `web/src/bridge/mockBridge.ts` |
| Modify | `web/src/contracts/fixtures.ts` |
| Modify | `web/src/contracts/snapshotContract.ts` |
| Modify | `web/src/features/work/resolve/ResolveGridToolbar.tsx` |
| Modify | `web/src/features/work/ResolveAndOrganizeWorkspace.tsx` |
| Create | `web/src/features/work/resolve/ResolveGridToolbar.test.tsx` |

## Risks & mitigations

| Risk | Mitigation |
|------|------------|
| `queueCount` still shown elsewhere (preflight) shows total | Document; toolbar uses split only |
| Zero near/relation library | Chips show `0` — no hide-on-zero |
| Contract drift mocks vs Python | Update all fixture sites in same PR |
| TS mock drift from Python semantics | Shared `resolveInsightCounts` helper in `mockReviewState.ts` mirroring finalize row filters |

## Verify commands

```bash
pytest tests/test_bridge_contract.py -k "resolve_split or near_filter or relation" -v
cd web && npm run test:contracts
cd web && npm run lint
cd web && npx vitest run src/features/work/resolve/ResolveGridToolbar.test.tsx
```
