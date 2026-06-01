# PR-15: Real Apply Use Cases — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire `getMovePreview` / `applyResolvedActions` to **real dry-run planning** and **real `move_duplicate` filesystem moves** while preserving all PR-13 preview-token / stale-apply guards.

**Architecture:** Domain `ApplyPathPolicy` validates paths and destination conflicts. Application use cases build an immutable `PreviewOperation` list (with `sourceContentHash` / size / file id), persist it with PR-13 pending state, and execute moves through `FilesystemApplyPort`. `BridgeApi` validates DTOs and delegates only. After ≥1 successful move, `LibrarySession` runs **conservative refresh-from-disk** (Option B) — not FS+SQLite atomicity. Append-only audit JSONL lives under `~/.novelguard/`, outside the scanned library root.

**Tech Stack:** Python 3.12 (`domain` / `application` / `infrastructure` / `app`), existing PR-10 bridge DTOs, React unchanged in PR-15 (PR-16 UI outcomes), Vitest + Playwright (extend existing files only).

**Spec:** [003-2026-06-01-real-apply-use-cases-design.md](../specs/003-2026-06-01-real-apply-use-cases-design.md) (**approved**)

**Plan status:** **Approved** (2026-06-01) — plan gate: Task 7 revision/refresh order locked; `STALE_PREVIEW` pending policy; refresh-failure semantics.

**Parent:** [000 master roadmap](../roadmap/000-2026-06-01-novelguard-master-roadmap.md) — Wave A PR-15

**Test policy:** No new `test_*.py` / `*.test.tsx` files unless user grants `TEST_ALLOWED`. Extend:

- `tests/test_bridge_contract.py`
- `web/src/bridge/bridgeParity.test.ts` (and existing mock/contract tests as needed)
- `web/e2e/smoke.spec.ts`

Path-policy unit cases → `tests/test_bridge_contract.py` (or `tests/test_scaffold.py` if adding domain-only helpers there). Do **not** create `tests/test_apply_path_policy.py` without approval.

**Non-goals (PR-15):** `delete` emit/execute; overwrite; auto-rename; rollback; PR-16 apply outcome UI; review-state persistence; `move_organized` execution; near/relation; quality repair; new bridge methods; mockBridge removal for browser dev.

---

## Plan-locked decisions

### PR-15 safety mantra

```text
PR-15 = real move_duplicate only
no delete
no overwrite
no auto-rename
no rollback
preview and apply use the same immutable PreviewOperation plan
after success or partial success (>=1 move), conservative index refresh from disk
```

### Hard locks (from spec)

| Lock | Value |
|------|--------|
| FS mutation | **`move_duplicate` only** via `FilesystemApplyPort.move_file` |
| `delete` | Never emitted by planner; never executed |
| PR-13 guards | `previewToken`, `libraryRevision`, `selectionFingerprint` unchanged |
| Plan row | `PreviewOperation` includes `sourceFileId`, `sourceSize`, `sourceContentHash`, optional `sourceMtimeNs` |
| Destination exists | Preview conflict; not executable; no overwrite / auto-rename |
| Partial batch | `APPLY_FAILED`; audit has ok+error rows; revision++ if ≥1 move; pending cleared if any FS attempted |
| Bridge | Thin delegate; no FS in `BridgeApi` |
| mockBridge | Browser dev only; **no** pywebview failure fallback |

### Index consistency — **Option B (locked)**

```text
After apply success OR partial success with >=1 filesystem move:
  LibrarySession.refresh_index_from_disk()
    - synchronous re-walk of library_root (reuse scan_folder + content hash)
    - rebuild review + quality caches (_rebuild_review_index / _rebuild_quality_index)
    - do NOT claim FS + SQLite atomicity
```

**Conservative refresh (locked nuance):** Prefer full re-walk + cache rebuild. If manual smoke shows unacceptable latency on large folders, implementation may keep the same re-walk but **without** starting the background pipeline UI (inline walk only). **Do not** switch to per-row SQLite patch in PR-15 (that is Option A / future optimization).

