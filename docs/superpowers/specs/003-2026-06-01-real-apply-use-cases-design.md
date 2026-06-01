---
title: PR-15 Real Apply Use Cases
status: approved
date: 2026-06-01
authors: roadmap review + product safety (apply wave A)
parent_spec: docs/superpowers/specs/000-2026-06-01-novelguard-ui-overhaul-design.md
related_specs:
  - docs/superpowers/specs/001-2026-06-01-pr13-preview-token-stale-apply-design.md
  - docs/superpowers/specs/002-2026-06-01-novelguard-greenfield-library-session-design.md
roadmap: docs/superpowers/roadmap/000-2026-06-01-novelguard-master-roadmap.md
pr_label: PR-15
---

# PR-15 — Real Apply Use Cases

## Status

**Approved** (2026-06-01) — spec review locks applied. **Implementation plan:** [009-2026-06-01-pr15-real-apply-use-cases.md](../plans/009-2026-06-01-pr15-real-apply-use-cases.md) (**approved** — implement Task 0+).

## Scope sentence

PR-15 turns `getMovePreview` / `applyResolvedActions` from **stub preview + filesystem no-op** into **real dry-run planning and real move execution only** (`move_duplicate`) behind the existing PR-13 guard rails. It adds an **audit log**, **application-layer apply use cases**, and an **infrastructure filesystem port**. It does **not** change Resolve UI outcome presentation (PR-16), review-state persistence (PR-17), near/relation detection, or quality repair.

## Summary

| Area | Today (post PR-14d) | PR-15 target |
|------|---------------------|--------------|
| `getMovePreview` | PR-13 shape; Python returns synthetic one-row preview | **Real** plan rows derived from `SelectionScope` + indexed `ReviewRow` data |
| `applyResolvedActions` | PR-13 validation then **no FS mutation** | Same validation, then **real move only** per immutable preview plan |
| `mockBridge` | Full PR-13 simulation, no I/O | Stays **browser dev only**; simulates plan/apply without touching user disk |
| `BridgeApi` | Holds `_pending_apply` + stub preview | **Thin**: validate → delegate → map errors |
| Safety | Preview token + revision + fingerprint | Unchanged **plus** path confinement + dry-run ≡ apply plan |

---

## Locked decisions (proposal)

| Decision | Value |
|----------|--------|
| PR name | **PR-15 Real Apply Use Cases** |
| Wave | **A** (roadmap-locked sequencing; this spec/plan still require approval) |
| Phase 0 | **E2E preflight** inside PR-15 (not a standalone PR) |
| Bridge response shape | `applyResolvedActions` remains **`Promise<void>`** on full success; structured errors on failure (PR-16 may add outcome DTOs) |
| Preview/apply guards | **PR-13 unchanged** — no bypass paths |
| `mockBridge` | Browser-only; **no** silent fallback when pywebview fails |
| v1 apply actions | **`move_duplicate`** enabled; **`keep` / `ignore`** no-op (omitted from plan); **`delete`** recognized by contract but **never emitted or executed** in PR-15; **`move_organized`** not emitted (unsupported → `blockedCount`) |
| Hard delete / trash | **Out of scope** — future spec after PR-16/17: trash/quarantine → hard delete |
| Near / relation rows | **Out of scope** — preview returns only rows applicable to exact-duplicate v1 data |
| UTF-8 / quality repair | **Out of scope** (PR-22+) |
| Auto-rollback | **No** automatic filesystem rollback in v1 |
| Audit persistence | **Append-only JSONL** under session data dir (path in plan) |
| Preview token storage | May move from `BridgeApi` to app helper **only** if behavior identical; extraction to PR-30 remains optional |

---

## Phase 0 — E2E preflight (entry gate)

**Purpose:** Confirm UI/bridge contract stability before enabling real filesystem mutation.

**Not a separate PR.** Completes before Phase 1 (use cases + real apply).

### Steps

