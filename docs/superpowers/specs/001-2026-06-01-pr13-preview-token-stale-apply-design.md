---
title: PR-13 Preview Token & Stale Apply Contract
status: approved
date: 2026-06-01
authors: brainstorming (product + bridge + UI)
parent_spec: docs/superpowers/specs/00-2026-06-01-novelguard-ui-overhaul-design.md
pr_label: PR-13
---

# PR-13 — Preview Token & Stale Apply Contract

## Status

**Approved** (2026-06-01) — reviewer locks applied; implementation plan in `004-2026-06-01-pr13-preview-token-stale-apply.md`.

## Scope sentence

PR-13 implements preview-token and stale-apply invariants across bridge contracts, mock simulation, `ApplySubflowDialog`, and Python `BridgeApi` stubs. It does **not** perform real filesystem move/delete operations.

## Not in scope (naming)

This PR is **not** about `DESIGN.md` color/spacing **design tokens** or Tailwind `@theme` work. “Token” here means an **opaque preview-apply correlation id** returned by `getMovePreview` and required by `applyResolvedActions`.

## Summary

PR-0..12 delivered the destructive apply **UI flow** (`getMovePreview` → confirm → `applyResolvedActions`) and `hasPendingApply` for preflight, but **no contract** binds a preview snapshot to an apply request. A client can change `SelectionScope` after preview, or apply without preview; the bridge cannot detect stale library state.

PR-13 adds:

- **`MovePreviewResult`** with `previewToken`, `libraryRevision`, `selectionFingerprint`
- **`applyResolvedActions`** requiring `{ selection, previewToken }`
- **`discardMovePreview`** to end preview lifetime on dialog cancel/close
- **Mock full simulation** and **Python stub guards** (apply remains no-op)
- **UI dual guard** (disable stale apply + bridge rejection)

Real move/delete execution stays in a **future PR** (post PR-13 / alongside application use cases).

## Parent spec alignment

Extends [00-2026-06-01-novelguard-ui-overhaul-design.md](./00-2026-06-01-novelguard-ui-overhaul-design.md):

- Destructive path: **dry-run preview → user confirm → apply** (unchanged UX steps)
- `hasPendingApply` drives GlobalCommandBar preflight (unchanged semantics; lifecycle clarified)
- `SelectionScope` on preview/apply (unchanged; fingerprint added)

Does **not** change: snapshot forbids row arrays, query pagination limits, grid stack, PR-14 packaging.

---

## Locked decisions

| Decision | Value |
|----------|--------|
| Scope tier | **C** — contract + mock simulation + Python stub guard; no FS mutation |
| PR name | **PR-13 Preview Token & Stale Apply Contract** |
| Pending slot | **Single** `pendingPreview` per bridge instance; new preview replaces old token |
| Stale handling | **UI first + bridge final** (defense in depth) |
| Error transport | `BridgeCallError` with `code: "rejected"` + `reason: PreviewApplyErrorCode` |
| `libraryRevision` type | **`number`** (monotonic counter) |
| Dialog cancel/close | **(2) clear** — discard pending preview; `hasPendingApply=false` |
| Selection stale codes | **`SELECTION_CHANGED`** separate from **`STALE_PREVIEW`** |
| Tests | Extend **existing** test files; no new test files without `TEST_ALLOWED` |
| `libraryRevision` on snapshot | **Required** on `ResolveSnapshot` (not optional) |
| `selectionFingerprint` | **SHA-256** over canonical normalized JSON (algorithm fixed below) |
| `discardMovePreview` mismatch | **Idempotent success** — lifecycle cleanup, not mutation auth |

---

## Bridge contract

### Types

New module: `web/src/types/movePreview.ts` (recommended).

