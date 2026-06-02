---
title: PR-18 Duplicate Group Detail Panel
status: approved
date: 2026-06-01
parent_spec: docs/superpowers/specs/000-2026-06-01-novelguard-ui-overhaul-design.md
related_specs:
  - docs/superpowers/specs/002-2026-06-01-novelguard-greenfield-library-session-design.md
  - docs/superpowers/specs/005-2026-06-01-review-state-persistence-design.md
plan: docs/superpowers/plans/012-2026-06-01-pr18-duplicate-group-detail.md
---

# PR-18: Duplicate Group Detail Panel

## Goal

Deliver a **typed**, **review-state-aware** `getDuplicateGroupDetail` payload and wire **Resolve `DetailPanel`** to it so users can inspect every member of an exact-duplicate group, see keeper / move evidence, and run **keeper / conflict / reset** review commands from the panel (PR-17 left these API-only).

PR-14b shipped a **minimal** backend shape (`groupId` + `members[]` with `isKeeper` from domain pick only). PR-17 persisted keeper and status but **did not** enrich detail or add detail UI commands. Today `DetailPanel` renders only the selected `ReviewRow` stub fields ([DetailPanel.tsx](../../../web/src/features/work/resolve/DetailPanel.tsx)).

## Position in program

| PR | Delivers |
|----|----------|
| PR-14b | Exact duplicate rows + minimal `get_duplicate_group_detail` |
| PR-17 | `updateReviewDecisions`, SQLite review state, batch approve/exclude |
| **PR-18** | **Rich group detail DTO + DetailPanel member list + review commands** |
| PR-19+ | Near / relation duplicate types in grid and detail |

Wave B per [master roadmap](../roadmap/000-2026-06-01-novelguard-master-roadmap.md). Depends on **PR-14b**, **PR-17** (recommended: PR-15/16 for apply path already done).

---

## In scope

| Area | Behavior |
|------|----------|
| DTO | `DuplicateGroupDetail` — typed TS + validated Python dict (mirror `QualityIssueDetail` pattern) |
| Backend | Build detail from **merged review cache** + `FileRecord` + optional quality join — not raw `_pick_keeper` only |
| Bridge | `getDuplicateGroupDetail(groupId)` returns typed union; unknown/stale `groupId` → `status: "not_found"` (no HTTP/bridge throw) |
| UI fetch | On group **or** file row select, resolve `groupId` → fetch detail (same pattern as [QualityWorkspace.tsx](../../../web/src/features/work/QualityWorkspace.tsx)) |
| DetailPanel | Member table, keeper radio, group/file **충돌 표시** / **되돌리기**, read-only move plan + evidence |
| Commands | Wire `setKeeper`, `markConflict`, `reset` via existing `updateReviewDecisions` (PR-17 semantics unchanged) |
| Refresh | After detail mutation: mandatory 4-step sequence (§ Post-mutation refresh) |
| mockBridge | Return PR-18-shaped detail from merged mock review rows + review store |
| Contracts | Extend `bridge_contract` / optional `web/src/contracts` validator; parity list unchanged |

## Out of scope

| Item | Owner |
|------|--------|
| Near / relation / `move_only` groups in detail | PR-19+ |
| Target folder editing, `move_organized`, delete | Future |
| Auto conflict from encoding/integrity heuristics | Future |
| Per-row post-apply status chips in grid | Optional polish; not required for PR-18 acceptance |
| Quality workspace detail changes | PR-21 |
| New `test_*.py` / `*.test.tsx` files without `TEST_ALLOWED` | Extend existing modules only |
| `queryFileRows` / library-wide file grid | PR-29 |

---

## Current baseline (code truth)

| Item | Today |
|------|--------|
| `library_session.get_duplicate_group_detail` | Recomputes groups from files; **ignores PR-17 review merge**; members lack status / size / hash |
| `mockBridge.getDuplicateGroupDetail` | `{ groupId, row: ReviewRow \| null }` — **not** PR-14 contract shape |
| `NovelGuardBridge.getDuplicateGroupDetail` | `Promise<Record<string, unknown>>` — untyped |
| `DetailPanel` | Static fields from `selectedRow` only; **no bridge call** |
| PR-17 UI | Batch approve/exclude only; detail commands API-only |