```text
1. Run: cd web && npm run test:e2e
2. Record pass/fail count and failing test names (reconfirm at plan time; last local artifact may show 0 failures)
3. For each failure, classify:
   - flake
   - pre-existing defect
   - PR-14 regression
4. If failure blocks preview/apply/discard/stale-banner contract path → fix in Phase 0
5. Else → document in plan as known-failure artifact (optional note under docs/superpowers/)
```

### Blocking failures (must fix before Phase 1)

Any failure in:

- `preview failure blocks apply`
- `closing apply dialog discards pending preview`
- `library revision bump shows stale banner`
- Bridge unavailable / snapshot contract smoke that prevents Apply subflow mount

### Non-blocking

Grid perf, column resize, quality query retry-only failures — document; do not delay real apply unless product says otherwise.

### Phase 0 exit criteria

- [ ] E2E command run recorded in plan PR notes
- [ ] Blocking failures = 0 (or waived explicitly in spec review)
- [ ] Apply-subflow tests pass against **mockBridge** (baseline unchanged)

---

## Real apply safety model

### Product invariant (unchanged)

From [AGENTS.md](../../../AGENTS.md) and [000 UI overhaul](./000-2026-06-01-novelguard-ui-overhaul-design.md):

```text
destructive filesystem change ONLY after:
  getMovePreview (dry-run) → user confirm in ApplySubflowDialog → applyResolvedActions
```

### Defense in depth

| Layer | Responsibility |
|-------|----------------|
| UI (`ApplySubflowDialog`) | Disable apply when preview not `ready` or `stale`; require confirm step |
| Bridge (`BridgeApi`) | PR-13 token/revision/fingerprint checks **before** delegate |
| Application (`ApplyResolvedActionsUseCase`) | Build plan from session index; refuse ambiguous paths |
| Domain (`ApplyPathPolicy` or equivalent) | Pure rules: path under library root, no `..` escape, allowed action enum |
| Infrastructure (`FilesystemApplyPort`) | Execute **move only** in PR-15; map OS errors to port result |

### Path confinement (hard lock)

All source and destination paths must satisfy:

1. Resolved absolute path is **under** the session `library_root` (canonical comparison).
2. No operation targets **outside** library root.
3. `targetFolder` from review rows is **relative**; join only via library-root-safe resolver (no user-provided absolute paths in v1).
4. Destination parent directories created **only** under library root.
5. **Destination exists:** if `library_root / targetFolder / basename` already exists → **conflict**; operation not executable; **no overwrite**, **no auto-rename** in PR-15.

**Symlink resolution (hard lock):**

- For **existing** source paths and **existing** destination parent directories: resolve symlinks; require resolved path under `library_root`.
- For **non-existing** destination file: resolve the destination **parent** under `library_root`, then append `basename` lexically (do not `resolve()` a path that does not exist yet).

Violations → **do not mutate**; preview marks row as conflict (or `blockedCount` for unsupported actions); apply skips non-executable ops (see partial failure).

### Plan immutability

The **preview plan** (ordered list of operations + content hash) is stored server-side with `previewToken`. `applyResolvedActions` must execute **exactly** that plan — not re-derive from live index if revision unchanged but row data changed. If live data no longer matches plan fingerprint → `STALE_PREVIEW` (bridge) before any FS call.

**Preview operation (immutable plan row):** stored server-side and hashed into `planFingerprint`:

```text
PreviewOperation {
  rowId: string
  action: "move_duplicate"   // only executable action in PR-15
  sourcePath: string         // relative to library_root
  destPath?: string           // relative destination file path
  sourceFileId: string
  sourceSize: number
  sourceContentHash: string   // SHA-256 of file bytes at preview time
  sourceMtimeNs?: number      // optional; include if available from index
}
```

**Plan fingerprint:**

```text
planFingerprint = sha256(canonicalJson(previewOperations)).hex()
```

`previewOperations` is the ordered list of `PreviewOperation` objects above (canonical JSON per PR-13 rules).

**Apply-time file drift validation (before each FS move):**