**Revision bump (locked):** When ≥1 move succeeds, `increment_library_revision()` runs **once** immediately after the move loop and per-row `apply_row` audit events, **before** `refresh_index_from_disk()`. That bump marks the moment filesystem truth diverged from the preview baseline. `refresh_index_from_disk()` only rebuilds index/caches and **MUST NOT** increment `libraryRevision`.

### Audit log path (locked)

```text
~/.novelguard/apply-audit.jsonl   # same parent as default_library_db_path()
Must NOT be under library_root (scanned folder)
```

Use `sessionId` = stable id per `LibrarySession` / db path (plan: hash of db path or uuid stored on first write).

### Pending preview state (locked)

Store on bridge or `app/preview_apply_guard.py`:

```python
{
  "token": str,
  "fingerprint": str,           # selectionFingerprint
  "library_revision": int,
  "plan_fingerprint": str,
  "preview_operations": list[dict],  # PreviewOperation serialized
}
```

### `APPLY_FAILED` / `LIBRARY_BUSY`

- Extend `PreviewApplyError` / TS `PreviewApplyErrorCode` in existing modules.
- `ApplyFailedError` optional `details`: `{ "partialSuccess": true, "succeededCount": n, "failedRowId": "..." }`.

### Content hash at preview

1. Prefer `FileRecord.content_sha256` from index when present.
2. Else `infrastructure.content_hasher.hash_file` at preview time (preview phase only — not a mutation).

### Drift check at apply

Per operation, before move:

```text
source exists; resolved under library_root
size + sha256 match PreviewOperation
destination file must not exist
```

Any failure → `STALE_PREVIEW` (no FS mutation for remaining batch — fail fast before first op on plan-level drift; per-row before each op).

### `STALE_PREVIEW` pending handling (locked)

On `STALE_PREVIEW` at apply (plan drift, file drift, or fingerprint mismatch):

```text
1. Clear pending preview state (previewToken invalidated)
2. Set hasPendingApply = false
3. Do not increment libraryRevision (no FS mutation in this path)
4. UI must obtain a new preview via getMovePreview before apply — no reuse of old token
```

Do **not** leave orphan pending state that could confuse preflight.

### Refresh failure after successful move(s) (locked)

If ≥1 move succeeded and `increment_library_revision()` already ran, then `refresh_index_from_disk()` fails:

```text
- libraryRevision: already bumped (keep)
- pending: clear (same as post-apply cleanup)
- bridge: APPLY_FAILED with details indicating refresh failure after partial/total move success
- audit: apply_failed or apply_row + critical note that index refresh failed (FS state is truth; index may be stale until manual rescan)
```

---

## Current state (baseline)

| Item | Status |
|------|--------|
| `BridgeApi.get_move_preview` | Stub: one synthetic row via `first_file_id()` |
| `BridgeApi.apply_resolved_actions` | PR-13 validate; **no FS** |
| `LibrarySession` | Real scan/index; `_review_rows_cache`; no apply use cases |
| `FilesystemApplyPort` | **Missing** |
| `ApplyPathPolicy` / `PreviewOperation` | **Missing** |
| Audit JSONL | **Missing** |
| `mockBridge` | PR-13 simulation; no real I/O |
| E2E apply smoke | Present (mockBridge); last run artifact may show 0 failures — **re-run in Task 0** |

---

## File map