```typescript
interface MovePreviewRow {
  id: string;
  action: string; // e.g. "move_organized"
}

interface MovePreviewSummary {
  rowCount: number;
  conflictCount?: number;
}

interface MovePreviewResult {
  previewToken: string;
  libraryRevision: number;
  selectionFingerprint: string;
  hasPendingApply: true;
  rows: MovePreviewRow[];
  summary: MovePreviewSummary;
}

interface ApplyResolvedActionsRequest {
  selection: SelectionScope;
  previewToken: string;
}

interface DiscardMovePreviewRequest {
  previewToken: string;
}

type PreviewApplyErrorCode =
  | "MISSING_PREVIEW_TOKEN"
  | "INVALID_PREVIEW_TOKEN"
  | "NO_PENDING_APPLY"
  | "STALE_PREVIEW"
  | "SELECTION_CHANGED";
```

### `selectionFingerprint` algorithm (hard lock)

```text
selectionFingerprint = sha256(utf8(canonicalJson(normalizedSelectionScope))).hex()
```

**Canonical JSON rules** (TS and Python must match):

- Object keys sorted **lexicographically** at every nesting level
- **Omit** `undefined` fields (TS); omit keys with value `null` only if normalization removes them
- Normalize empty arrays to `[]` (e.g. `excludeRowIds`)
- **Normalize `ReviewRowsQuery` defaults** before hashing: explicit `limit` default `100`, omitted optional `filters` → `{}`, omitted `cursor` → `null`, omitted `sort` → omitted from object
- JSON serialization: **no insignificant whitespace** (`separators=(",", ":")` in Python; `JSON.stringify` after canonical build in TS)

Implementations: `web/src/bridge/selectionFingerprint.ts` and `src/app/selection_fingerprint.py` (or module under `src/app/`).

### API surface (`NovelGuardBridge`)

```typescript
getMovePreview(selection: SelectionScope): Promise<MovePreviewResult>;

applyResolvedActions(request: ApplyResolvedActionsRequest): Promise<void>;

discardMovePreview(request: DiscardMovePreviewRequest): Promise<void>;
```

**Breaking change:** `applyResolvedActions` no longer accepts `SelectionScope` alone.

### Pywebview parity

| TS | Python |
|----|--------|
| `getMovePreview` | `get_move_preview` |
| `applyResolvedActions` | `apply_resolved_actions` |
| `discardMovePreview` | `discard_move_preview` |

Add to `NOVEL_GUARD_BRIDGE_METHODS` / `PYWEBVIEW_API_METHODS` and contract validators (PR-10 style).

### Errors

Bridge implementations throw `BridgeCallError` with:

- `code`: `"rejected"` (transport)
- `method`: caller method name
- `reason`: `PreviewApplyErrorCode` (business invariant)

UI and E2E may branch on `reason` for messages and `data-testid` behavior.

### Snapshot fields (hard lock)

**Required on `ResolveSnapshot`:**

```typescript
interface ResolveSnapshot {
  // ...existing counters...
  hasPendingApply: boolean;
  libraryRevision: number; // monotonic; required in PR-13
}
```

`AppSnapshot.work.resolve.libraryRevision` is **required**. Contract validators (TS + Python) reject snapshots missing it or with non-number values. UI **must** compare dialog preview revision to snapshot `libraryRevision` on each snapshot refresh to detect `STALE_PREVIEW` without re-fetching preview.

**Rule:** After successful `getMovePreview`, snapshot refresh (or mock inline update) sets `hasPendingApply: true`. After successful `applyResolvedActions` or successful `discardMovePreview`, `hasPendingApply: false`.

Preview response `libraryRevision` must equal snapshot `work.resolve.libraryRevision` at preview time.

Preview response `hasPendingApply: true` must match snapshot after refresh.

---

## Invariants (must enforce)

