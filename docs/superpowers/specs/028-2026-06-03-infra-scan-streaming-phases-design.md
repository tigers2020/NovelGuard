---
title: Streaming scan pipeline and phased UI
status: approved
grill_me: 2026-06-03
approved: 2026-06-03
date: 2026-06-03
authors: design review (user) + codebase alignment
parent_spec: docs/superpowers/specs/002-2026-06-01-novelguard-greenfield-library-session-design.md
related_specs:
  - docs/superpowers/specs/013-2026-06-02-shell-filedock-design.md
  - docs/superpowers/specs/007-2026-06-01-near-duplicate-detection-design.md
  - docs/superpowers/specs/023-2026-06-02-feature-ui-scan-scan-section-design.md
pr_label: PR-46
plan: docs/superpowers/plans/046-2026-06-03-infra-scan-streaming-phases.md
---

# 028 — Streaming Scan Pipeline and Phased UI

## Status

**Approved** (2026-06-03) — product decision **C** locked; first implementation slice **A + B** (streaming persist + phase UX). Policy slice **C** (deep analysis scheduling) follows in the same PR where cheap, otherwise as a thin follow-up.

## Scope sentence

Fix **7k+ file scan freeze at 100%** by never holding the full library in RAM, persisting in batches with visible progress, and separating **index-ready** from **deep-analysis-complete** in bridge snapshot + UI. **No Work hub IA change** in this spec.

---

## 1. Terminology map (review doc → NovelGuard code)

| Review / product term | Codebase term |
| --------------------- | ------------- |
| FileDataStore | `LibraryIndexPort` (`SqliteLibraryIndex`), `library.fileCount` / `library.totalBytes` on `AppSnapshot` |
| WorkFileDock | `ShellFileDock` (`web/src/components/layout/ShellFileDock.tsx`) |
| `scan_completed` (single gate) | `work.scan.state` + `pipeline.phase` + new readiness flags (this spec) |
| Real-time batch add | Batch `replace_files` / `append_files` + `libraryRevision` bump per batch |
| Wizard + bottom dock | `WorkRoute` tabs + global `ShellFileDock` (unchanged layout) |

---

## 2. Problem

Observed on ~7,392 files (`F:\kiwi\text\소설\정리`):

1. Progress shows **100%** and label **스캔 중 (7392/7392)** for a long time.
2. **ShellFileDock** and scan summary show **0 files** until the entire scan + post-process finishes.
3. App feels frozen: pywebview polls `get_snapshot()` while the scan thread holds large in-memory structures or runs monolithic SQLite writes.

Root causes in current implementation (2026-06-03):

| Issue | Detail |
| ----- | ------ |
| RAM peak | All `FileRecord` instances accumulated in `collected[]`, including optional `near_text_preview` (up to ~256 KiB head per text file). |
| Monolithic persist | After probe, `_records_for_persistence(collected)` duplicates rows, then one large `replace_files`. |
| Single completion signal | `work.scan.state` stays `running` until persist + exact/quality rebuild finish; UI treats scan as incomplete. |
| Phase conflation | `pipeline.phase` remains `scan` during persist; label can stay **스캔 중** at 100%. |
| `file_count` source | `SqliteLibraryIndex.file_count()` only reflects committed rows; no partial count during save. |
| Deep analysis cost | Near/relation phases run on full library; acceptable in background but must not block index-ready UX. |

---

## 3. Product decision (locked)

**C — 목록은 빨리, 분석은 끝까지**

- User sees **file list and counts** as soon as the first index batch is committed.
- Near duplicate and relation may continue **in background** after the file list is usable.
- Exact duplicate bucketing (size + fingerprint) and quality detect run during **`exact_index`** before `scan.state=success` (cheap, blocking).

**Implementation slices**

| Slice | Content |
| ----- | ------- |
| **PR-1 (this work)** | **A + B**: streaming persist, phase model, snapshot readiness flags, UI labels, batch revision bumps |
| **PR-1 or PR-2** | **C policy**: ≥3,000 files → near/relation default background; optional manual “심층 분석” if already partially present |