| File | Action |
|------|--------|
| `src/domain/apply_path_policy.py` | **Create** — path confinement, destination-exists, symlink rules |
| `src/domain/apply_models.py` | **Create** — `PreviewOperation`, `PolicyResult`, `ApplyRowOutcome` (pure types) |
| `src/application/ports/filesystem_apply.py` | **Create** — `FilesystemApplyPort` protocol |
| `src/infrastructure/local_filesystem_apply.py` | **Create** — move-only adapter (`shutil.move` / `rename`) |
| `src/application/build_preview_plan.py` | **Create** — `BuildPreviewPlanUseCase` |
| `src/application/apply_resolved_actions.py` | **Create** — `ApplyResolvedActionsUseCase` |
| `src/application/audit_log.py` | **Create** — JSONL append writer |
| `src/application/plan_fingerprint.py` | **Create** — canonical JSON + sha256 (mirror selection fingerprint style) |
| `src/app/preview_apply_guard.py` | **Create** (recommended) — pending state + plan storage |
| `src/app/bridge_api.py` | **Modify** — thin delegate to use cases |
| `src/application/library_session.py` | **Modify** — `library_root()`, `refresh_index_from_disk()`, `increment_library_revision()`, apply-busy flag |
| `src/app/bridge_contract.py` | **Modify** — `APPLY_FAILED`, `LIBRARY_BUSY`; optional summary fields |
| `src/app/session_factory.py` | **Modify** — wire port + use cases if needed |
| `web/src/types/movePreview.ts` | **Modify** — add `APPLY_FAILED`, `LIBRARY_BUSY` to error union |
| `web/src/bridge/mockBridge.ts` | **Modify** — align planner simulation (move only; store plan fingerprint) |
| `tests/test_bridge_contract.py` | **Extend** — temp-dir integration, path policy cases |
| `web/src/bridge/bridgeParity.test.ts` | **Extend** — error codes parity if added |
| `docs/entry_points.md` | **Modify** — PR-15 real apply behavior |
| `docs/superpowers/roadmap/000-…-master-roadmap.md` | **Modify** on Task 9 — PR-15 done |

---

## Acceptance criteria

```text
✓ Task 0: E2E preflight recorded; blocking apply-path failures = 0
✓ get_move_preview returns real ReviewRow ids for move_duplicate rows in temp-dir session
✓ PreviewOperation stored with sourceFileId, sourceSize, sourceContentHash
✓ delete / move_organized never appear in executable preview plan
✓ destination exists → conflictCount; row not in executable plan
✓ apply_resolved_actions moves file on disk for move_duplicate (temp dir)
✓ File drift after preview → STALE_PREVIEW; no move
✓ Partial batch: 2 ok, 3rd fails → APPLY_FAILED; audit has apply_row ok+error; revision bumped
✓ Empty plan apply → void; audit apply_completed operationCount 0
✓ After >=1 move: revision bumps once before refresh; refresh_index_from_disk does not bump again
✓ STALE_PREVIEW clears pending; re-preview required
✓ Refresh failure after move: APPLY_FAILED; revision kept; audit notes refresh failure
✓ No overwrite, no auto-rename, no delete, no rollback
✓ BridgeApi contains no shutil/open for mutation
✓ mockBridge: no real I/O; pywebviewBridge does not fallback to mock
✓ python scripts/verify_phase_completion.py PASS
✓ Manual smoke checklist signed off (Task 9)
```

---

## Commit strategy (recommended)

| Commit | Content |
|--------|---------|
| `[docs] PR-15 real apply implementation plan` | This file only (if committed separately) |
| `[app] add apply path policy and filesystem move port` | Tasks 1–2 |
| `[app] build real move preview plan` | Task 3 + bridge preview delegate |
| `[app] execute real move apply with audit` | Tasks 4–6 |
| `[app] refresh library index after apply` | Task 7 |
| `[tests] cover PR-15 real apply safety gates` | Task 8 |
| `[docs] mark PR-15 complete` | Task 9 only |

Squash allowed if user prefers one PR commit; keep logical order for review.

---

### Task 0: E2E preflight

**Files:**
- Modify (only if blocking): `web/e2e/smoke.spec.ts`, related bridge/mock fixes
- Record: plan PR notes section below

- [x] **Step 1: Run E2E**

Run: `cd web && npm run test:e2e`

- [x] **Step 2: Triage**

| Test | Blocker? | Action |
|------|----------|--------|
| `preview failure blocks apply` | Yes | PASS — no fix |
| `closing apply dialog discards pending preview` | Yes | PASS — no fix |
| `library revision bump shows stale banner` | Yes | PASS — no fix |
| Others | — | PASS (13/13) |

- [x] **Step 3: Exit gate**

Blocking failures = **0** — proceed to Task 1.

- [x] **Step 4: Commit** (only if code changed)

No code changes required.

**Task 0 PR notes:**

```text
Date: 2026-06-01
Command: cd web; npm run test:e2e
Result: 13 passed (5.5s), 0 failed
Blocking apply-path tests: all PASS
Classification: N/A (no failures)
Gate: EXIT — Task 1 approved
```