1. Source path exists under `library_root`.
2. Resolved source path still under `library_root` (symlink re-check).
3. Current `size` and `content hash` match `sourceSize` / `sourceContentHash` from the stored operation.
4. Destination parent safe; destination file must **not** exist (see destination conflict policy).

Any mismatch → **`STALE_PREVIEW`**; **no FS mutation** for that batch attempt (fail before first op if plan-level check fails; per-row check before each op).

On apply: recompute `planFingerprint` from stored plan; structural mismatch → `STALE_PREVIEW`.

### Concurrency

- Apply holds `LibrarySession` lock (same as scan) for duration of batch.
- New `startScan` or `select_folder` while apply running → **rejected** at bridge with new code `LIBRARY_BUSY` (or queue in plan — default **reject**).
- `libraryRevision` bump rules: see § Rollback / partial failure (partial success with later failure still bumps if ≥1 move succeeded).

### mockBridge vs BridgeApi

| Runtime | Apply behavior |
|---------|----------------|
| Browser `npm run dev` | mockBridge logs plan; **no** real I/O |
| pywebview + BridgeApi | Real I/O via use case |

No automatic fallback to mock on bridge errors.

---

## Dry-run preview contract

Extends [001 PR-13](./001-2026-06-01-pr13-preview-token-stale-apply-design.md); **does not** remove fields.

### `getMovePreview(selection)` — real plan

**Inputs:** `SelectionScope` (unchanged PR-10 shape).

**Process (application layer):**

1. Resolve selection to concrete `ReviewRow` ids from current session index / review row cache.
2. For each row, map `proposedAction` + `targetFolder` + file paths to zero or one **preview operation**.
3. Run domain path policy on each operation (mark conflicts without I/O).
4. Persist pending state: PR-13 fields + `planFingerprint` + serialized `previewOperations`.
5. Return `MovePreviewResult` validated by existing contract.

### `MovePreviewRow` (v1 semantics)

Bridge `MovePreviewRow` remains `{ id, action }` for PR-10 compatibility. Server stores full `PreviewOperation` (including hash/size) in pending state; `id` = `rowId`.

| `action` (preview row) | PR-15 planner |
|------------------------|---------------|
| `move_duplicate` | **Emitted** when path policy passes and destination does not exist |
| `keep` | Not emitted (no-op) |
| `ignore` | Not emitted (no-op) |
| `delete` | **Never emitted** — contract may recognize the string elsewhere; PR-15 planner does not schedule delete |
| `move_organized` | **Not emitted** — if row data implies `move_organized`, count `blockedCount` (not `conflictCount`); user should not read as path conflict |

**Destination conflict (preview):** existing destination file → row omitted from executable plan; increment `conflictCount`; shown in summary only (detail UI → PR-16).

Each row **`id`** must be a real `ReviewRow.id` from the session ([002 greenfield](./002-2026-06-01-novelguard-greenfield-library-session-design.md)).

### `MovePreviewSummary` extensions (additive)

```typescript
interface MovePreviewSummary {
  rowCount: number;
  conflictCount?: number;
  operationCount?: number;  // rows that will mutate FS
  blockedCount?: number;    // unsupported actions (e.g. move_organized), not path conflicts
}
```

Contract validators: optional fields allowed; plan defines strict validation if added.

### Empty selection

Valid: `rows: []`, `summary.rowCount: 0`, `operationCount: 0`, still returns token (user confirmed empty apply is harmless). Apply succeeds as no-op; audit `event: "apply_completed"` with `operationCount: 0` (no separate `empty_apply` event).

### Dry-run ≡ apply

Infrastructure **must not** perform mutation during preview. Optional `FilesystemApplyPort.dry_run_validate(paths)` may stat/check existence only — no rename/unlink in preview phase.

---

## User approval contract

PR-13 UI rules remain authoritative ([001 § UI — ApplySubflowDialog](./001-2026-06-01-pr13-preview-token-stale-apply-design.md)).

PR-15 adds **no new approval surface** in the web UI (that is PR-16).