---

## 4. Design LOCKs

| ID | LOCK |
| -- | ---- |
| **LOCK-SCAN-1** | Separate the scan lifecycle from a single overloaded phase. Allowed `pipeline.phase` values: `probe`, `persist`, `exact_index`, `analyze`, `idle` only. User-facing “ready” / “analysis done” come from `indexReady` / `deepAnalysisComplete`, not from `pipeline.phase`. Do not emit `pipeline.phase=scan` in new code. |
| **LOCK-SCAN-2** | Do not hold the full library in RAM. Stream probe results into persist batches (default **400** files/batch, tunable 300–500). |
| **LOCK-SCAN-3** | After each persist batch: commit SQLite, bump `libraryRevision`, update `library.fileCount` / `totalBytes` so **ShellFileDock** and scan summary increase without waiting for full library. |
| **LOCK-SCAN-4** | Do **not** store `near_text_preview` on `FileRecord` or in `files` table payload. Near/relation read head samples lazily at analysis time only. |
| **LOCK-SCAN-5** | Forbidden UX: progress **100%** with label still **스캔 중** during persist/index. Persist must use **인덱스 저장 중… (n/total)**. |
| **LOCK-SCAN-6** | Split **`indexReady`** vs **`deepAnalysisComplete`** in snapshot. FileDock “has files” gate uses **`indexReady`**, not deep analysis. |
| **LOCK-SCAN-7** | Libraries with **≥3,000** indexed files: near + relation run in **background** after index-ready (no blocking). Exact/fingerprint index remains automatic. |
| **LOCK-SCAN-8** | No Work hub IA redesign; only scan pipeline, snapshot contract, and phase display. |

---

## 5. Pipeline phases and UI labels

### 5.1 Internal `pipeline.phase` values (bridge)

Allowed values only (validate in `bridge_contract` / TS types):

```text
"idle" | "probe" | "persist" | "exact_index" | "analyze"
```

| `pipeline.phase` | When | `pipeline.cancellable` |
| ---------------- | ---- | ------------------------ |
| `probe` | Walking + content probe | true |
| `persist` | Batch SQLite write | true (cancel = cooperative stop; see §7) |
| `exact_index` | Rebuild exact duplicate rows + quality detect | false |
| `analyze` | Near/relation background | false |
| `idle` | Pipeline idle (deep analysis may still be finishing; see flags) | false |

**Compatibility:** Older snapshots or code paths may still emit `phase="scan"`. Web maps `scan` → `probe` for display and `deriveScanSectionState` only; Python must not emit `scan` after this change.

### 5.2 User-visible `pipeline.label` (Korean)

Labels map to `pipeline.phase` or readiness flags — not a separate phase enum:

| Source | Label pattern |
| ------ | ---------------- |
| `probe` | `파일 확인 중… (n/N)` |
| `persist` | `인덱스 저장 중… (n/N)` |
| `exact_index` | `정확 중복 인덱스 생성 중…` |
| `indexReady` (flag) | `파일 목록 준비됨` (short banner/toast; optional) |
| `analyze` | `중복·관계 분석 중… (백그라운드)` |
| `deepAnalysisComplete` (flag) | (no persistent label; pipeline → `idle` / `대기 중`) |
| `idle` | `대기 중` |

### 5.3 Readiness flags and `work.scan.state` (canonical)

Add under `work.scan` (or top-level `library` — prefer `work.scan` for contract locality):

```typescript
interface ScanSnapshot {
  state: "empty" | "ready" | "running" | "success" | "error";
  lastRun: string | null;
  indexReady: boolean;           // ≥1 batch committed; file list usable
  deepAnalysisComplete: boolean; // near+relation finished (or skipped)
}
```

**Three signals (do not conflate):**

| Signal | Meaning | When set true |
| ------ | ------- | ------------- |
| **`indexReady`** | File list / `query_file_rows` / ShellFileDock usable | First persist batch committed and `library.fileCount > 0` |
| **`work.scan.state = success`** | Scan indexing pass finished (all files persisted + exact/quality index built) | After **`finalize_index`** (`exact_index` phase) completes |
| **`deepAnalysisComplete`** | Near + relation analysis finished (or skipped by policy) | Post-scan worker exits |