---

### Task 1: ApplyPathPolicy + PreviewOperation model

**Files:**
- Create: `src/domain/apply_models.py`
- Create: `src/domain/apply_path_policy.py`
- Modify: `tests/test_bridge_contract.py` (path policy cases)

- [x] **Step 1: Define `PreviewOperation` dataclass** (`apply_models.py`)

Fields per spec: `row_id`, `action` (literal `move_duplicate`), `source_path`, `dest_path`, `source_file_id`, `source_size`, `source_content_hash`, `source_mtime_ns: int | None`.

- [x] **Step 2: Implement `ApplyPathPolicy`**

Functions (pure):

- `resolve_under_library_root(library_root: Path, relative: str) -> Path`
- `validate_move_operation(library_root, op) -> PolicyResult` — blocked reasons: `outside_root`, `destination_exists`, `invalid_target`, `unsupported_action`
- Symlink rules: resolve existing source + dest parent; non-existing dest = parent resolve + basename join

- [x] **Step 3: Add pytest cases** in `tests/test_bridge_contract.py`

Cases (temp `Path` fixtures):

- `..` escape → blocked
- path outside root → blocked
- destination file exists → `destination_exists`
- valid move → allowed

Run: `python -m pytest tests/test_bridge_contract.py -k "apply_path" -v` — **4 passed** (2026-06-01)

- [x] **Step 4: Commit** — combined with Task 2 (2026-06-01)

---

### Task 2: FilesystemApplyPort + LocalFilesystemApplyAdapter

**Files:**
- Create: `src/application/ports/filesystem_apply.py`
- Create: `src/infrastructure/local_filesystem_apply.py`

- [x] **Step 1: Define port** — `filesystem_apply.py` (move only; no delete APIs)

- [x] **Step 2: Implement adapter** — `LocalFilesystemApplyAdapter`; `move_file` rejects existing dest

- [x] **Step 3: Smoke test** — 7 passed (`apply_path` + `filesystem_apply`, 2026-06-01)

- [x] **Step 4: Commit** — combined with Task 1: `[app] add apply path policy and filesystem move port`

---

### Task 3: BuildPreviewPlanUseCase

**Files:**
- Create: `src/application/plan_fingerprint.py`
- Create: `src/application/build_preview_plan.py`
- Modify: `src/application/library_session.py` — helpers: `library_root()`, `review_rows_for_selection()`, `file_record_for_row_id()`
- Modify: `src/app/preview_apply_guard.py` (create) or `bridge_api.py` pending structure
- Modify: `src/app/bridge_api.py` — delegate `get_move_preview`

- [ ] **Step 1: Selection → rows**

Resolve `SelectionScope` against `_review_rows_cache` + `_files_by_id` (explicit row ids, filters, etc. — match existing query semantics).

- [ ] **Step 2: Planner rules**

| `proposedAction` | Plan |
|------------------|------|
| `move_duplicate` | Build op when policy allows |
| `keep`, `ignore` | Skip |
| `delete` | **Never emit** |
| `move_organized` | Skip; count `blockedCount` |

Set `MovePreviewRow` `{ id: rowId, action: "move_duplicate" }` only for executable ops.

Populate `summary`: `rowCount`, `operationCount`, `conflictCount`, `blockedCount`.

- [ ] **Step 3: `plan_fingerprint`**

Canonical JSON (PR-13 rules) over serialized `preview_operations` list.

- [ ] **Step 4: Persist pending** via `preview_apply_guard` + PR-13 token/fingerprint/revision

- [ ] **Step 5: Audit `preview_built`**

- [ ] **Step 6: Wire `BridgeApi.get_move_preview`**

Validate selection → use case → `validate_move_preview` → return.

- [ ] **Step 7: Pytest**

Temp library with duplicate pair from scan fixture pattern; preview returns member row id; `operationCount >= 1`.

- [ ] **Step 8: Commit**

```bash
git commit -m "[app] build real move preview plan"
```

---

### Task 4: ApplyResolvedActionsUseCase