| Step | User action | Backend |
|------|-------------|---------|
| Open subflow | `batch-preview-open` | — |
| Preview | `apply-preview-run` → `getMovePreview` | Builds real plan |
| Confirm | User reads table; clicks confirm | — |
| Apply | `apply-confirm-run` → `applyResolvedActions` | Executes plan |

**Hard locks:**

- Confirm button **hidden** until preview success (existing E2E).
- Confirm **disabled** when `PreviewState.stale` or bridge `rejected`.
- Cancel/close → `discardMovePreview` (idempotent).
- No new “force apply” or “skip preview” API in PR-15.

Copy changes (Korean) for real paths/conflicts: **PR-16** unless blocking safety — then minimal text in PR-15 plan only.

---

## Audit log

### Purpose

Evidence for support and post-incident review; **not** input to duplicate detection logic.

### Format

Append-only **JSONL** file, one event per line:

```json
{
  "ts": "2026-06-01T12:34:56.789Z",
  "sessionId": "uuid",
  "previewToken": "preview-…",
  "libraryRevision": 3,
  "event": "apply_started" | "apply_row" | "apply_completed" | "apply_failed" | "preview_built",
  "rowId": "file:…",
  "action": "move_duplicate",
  "source": "relative/path.txt",
  "dest": "duplicate/path.txt",
  "outcome": "ok" | "skipped" | "error",
  "error": "optional message"
}
```

### Write points

| Event | When |
|-------|------|
| `preview_built` | After successful `getMovePreview` |
| `apply_started` | After PR-13 validation, before first FS op |
| `apply_row` | Per operation |
| `apply_completed` | Batch end (success or partial) |
| `apply_failed` | Unrecoverable batch abort |

### Location

Under application session storage (e.g. next to SQLite index directory). Exact path chosen in **plan** — must not live inside scanned library root (avoid scan picking up logs).

### Retention

v1: no rotation policy required; document manual cleanup. Rotation → future PR.

---

## Rollback / partial failure policy

### No automatic rollback (v1)

If operation 3 of 10 fails, operations 1–2 **remain committed**. User restores from OS backup or manual undo outside NovelGuard.

**Rationale:** Automatic rollback of arbitrary partial moves is error-prone (overwrites, cross-volume moves). Audit log provides traceability.

### Partial failure behavior

| Situation | Behavior |
|-----------|----------|
| Policy block / destination exists | Preview: `conflictCount++` or `blockedCount++`; row not in executable plan |
| File drift at apply | `STALE_PREVIEW` before mutating (or before next op — plan picks per-row check) |
| FS error mid-batch (e.g. permission, cross-volume) | Stop **remaining** ops; prior ops kept |
| All ops skipped / empty | `applyResolvedActions` resolves **`void`**; audit `apply_completed`, `operationCount: 0` |
| Total batch failure before any FS op | No FS mutation; `PreviewApplyError` or `APPLY_FAILED` |

### Partial success + `Promise<void>` (hard lock)

Example: operations 1–2 move OK; operation 3 fails.

| Aspect | Rule |
|--------|------|
| Bridge return | **`applyResolvedActions` rejects** with `APPLY_FAILED` (not `void`) |
| Audit log | Contains `apply_row` with `outcome: "ok"` for successes and failing row with `outcome: "error"`; ends with `apply_failed` or `apply_completed` per plan |
| `libraryRevision` | **Increment if ≥1 FS move succeeded** |
| Pending preview | **Cleared** after failure if **any** FS operation was attempted (same as success path) |
| UI (PR-15) | Sees structured `BridgeCallError` only — no per-row outcome DTO |
| UI (PR-16+) | May read audit / future `ApplyResult` for row-level display |

Full success (all executable ops OK): **`Promise<void>`** as today.

### New error codes

```typescript
type PreviewApplyErrorCode =
  | /* PR-13 codes */
  | "APPLY_FAILED"           // FS or internal error after guards passed (includes partial batch)
  | "LIBRARY_BUSY";          // scan/apply overlap
```

`APPLY_FAILED` carries message + optional `details` (e.g. `partialSuccess: true`, `succeededCount`, `failedRowId`) for PR-16; PR-15 UI shows generic error only.