---

## `DuplicateGroupDetail` contract

### TypeScript (`web/src/types/review.ts`)

```typescript
export type DuplicateMatchKind = "exact_content_hash";

export interface MemberIntegrity {
  status: "ok" | "issue";
  label: string; // e.g. "OK" or representative issue label
  issueCount: number;
}

export interface DuplicateGroupMemberDetail {
  /** Review grid row id: file:{groupId}:{fileId} */
  rowId: string;
  fileId: string;
  name: string;
  path: string;
  sizeBytes: number;
  status: ReviewStatus;
  isKeeper: boolean;
  proposedAction: ProposedAction;
  targetFolder?: string;
  encoding?: string;
  integrity: MemberIntegrity;
}

export interface DuplicateGroupDetailOk {
  status: "ok";
  groupId: string;
  type: "exact";
  /** Group header row review status (merged review state) */
  groupStatus: ReviewStatus;
  keeperFileId: string;
  keeperLabel: string;
  members: DuplicateGroupMemberDetail[];
  evidence: {
    matchKind: DuplicateMatchKind;
    contentSha256: string;
    memberCount: number;
  };
  movePlan: {
    keeperAction: "keep";
    duplicateAction: "move_duplicate";
    targetFolder: string;
  };
}

export interface DuplicateGroupDetailNotFound {
  status: "not_found";
  groupId: string;
  members: [];
  message: string;
}

export type DuplicateGroupDetail = DuplicateGroupDetailOk | DuplicateGroupDetailNotFound;
```

### Python

Same keys in `camelCase` JSON over pywebview. Validate in `bridge_contract.validate_duplicate_group_detail` (new helper, called from `BridgeApi.get_duplicate_group_detail` return path).

### Field rules

| Field | Source |
|-------|--------|
| `status` | `"ok"` when ≥1 file row in cache for `groupId`; else `"not_found"` |
| `groupId` | Request id (normalized trim) |
| `type` | Always `"exact"` on `ok` variant only |
| `groupStatus` | Merged group header row `status` from `_review_rows_cache` (`ok` only) |
| `keeperFileId` | Parsed from merged keeper on group/file rows (`file:{gid}:{fid}` → `fid`) |
| `keeperLabel` | Keeper member `name` |
| `members[]` | One entry per current group member in index, sorted **keeper first**, then `path` ascending |
| `members[].status` | Merged per-file status (PR-17 rules) |
| `members[].isKeeper` | `fileId === keeperFileId` |
| `encoding` | `FileRecord.encoding_status` or `"Unknown"` |
| `members[].integrity` | See § Member integrity |
| `evidence.contentSha256` | Shared hash from first member with `content_sha256` set |
| `evidence.matchKind` | Always `exact_content_hash` |
| `movePlan.targetFolder` | `"duplicate/"` (v1 convention, unchanged) |

### Member integrity

Per file member, join quality rows for that `fileId` (or path fallback):

| `integrity.status` | When |
|--------------------|------|
| `ok` | No quality issues for file |
| `issue` | ≥1 quality issue |

| `integrity.label` | When |
|-------------------|------|
| `"OK"` | `status === "ok"` |
| Representative label | Highest-severity issue kind mapped to short label (e.g. `encoding`, `integrity`, `small_file`) |

| `integrity.issueCount` | Count of quality issues for that file (0 when ok) |

UI may display `label` only; DTO always includes `issueCount`.

### Unknown / stale group (`not_found`)

No bridge exception. Return discriminated `not_found` so UI can distinguish from a real empty duplicate group (which cannot exist in v1 exact-dup model with 0 members).

```json
{
  "status": "not_found",
  "groupId": "dup-missing",
  "members": [],
  "message": "Group not found. Refresh the review list."
}
```

**UI (not toast):** empty state in detail panel:

> 그룹을 찾을 수 없습니다. 목록을 새로고침하세요.

Offer inline **새로고침** action → `queryReviewRows` reload (same as resolve retry). Do **not** use error banner styling for `not_found`.

---

## Backend design

### Use case

Add `application/duplicate_group_detail.py`:

```python
def build_duplicate_group_detail(
    group_id: str,
    *,
    review_rows: list[dict[str, Any]],
    files_by_id: dict[str, FileRecord],
    quality_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    ...
```