| Case | Bridge `reason` | UI behavior |
|------|-----------------|-------------|
| Apply without `previewToken` | `MISSING_PREVIEW_TOKEN` | Apply disabled until preview success |
| No pending preview / unknown token | `NO_PENDING_APPLY` | Inline error; offer re-preview |
| Token mismatch | `INVALID_PREVIEW_TOKEN` | Inline error |
| `libraryRevision` changed since preview | `STALE_PREVIEW` | `PreviewState.stale(library_changed)`; apply disabled |
| `selectionFingerprint` mismatch | `SELECTION_CHANGED` | `PreviewState.stale(selection_changed)`; apply disabled |
| Apply success, reuse same token | `NO_PENDING_APPLY` | Token discarded locally |
| New `getMovePreview` while pending | Previous token invalidated | Single-slot `pendingPreview` replaced |

---

## `discardMovePreview`

Ends preview lifetime when the user closes the apply dialog without applying.

```typescript
discardMovePreview(request: { previewToken: string }): Promise<void>;
```

| Case | Result |
|------|--------|
| Dialog **Cancel** or **X (close)** while `ready` | Call `discardMovePreview({ previewToken })` |
| Discard success | `pendingPreview = null`, `hasPendingApply = false`, snapshot refresh |
| Token already invalid / no pending | Idempotent: local dialog reset + snapshot refresh |
| Apply after discard | `NO_PENDING_APPLY` |

**Rationale:** Dialog-local token is destroyed on close. Keeping bridge `pendingPreview` would orphan `hasPendingApply=true` with no UI path to apply — violates PR-13 safety goals.

**Idempotent mismatch policy (hard lock):** `discardMovePreview` is a **lifecycle cleanup API**, not a mutation authorization API. Token mismatch or missing pending **does not throw** — bridge clears orphan `hasPendingApply` if needed and returns success so Cancel/X always closes UI cleanly. Apply paths remain strict (throw on mismatch).

---

## UI — `ApplySubflowDialog`

### Dialog-local state

```typescript
type PreviewState =
  | { status: "idle" }
  | {
      status: "ready";
      token: string;
      libraryRevision: number;
      selectionFingerprint: string;
      rowCount: number;
    }
  | { status: "stale"; reason: "selection_changed" | "library_changed" }
  | { status: "error"; message: string; reason?: PreviewApplyErrorCode };
```

### Rules

1. **Before preview:** Apply (confirm step) not rendered / disabled.
2. **Preview success:** Store token, revision, fingerprint, row count; move to confirm step.
3. **`selection` prop changes** while `ready`: if fingerprint ≠ stored → `stale(selection_changed)`; hide apply; show re-preview message (Korean copy in plan).
4. **Library revision changes** (snapshot field or explicit bump): → `stale(library_changed)`.
5. **Apply:** Only when `ready` and not stale; call `applyResolvedActions({ selection, previewToken })`.
6. **Apply success:** Close dialog; reset state; snapshot shows `hasPendingApply=false`.
7. **Cancel/close:** Call `discardMovePreview({ previewToken })` when `ready`; reset dialog state; refresh snapshot (`hasPendingApply=false`, pending cleared on bridge).
8. **Bridge errors on apply/discard:** Inline alert in dialog (`data-testid="apply-bridge-error"`); stale banner `data-testid="apply-stale-banner"`.

### Preflight

`GlobalCommandBar` / `PreflightPipelineDialog` continue to use `hasPendingApply` from snapshot. With cancel policy (2), closing the dialog clears the flag — preflight no longer blocks on abandoned previews.

---

## Mock bridge (`mockBridge.ts`)

Full simulation **without file I/O**.

### State

```typescript
pendingPreview: {
  token: string;
  libraryRevision: number;
  selectionFingerprint: string;
  rows: MovePreviewRow[];
} | null;

libraryRevision: number; // monotonic, bump on defined events
```

### `getMovePreview`

- Normalize selection; compute fingerprint.
- Generate `previewToken` (opaque string).
- Replace `pendingPreview` (invalidates prior token).
- Set `hasPendingApply = true`.
- Return `MovePreviewResult`.

### `applyResolvedActions`

Validate in order:

1. `previewToken` present → else `MISSING_PREVIEW_TOKEN`
2. `pendingPreview` exists → else `NO_PENDING_APPLY`
3. Token match → else `INVALID_PREVIEW_TOKEN`
4. `libraryRevision` match → else `STALE_PREVIEW`
5. Fingerprint match → else `SELECTION_CHANGED`

On success: `pendingPreview = null`, `hasPendingApply = false`, log only (no FS).

### `discardMovePreview`

- If token matches pending → clear pending, `hasPendingApply = false`
- If no pending or mismatch → no-op success (idempotent)
- Never leaves orphan `hasPendingApply=true` without valid pending

### `libraryRevision` bumps (v1)

Document in plan; pick at least one for E2E:

- `startScan` completion (mock)
- Explicit test hook: `window.__NOVELGUARD_TEST_BUMP_REVISION__` (E2E only, optional)

---

## Python `BridgeApi` stub

- **`get_move_preview`:** validate selection; create token + fingerprint + revision; set `_pending_apply`; return full `MovePreviewResult` shape; validate via `validate_move_preview` (extended).
- **`apply_resolved_actions`:** accept dict with `selection` + `previewToken`; run same checks as mock; **no-op** apply; clear `_pending_apply`.
- **`discard_move_preview`:** accept `{ previewToken }`; clear if match; idempotent.
- Raise structured errors mapped to TS `reason` codes (new exception type or error dict — plan chooses minimal path).

No imports from domain FS move use cases in PR-13.

---

## Testing strategy

Extend existing files only (unless user grants `TEST_ALLOWED`):

| Layer | File | Cases |
|-------|------|--------|
| Vitest | `web/src/contracts/bridgeParity.test.ts`, bridge/mock tests | parity includes `discardMovePreview`; missing token; stale fingerprint |
| Vitest | `web/src/bridge/callBridge.test.ts` or mock-focused existing file | `reason` on rejected apply |
| Pytest | `tests/test_bridge_contract.py` | bad token, missing token, stale revision, valid apply clears pending, discard |
| E2E | `web/e2e/smoke.spec.ts` | keep preview-fail blocks apply; add discard on close; stale selection disables apply |

---

## Non-goals (PR-13)

- Real filesystem move, delete, or duplicate merge execution
- Finalize / repair apply body
- PR-14 packaging / `webview_main` production path changes
- AG Grid, FileDock, new Work screens
- Changing PR-10 query validators except move-preview/apply/discard shapes
- `DESIGN.md` / `@theme` color token work

---

## Implementation plan outline (for `writing-plans`)

| Task | Content |
|------|---------|
| 1 | `movePreview.ts` types + `PreviewApplyErrorCode` + `BridgeCallError.reason` |
| 2 | Update `NovelGuardBridge`, parity lists, fixtures, validators |
| 3 | `selectionFingerprint` util (TS) + Python mirror |
| 4 | `mockBridge` pending preview + discard + revision bumps |
| 5 | `ApplySubflowDialog` state machine + discard on close |
| 6 | `pywebviewBridge` + `testBridge` wiring |
| 7 | Python `BridgeApi` + `bridge_contract` validation |
| 8 | Extend Vitest / Pytest / E2E per table above |
| 9 | Docs: `entry_points.md` / plan cross-link; audit note “not DESIGN tokens” |
| 10 | `verify_phase_completion.py` |

---

## Approval checklist

- [x] Scope C: contract + mock + stub; no FS apply
- [x] `previewToken` required for apply
- [x] Token bound to selection fingerprint + library revision
- [x] Stale blocked in UI and bridge
- [x] Cancel/close clears pending via `discardMovePreview`
- [x] Mock simulates full invariant paths
- [x] Python no-op apply with guard rails
- [x] Separated from PR-14 packaging

---

## Changelog

| Date | Change |
|------|--------|
| 2026-06-01 | Initial PR-13 spec from brainstorming; cancel policy (2) clear + `discardMovePreview` |
| 2026-06-01 | Reviewer locks: required `libraryRevision`, SHA-256 fingerprint, discard idempotent rationale; status → approved |