### `libraryRevision` (hard lock)

- Increment **once** if **≥1** filesystem move succeeded.
- Do **not** increment on zero-op apply or total failure before any FS touch.
- File drift → `STALE_PREVIEW` (PR-13 family); no increment.

### Index / audit consistency (not a true transaction)

Filesystem moves and SQLite/audit updates **cannot** be one atomic transaction (cross-volume move, permissions, Windows file locks).

**PR-15 ordered best-effort consistency (per operation):**

```text
1. validate operation (path policy + file drift)
2. execute filesystem move
3. append audit apply_row
4. update in-memory / SQLite index for affected FileRecord
5. if step 4 fails after step 2 succeeded → audit severity critical + APPLY_FAILED
```

**Plan may additionally choose** (document in PR-15 plan):

- **Option A:** best-effort per-row index patch (above), or
- **Option B:** after apply success or partial success with ≥1 move, **force rescan / full index refresh** (safer, slower)

Do **not** describe FS + SQLite as “same transaction” in docs or code comments.

---

## Filesystem mutation boundary

### Layer placement

```text
domain/          Pure policies (path allowed?, action allowed?)
application/     BuildPreviewPlanUseCase, ApplyResolvedActionsUseCase
application/ports/  FilesystemApplyPort (protocol)
infrastructure/  LocalFilesystemApplyAdapter (move/rename only; no delete in PR-15)
app/bridge_api   validate PR-13 → call use cases → audit
```

### Domain (도미닉)

- **No** `open()`, `shutil`, `pathlib` mutation.
- Value objects / functions: `ResolvedApplyOperation`, `ApplyPathPolicy.validate(operation, library_root) -> PolicyResult`.

### Application (유리)

- Resolve `SelectionScope` → rows → operations.
- Orchestrate preview vs apply.
- Call `FilesystemApplyPort` only through protocol.
- Bump session revision via `LibrarySession` API (not bridge ad hoc).

### Infrastructure (아다)

- Implements `FilesystemApplyPort`.
- Maps `PermissionError`, `FileNotFoundError`, etc. to typed `ApplyRowResult`.
- Creates destination dirs under library root.

### Forbidden

- FS mutation inside `BridgeApi` beyond delegation.
- FS mutation inside `web/` React code.
- Bypass preview token checks “for efficiency”.
- Writing audit entries into scanned novel folders.

---

## `BridgeApi` thin boundary

### Responsibilities (keep)

1. DTO validation (`validate_selection_scope`, `validate_move_preview`).
2. PR-13 pending preview lifecycle (`previewToken`, fingerprint, revision, `planFingerprint`).
3. Map `PreviewApplyError` / `ApplyFailedError` to JS bridge contract.
4. Delegate `get_move_preview` → `BuildPreviewPlanUseCase`.
5. Delegate `apply_resolved_actions` → `ApplyResolvedActionsUseCase` after `_validate_apply`.

### Move out of bridge (optional in PR-15)

- Preview pending state → `app/preview_apply_guard.py` (same behavior).
- **Not required** if risk delays PR-15; PR-30 remains escape valve.

### `LibrarySession` interaction

- Session exposes `library_root()`, `library_revision()`, `increment_revision()`, row lookup by id.
- Apply use case receives session + port; bridge does not iterate files directly.

### Parity

`NOVEL_GUARD_BRIDGE_METHODS` / `PYWEBVIEW_API_METHODS` unchanged unless new methods added (none in PR-15).

---

## Tests and manual smoke

### Automated (extend existing files only)

Unless user grants `TEST_ALLOWED` for new files:

| Layer | File (existing) | New cases |
|-------|-----------------|-----------|
| Pytest | `tests/test_bridge_contract.py` | Real temp dir: preview lists real row ids; apply moves file; token stale blocks; audit file created |
| Pytest | `tests/test_apply_path_policy.py` **only if file exists** — else add cases to nearest domain test module | `..` escape, outside root rejected |
| Vitest | `web/src/bridge/bridgeParity.test.ts` | Optional `operationCount` in summary if contract extended |
| Vitest | mockBridge | Plan stored; apply clears pending; still no real I/O |
| E2E | `web/e2e/smoke.spec.ts` | Phase 0 triage; **no** real FS in CI (mockBridge only) |