**Files:**
- Create: `src/application/apply_resolved_actions.py`
- Modify: `src/app/bridge_contract.py` — `ApplyFailedError`, codes
- Modify: `src/app/bridge_api.py` — delegate after `_validate_apply`

- [ ] **Step 1: Load stored plan** by `previewToken` (must match pending)

- [ ] **Step 2: Plan-level checks**

- `plan_fingerprint` matches stored operations
- `LIBRARY_BUSY` if session scan/apply flag set

- [ ] **Step 3: Per-operation loop**

```text
drift check → ensure_parent_dir → move_file → audit apply_row
on error: stop, record partial, raise APPLY_FAILED with details
```

- [ ] **Step 4: Completion**

| Outcome | Bridge | Revision | Pending | Audit |
|---------|--------|----------|---------|-------|
| All ok | `void` | +1 if ≥1 move | clear | `apply_completed` |
| Partial | `APPLY_FAILED` | +1 if ≥1 move | clear if any FS tried | `apply_failed` + row events |
| Empty | `void` | no bump | clear | `apply_completed` op=0 |
| Drift before any FS | `STALE_PREVIEW` | no bump | **clear** pending | no row moves |

- [ ] **Step 5: Pytest**

- Happy path move
- Drift hash → `STALE_PREVIEW`
- Destination pre-created → should have been preview conflict; if in plan, `STALE_PREVIEW` at apply

- [ ] **Step 6: Commit**

```bash
git commit -m "[app] execute real move apply with audit"
```

---

### Task 5: Audit JSONL writer

**Files:**
- Create: `src/application/audit_log.py`

- [ ] **Step 1: Implement append-only writer**

`AuditLog.append(event: dict)` — ISO `ts`, ensure `sessionId` on first write.

- [ ] **Step 2: Integrate** in preview + apply use cases

Events: `preview_built`, `apply_started`, `apply_row`, `apply_completed`, `apply_failed`.

- [ ] **Step 3: Pytest**

After preview+apply in temp session, `~/.novelguard/apply-audit.jsonl` (or test override path via injection) contains `preview_built` and `apply_row`.

Use `tmp_path` + inject audit path in `create_library_session` test hook.

- [ ] **Step 4: Commit** (may squash with Task 4 if preferred)

```bash
git commit -m "[app] add apply audit JSONL writer"
```

---

### Task 6: BridgeApi thin delegation

**Files:**
- Create: `src/app/preview_apply_guard.py` (if not done)
- Modify: `src/app/bridge_api.py`
- Modify: `web/src/types/movePreview.ts` — error codes
- Modify: `web/src/bridge/mockBridge.ts` — align plan storage / move-only simulation

- [ ] **Step 1: Extract PR-13 pending + plan** to `preview_apply_guard.py`

`BridgeApi` calls guard for validate/store/clear.

- [ ] **Step 2: Ensure `bridge_api` has no FS imports**

- [ ] **Step 3: mockBridge**

Store `previewOperations` + `planFingerprint`; simulate move without I/O; never emit `delete`.

- [ ] **Step 4: Vitest**

Run: `cd web && npm run test:contracts`

Extend `bridgeParity.test.ts` only if new error codes need parity asserts.

- [ ] **Step 5: Commit**

```bash
git commit -m "[app] thin BridgeApi delegation for real apply"
```

---

### Task 7: Refresh / index consistency after apply

**Files:**
- Modify: `src/application/library_session.py`

- [ ] **Step 1: Add `refresh_index_from_disk()`**

Under `_lock`:

- Require `folder_path` set
- Synchronous `scan_folder` into new file list (reuse `_scan_with_content_hash` pattern)
- `_index.replace_files` + `_rebuild_review_index` + `_rebuild_quality_index`
- **Do not** increment `libraryRevision` here

- [ ] **Step 2: Call from `ApplyResolvedActionsUseCase`** — **order (locked)**

```text
1. execute move loop
2. audit apply_row events (per successful/failed row)
3. if succeeded_count >= 1: increment_library_revision() exactly once
4. if succeeded_count >= 1: refresh_index_from_disk()
5. audit apply_completed / apply_failed
6. clear pending according to apply outcome (success, partial, or empty)

refresh_index_from_disk() MUST NOT increment libraryRevision.
```