`LibrarySession.get_duplicate_group_detail`:

1. Under session lock, read `_review_rows_cache` and `_files_by_id`.
2. Filter cache rows where `groupId == group_id`.
3. If no file rows for `groupId` → return `not_found` variant (§ Unknown / stale group).
4. Build members from **file** rows in cache (not a second duplicate pass).
5. Join `FileRecord` + optional quality row per `fileId`.
6. Derive group-level `status` from `rowKind == "group"` row if present, else `unreviewed`.
7. Derive `keeperFileId` from member with `proposedAction == "keep"` or `isKeeper` on merged rows.

**Critical fix:** Stop using standalone `find_exact_duplicate_groups` + domain keeper for detail; detail must reflect **PR-17 merged cache** so keeper radio matches grid.

### Layering

| Layer | Responsibility |
|-------|----------------|
| `application/duplicate_group_detail.py` | Pure assembly from DTO dicts + `FileRecord` |
| `application/library_session.py` | Lock + delegate |
| `app/bridge_api.py` | Pass-through + contract validate |
| `domain/` | No change required |

---

## UI design (Resolve `DetailPanel`)

### Selection → fetch

| Selected `rowKind` | `groupId` | Fetch |
|--------------------|-----------|-------|
| `group` | `row.groupId` or parse from `row.id` (`group:{id}`) | `getDuplicateGroupDetail(groupId)` |
| `file` | `row.groupId` (required on file rows) | same |
| none | — | clear detail |

Loading: skeleton or muted “Loading…” in panel.

| Detail `status` | UI |
|-----------------|-----|
| `ok` | Full panel sections |
| `not_found` | Empty state copy (Korean) + refresh — **not** error toast |
| Bridge transport failure | Inline error + retry (resolve query error pattern) |

### Sections (top → bottom)

1. **Header** — group type `exact`, `status` badge, member count
2. **Keeper** — radio list bound to `members[]`; change calls `updateReviewDecisions({ command: "setKeeper", selection: { type: "explicit_rows", rowIds: [member.rowId] }, keeperFileId: member.fileId })`
3. **Move plan** — read-only summary from `movePlan` + per-member `proposedAction` / `targetFolder`
4. **Members table** — path, size, encoding, `integrity.label`, status
5. **Actions** (secondary buttons, not batch bar):
   - **충돌 표시** → `markConflict` with `selection: { type: "explicit_rows", rowIds: [selectedRow.id] }`
   - **되돌리기** → `reset` with same selection (group vs file semantics per PR-17 § reset)
6. **Evidence** — `contentSha256` truncated + copy-friendly; `matchKind` label
7. **Collapsible JSON** — full `DuplicateGroupDetail` for debugging

Disable keeper radio / actions while mutation in flight. After success, run § Post-mutation refresh (mandatory).

### `ResolveAndOrganizeWorkspace` wiring

- Pass `bridge`, `refreshSnapshot`, `onReviewMutated` callback into `DetailPanel` **or** hoist fetch state in workspace (preferred: workspace owns fetch like Quality — keeps panel presentational).
- Do **not** move batch approve/exclude into detail panel.

### Accessibility

- Keeper radios: `name={`keeper-${groupId}`}` + `aria-checked`
- Action buttons: `aria-disabled` when no `selectedRow`

---

## Bridge / mock parity

| Surface | Change |
|---------|--------|
| `NovelGuardBridge.getDuplicateGroupDetail` | Return `Promise<DuplicateGroupDetail>` |
| `pywebviewBridge` | Typed `call<DuplicateGroupDetail>` |
| `mockBridge` | Build from `mergedReviewRows()` + review store; **remove** `{ row }` stub |
| `bridge_contract` | `validate_duplicate_group_detail` |
| `bridgeParity.ts` | Method name unchanged |

---

## Interaction with PR-17 commands

Reuse [005 spec § Bridge contract](./005-2026-06-01-review-state-persistence-design.md) — no semantic changes.

| Detail UI control | Command | Selection |
|-------------------|---------|-----------|
| Keeper radio | `setKeeper` | `explicit_rows` with target member `rowId` + `keeperFileId` |
| 충돌 표시 | `markConflict` | `explicit_rows` with **currently selected grid row** id |
| 되돌리기 | `reset` | `explicit_rows` with **currently selected grid row** id |