**Integration tests** use `tempfile.TemporaryDirectory` as library root; never user home.

### Manual smoke (desktop)

Recorded in plan checklist:

1. `python src/main.py` (or webview entry) — select small test folder (2–3 txt, one duplicate pair).
2. Scan → Resolve → select duplicate member → preview → confirm table shows real paths.
3. Apply → verify file moved on disk; grid refresh or rescan reflects change.
4. Cancel path: preview → close dialog → `hasPendingApply` false.
5. Stale: preview → rescan → apply disabled.
6. Inspect audit JSONL for `preview_built` + `apply_row` lines.

### Verification gate

`python scripts/verify_phase_completion.py` must pass before PR-15 slice declared done.

---

## Non-goals (PR-15)

- Resolve UI outcome panels, toasts, per-row error grid (**PR-16**)
- Review state persistence (`approved`, keeper edits) (**PR-17**)
- `getDuplicateGroupDetail` / DetailPanel (**PR-18**)
- Near/relation duplicate apply (**PR-19+**)
- Quality UTF-8 repair / finalize (**PR-21+**)
- Packaging / production `run.bat` (**PR-24**)
- Changing PR-10 query pagination rules
- Automatic rollback / trash-can restore
- **`delete` execution** (hard delete or trash) — future spec after PR-16/17
- `move_organized` chosung layout

---

## PR-16 boundary (explicit)

| Concern | PR-15 | PR-16 |
|---------|-------|-------|
| Execute FS operations | Yes | No |
| Audit log write | Yes | Read optional |
| Show per-row apply result in UI | Minimal errors only | Yes |
| `ApplyResult` bridge type | Internal Python DTO | Expose to TS if needed |
| Post-apply snapshot messaging | Revision bump only | User-facing copy |

---

## Implementation plan outline (for `writing-plans` — not part of approval)

| Task | Content |
|------|---------|
| 0 | E2E preflight per § Phase 0 |
| 1 | `ApplyPathPolicy` + `PreviewOperation` model (incl. destination-exists conflict) |
| 2 | `FilesystemApplyPort` + local adapter (**move only**) |
| 3 | `BuildPreviewPlanUseCase` + immutable `planFingerprint` / pending state |
| 4 | `ApplyResolvedActionsUseCase` + file drift validation + partial semantics |
| 5 | Audit JSONL writer |
| 6 | `BridgeApi` thin delegation |
| 7 | SQLite / in-memory index refresh after apply (best-effort or rescan — pick in plan) |
| 8 | Contract tests + manual smoke |

**Start plan only after this spec approval (done).**

---

## Approval checklist

- [x] Phase 0 E2E gate acceptable
- [x] Safety model: path confinement + dry-run ≡ apply plan + file drift fields
- [x] PR-13 guards preserved; no bypass
- [x] **`delete` not emitted or executed in PR-15**
- [x] Partial failure: `APPLY_FAILED` on partial batch; revision bump if ≥1 move OK; pending cleared
- [x] FS + index/audit: best-effort ordering, not atomic transaction
- [x] Destination exists → conflict, no overwrite / auto-rename
- [x] FS mutation only in application + infrastructure ports (**move only**)
- [x] `BridgeApi` stays thin delegate
- [x] `move_organized` → omitted + `blockedCount` (not conflict)
- [x] PR-16 boundary agreed
- [x] Test strategy uses existing files / temp dirs only

---

## Changelog

| Date | Change |
|------|--------|
| 2026-06-01 | Initial PR-15 spec draft from master roadmap review |
| 2026-06-01 | Spec review: delete ban; PreviewOperation drift fields; non-atomic FS/index; partial `APPLY_FAILED` semantics; destination conflict; symlink wording; approved |