Rules:

- `work.scan.state` stays **`running`** until **`finalize_index`** completes — even if `indexReady` is already true.
- `deepAnalysisComplete` is independent; `pipeline.phase` may be `analyze` while `scan.state` is already `success`.
- `deriveScanSectionState` (web): UI “scan running” spinner for `probe` \| `persist` \| `exact_index` only. When `indexReady && scan.state===running`, show persist/exact labels but allow dock. When `scan.state===success`, scan section shows success even if `!deepAnalysisComplete`.

---

## 6. Architecture

### 6.1 Streaming scan flow (backend)

```text
start_scan
  → thread: scan_stream(folder)
       1. collect paths (progress: probe 0–2%)
       2. for each probe batch (size B):
            - parallel probe (existing ThreadPoolExecutor)
            - append_files_batch(folder, records)  # NEW port method
            - on_batch_committed(saved, total) → snapshot progress + revision++
            - after first batch commit → indexReady=true
       3. finalize_index(folder)  # exact_index phase: exact groups, quality, review skeleton
            → scan.state=success, scan.lastRun set
       4. start post_scan_worker (near/relation per LOCK-SCAN-7)
            → deepAnalysisComplete=true, pipeline.phase=idle
       (indexReady may already be true since step 2 batch 1)
```

**Port change:** `LibraryIndexPort.append_files_batch(folder, files)` — insert only; first batch may `DELETE FROM files WHERE folder_path=?` once. Alternative: keep `replace_files` for empty library only, then `append_files_batch`.

### 6.2 Memory budget

| Before | After |
| ------ | ----- |
| O(N) FileRecord + previews in RAM | O(batch_size) during probe+persist |
| Second list via `_records_for_persistence` | Write probe output directly to persist shape (no preview field) |

### 6.3 Near / relation

- Remove `near_text_preview` from `FileRecord` domain model (or keep field always `None` and never persist).
- `read_text_for_near_dup` / `near_text_from_head` only at analysis time.
- Worker uses `index.files()` or paginated file ids — not in-memory `collected`.

### 6.4 Snapshot polling

- `get_snapshot` must stay fast: `file_count` = SQL `COUNT(*)` (already fixed); during persist without commits use `library._index_save_committed` style session fields until batch API makes DB authoritative.
- Per-batch `library_revision += 1` so ShellFileDock `useEffect([libraryRevision])` refetches rows.

### 6.5 UI (web)

| File | Change |
| ---- | ------ |
| `scanSectionState.ts` | `running` iff `scan.state===running`; `success` iff `scan.state===success`; use `indexReady` only for dock/CTA enablement |
| `ScanWorkspace.tsx` | Show `library.fileCount` during persist; enable “전체 파일 목록” when `indexReady` |
| `ShellFileDock.tsx` | Query when `library.fileCount > 0` (already); ensure revision bumps each batch |
| `snapshot.ts` | Add `indexReady`, `deepAnalysisComplete` |
| `GlobalCommandBar.tsx` | Show analyze phase separately from scan progress |

---

## 7. Cancellation

- **probe / persist:** cooperative `cancel_check`; on cancel restore backup (existing semantics).
- **exact_index:** short; non-cancellable acceptable.
- **analyze:** `cancel_run` does not kill background worker v1; optional `post_scan` cancel flag in follow-up.

---

## 8. Thresholds (constants)

| Constant | Value | Purpose |
| -------- | ----- | ------- |
| `SCAN_PERSIST_BATCH_SIZE` | 400 | SQLite insert batch |
| `SCAN_DEEP_ANALYSIS_BACKGROUND_THRESHOLD` | 3000 | Auto background near/relation |
| `SCAN_PROGRESS_THROTTLE_FILES` | 48 | Probe progress callback throttle |
| `SCAN_LARGE_FILE_BYTES` | 2 MiB | Head/tail sample only (existing) |

---

## 9. Acceptance criteria