All mutations: revision bump + discard preview on server (PR-17 lock A). UI must run post-mutation refresh.

### Post-mutation refresh (mandatory — grill-me lock)

After **any** detail-panel `updateReviewDecisions` (`setKeeper`, `markConflict`, `reset`) — same sequence as batch approve/exclude, **plus** detail refetch:

```text
1. await bridge.updateReviewDecisions(...)
2. await refreshSnapshot()          // hasPendingApply false when server cleared preview
3. await queryReviewRows(...)       // reload current page; grid reflects _review_rows_cache
4. await getDuplicateGroupDetail(groupId)  // detail rebuilt from merged cache (setKeeper must show new keeper)
```

Client: when `snapshot.work.resolve.hasPendingApply === false`, clear any local preview token / pending apply UI state (`pendingPreview = null` in mockBridge; Apply subflow respects snapshot).

**Order:** steps 2→3→4 sequential; do not skip detail refetch after `setKeeper`.

---

## Testing policy

| Layer | Approach |
|-------|----------|
| Python | Extend `tests/test_bridge_contract.py` — scan fixture with duplicate pair → detail has 2 members, keeper flagged, status fields present; after `update_review_decisions` setKeeper → detail keeper changes |
| TS | Extend `bridgeParity.test.ts` / contract tests if present for shape; typecheck `DuplicateGroupDetail` usage |
| mockBridge | Manual dev parity |
| E2E | Optional: select group → detail shows member count (`data-testid` hooks in plan) — only if stable without new file |

No new test modules without `TEST_ALLOWED`.

---

## Acceptance criteria

1. Selecting a duplicate **group** or **file** row loads member list from bridge (not row-only stub).
2. Keeper shown in detail matches grid `keeperLabel` after PR-17 `setKeeper`.
3. Changing keeper in detail updates grid after refresh.
4. `markConflict` / `reset` from detail change row `status` visible in grid.
5. Unknown `groupId` returns `status: "not_found"` with `message`; valid group returns `status: "ok"`.
6. Detail mutation runs post-mutation refresh; `setKeeper` refetched detail shows new keeper.
7. `python scripts/verify_phase_completion.py` passes.
8. mockBridge and pywebview return the same JSON keys and discriminant.

---

## Non-goals (PR-18)

- Near/relation duplicate detail
- Inline approve/exclude in detail (stay on batch bar)
- Editing `targetFolder` or filesystem paths from detail
- Post-apply per-row animation / status overlay

---

## Grill-me decision log

| # | Topic | Lock | Status |
|---|--------|------|--------|
| 1 | Fetch on file row select | **Yes** — parent group detail | **Locked** |
| 2 | Member sort | Keeper first, then path asc | **Locked** |
| 3 | Detail command selection | conflict/reset = selected grid row; setKeeper = member `rowId` | **Locked** |
| 4 | Missing / stale group | `status: "not_found"` union + panel empty state (no throw) | **Locked** (grill-me 2026-06-01) |
| 5 | Member integrity | `{ status, label, issueCount }` per member | **Locked** (grill-me 2026-06-01) |
| 6 | Typed bridge return | **Required** — `DuplicateGroupDetail` union | **Locked** |
| 7 | Post-mutation refresh | update → snapshot → rows → refetch detail; clear pending preview client-side | **Locked** (grill-me 2026-06-01) |

---

## Approval checklist

- [x] `DuplicateGroupDetail` union + `MemberIntegrity` locked
- [x] Backend reads merged review cache (not raw duplicate recompute)
- [x] DetailPanel sections + command wiring agreed
- [x] PR-17 command semantics unchanged (consume only)
- [x] Post-mutation refresh sequence documented
- [x] Test strategy: extend existing files only
- [x] **Human sign-off:** spec approved 2026-06-01 → implement per [012 plan](../plans/012-2026-06-01-pr18-duplicate-group-detail.md)

---

## Changelog

| Date | Change |
|------|--------|
| 2026-06-01 | Initial PR-18 spec draft (Wave B) |
| 2026-06-01 | Grill-me: `not_found` union, `MemberIntegrity`, post-mutation refresh lock; approved |