Meaning: once step 3 runs, the library is at a new revision relative to the preview token; step 4 only reconciles index/caches to disk.

**Refresh failure:** If step 4 raises after step 3, follow § Refresh failure after successful move(s) — `APPLY_FAILED`, pending clear, audit critical note.

- [ ] **Step 3: Apply-busy flag**

Set `_apply_in_progress` during batch; reject `start_scan` / `select_folder` with `LIBRARY_BUSY`.

- [ ] **Step 4: Pytest**

After apply moves duplicate file, `query_review_rows` reflects new paths without manual `start_scan`.

Optional: simulate refresh failure after move → `APPLY_FAILED`, revision already bumped, audit records refresh failure.

- [ ] **Step 5: Commit**

```bash
git commit -m "[app] refresh library index after apply"
```

---

### Task 8: Contract tests + manual smoke

**Files:**
- Modify: `tests/test_bridge_contract.py`
- Modify: `web/src/bridge/bridgeParity.test.ts` (if needed)
- Modify: `web/e2e/smoke.spec.ts` (only if Phase 0 required)

- [ ] **Step 1: Integration suite** (temp dir)

| Case | Assert |
|------|--------|
| Preview real row ids | `file:` prefix ids from session |
| Apply moves file | `Path` exists at dest |
| Token reuse | `NO_PENDING_APPLY` |
| Revision stale | `STALE_PREVIEW` |
| Partial failure | `APPLY_FAILED` + audit |

- [ ] **Step 2: Run Python tests**

`python -m pytest tests/test_bridge_contract.py -v`

- [ ] **Step 3: Run web contracts + E2E**

```bash
cd web && npm run test:contracts
cd web && npm run test:e2e
```

- [ ] **Step 4: Manual smoke (desktop)**

1. `python src/main.py` — select small folder (2–3 txt, one duplicate pair).
2. Scan → Resolve → select duplicate member → Preview → confirm paths.
3. Apply → file on disk moved; grid consistent after refresh.
4. Cancel → `hasPendingApply` false.
5. Rescan after preview → stale banner; apply disabled.
6. Open `~/.novelguard/apply-audit.jsonl` — `preview_built`, `apply_row`.

- [ ] **Step 5: Commit**

```bash
git commit -m "[tests] cover PR-15 real apply safety gates"
```

---

### Task 9: Verification + docs closeout

**Files:**
- Modify: `docs/entry_points.md`
- Modify: `docs/superpowers/roadmap/000-2026-06-01-novelguard-master-roadmap.md`
- Modify: `docs/superpowers/README.md`
- Modify: `docs/superpowers/specs/003-…-design.md` — add plan link under Status (optional one line)

- [ ] **Step 1: Full verification**

Run: `python scripts/verify_phase_completion.py`

Record pass/fail counts in PR notes.

- [ ] **Step 2: Update `entry_points.md`**

Document: real `move_duplicate` apply; delete forbidden; audit path; refresh-after-apply.

- [ ] **Step 3: Roadmap**

PR-15 row → **Done**; Next → PR-16 spec/plan.

- [ ] **Step 4: Plan scope freeze**

No Task 10+ without new spec/plan cycle.

- [ ] **Step 5: Commit**

```bash
git commit -m "[docs] mark PR-15 complete"
```

---

## Plan scope freeze

When Tasks 0–9 are complete and verification passes, **stop**. Do not add PR-16 UI work, delete/trash, or per-row SQLite patch optimization in this slice.

---

## Risk register

| Risk | Mitigation |
|------|------------|
| Large library refresh slow | Inline walk without pipeline UI; document in manual smoke |
| Cross-volume move fails | `APPLY_FAILED`; audit; no rollback |
| Windows file lock | Same; partial semantics |
| Hash missing on old index | Hash at preview via `hash_file` |
| Index drift after move | Option B refresh |

---

## Changelog

| Date | Change |
|------|--------|
| 2026-06-01 | Initial PR-15 plan from approved spec 003; Option B refresh locked; Tasks 0–9 |
| 2026-06-01 | Plan gate: Task 7 order locked (bump then refresh); STALE_PREVIEW clear pending; refresh-failure semantics; approved |