1. On 7k+ library, label never stays **스캔 중 (N/N)** at 100% during persist.
2. After first batch (~400 files), `library.fileCount > 0` in snapshot and ShellFileDock shows rows.
3. No requirement to wait for full DB commit of all 7k before count moves off zero.
4. Peak RAM does not scale with full library size (verified by batch size × record size, no preview blobs).
5. `indexReady` becomes true after first batch; `work.scan.state === success` only after all persist batches + `exact_index` complete.
6. `pipeline.phase === analyze` may run while `scan.state === success`.
7. `deepAnalysisComplete` becomes true only after near/relation worker finishes (or threshold skip).
8. During background analysis, `query_file_rows` and dock remain usable.
9. Libraries ≥3k: `indexReady` and file dock populate before **중복·관계 분석** completes.
10. Exact duplicate groups available after `exact_index` phase (may be before near rows appear).

---

## 10. Non-goals

- Work hub IA / tab reorder ([021 reconciliation](021-2026-06-02-feature-fullstack-shell-ia-reconciliation-design.md) out of scope).
- PR-29 advanced file grid features.
- Incremental scan / mtime-only refresh (reserved settings keys only).
- Distributed or parallel SQLite across processes.

---

## 11. Testing strategy

| Layer | Tests |
| ----- | ----- |
| Python | Extend `test_bridge_contract`: batch append increases `file_count` mid-scan (mock index + sqlite); phase labels; `indexReady` before worker join; no `near_text_preview` on persisted rows |
| Python | Regression: small library (&lt;10 files) still correct; cancel during persist |
| Web | `scanSectionState` unit tests for new phases; contract test for snapshot fields |
| Manual | 7k folder on `F:` — first ~400 files visible &lt;30s after probe completes |

No new test **files** without user approval per test governance; extend `test_bridge_contract.py` only.

---

## 12. Migration / compatibility

- Bridge snapshot additive fields (`indexReady`, `deepAnalysisComplete`) default `false` in mock bridge until implemented.
- Existing SQLite DBs: no schema change if `near_text_preview` was never stored.
- One-time: users mid-scan on old build → restart scan after upgrade.
- **`pipeline.phase="scan"`:** not emitted by Python after this change. Web treats incoming `scan` as `probe` for labels and section state (compatibility shim only).

---

## 13. Spec self-review

| Check | Result |
| ----- | ------ |
| Placeholders | None |
| Internal consistency | `indexReady` vs `scan.state=success` vs `deepAnalysisComplete` aligned; `pipeline.phase` enum matches LOCK-SCAN-1 |
| Scope | Single pipeline feature; IA excluded per LOCK-SCAN-8 |
| Ambiguity | `append_files_batch` vs `replace_files` — implementer picks one delete-then-append strategy in plan |
| Contradiction with 002 | Extends library session scan lifecycle; does not replace LibrarySession ownership |

---

## 14. Recommended plan outline (for writing-plans)

1. Domain: drop persisted `near_text_preview`; document lazy read.
2. Infrastructure: `append_files_batch`, streaming orchestrator in `filesystem_scanner` / new `scan_stream.py`.
3. Application: refactor `_run_scan`, readiness flags, phase transitions, revision bumps.
4. Bridge: `dto_mapper`, `bridge_contract` validation for new phases/fields.
5. Web: types, `scanSectionState`, ScanWorkspace + command bar labels.
6. Verify: targeted pytest + manual 7k checklist.

---

## 15. Approval

- [x] User approves this spec (spec gate 2026-06-03)
- [x] Approved direction: **C** product goal, **A+B** first implementation slice
- [x] Required pre-plan edits applied:
  - `indexReady` vs `scan.state=success` vs `deepAnalysisComplete` clarified (§5.3)
  - `ready` / `analysis_done` removed from `pipeline.phase` enum; derived from flags/labels only
  - Legacy `phase="scan"` → web compatibility input only
- [x] Plan written under `docs/superpowers/plans/` ([046](../plans/046-2026-06-03-infra-scan-streaming-phases.md))
- [ ] Implementation PR(s)
