---
title: Large-library loading stability design
status: approved
date: 2026-06-05
risk: safe
kind: infra
layer: crosslayer
area: work
tags:
  - large-library
  - bridge
  - sqlite
  - degraded-loading
  - instrumentation
related_specs:
  - docs/superpowers/specs/017-2026-06-02-query-file-rows-advanced-design.md
  - docs/release/smoke-record-large-library.md
---

# Large-library loading stability design

## Summary

Stabilize NovelGuard loading behavior for 7k+ file libraries before any IA refactor or `LibrarySession` split.

Slice 1 combines:

1. **A — instrumentation first**: bridge spans, lock wait timing, SQLite query timing, and post-scan phase transitions.
2. **B-lite — timeout policy + degraded UI**: method-specific bridge timeouts, retry/backoff, and partial-row preservation.
3. **C-targeted — minimal backend relief**: shrink known long lock scopes, sync review projection earlier, and verify SQLite contention settings.

The target user outcome is simple: large libraries may still be slow during background analysis, but the UI must not present a hard timeout failure or wipe already-loaded rows.

## Locked constraints

```text
No IA refactor.
No LibrarySession surgery first.
7k+ repro baseline required.
UI degrades instead of hard failing.
```

Out-of-scope architectural work is deferred until timing data proves the bottleneck.

## 1. Problem and goals

### Problem

In 7k+ libraries, three different failures currently look the same to users:

| Failure mode | Current symptom | Likely root |
|--------------|-----------------|-------------|
| Bridge timeout | UI sees default timeout error | `callBridge` timeout too low for large read paths |
| Scan reaches 100%, but work continues | rows unavailable or stale after progress completes | persist/index/background analysis still running |
| Review query blocks | Resolve grid fails or waits during post-scan | `LibrarySession` lock held during relation/near phases and `query_review_rows` reads in-memory cache under lock |

This makes it impossible to tell whether the system is slow, stuck, or merely still processing.

### Slice 1 goal

The UI must not give up with a user-facing timeout error. It should show partial data as soon as possible, preserve loaded rows, retry with backoff, and expose diagnostics that separate bridge, lock, SQLite, and post-scan phase latency.

### Success criteria for 7k+ libraries

| Check | Pass condition |
|-------|----------------|
| FileDock first page | After `indexReady`, first page appears within 30s, or degraded banner appears while retry preserves partial rows |
| Resolve grid first page | After `indexReady`, first page appears within 30s; no full preload required |
| Bridge timeout error | 0 user-facing hard timeout errors in scripted large-library sequence |
| CI | synthetic 7k fixture smoke exits 0 |
| Operator | `F:\\kiwi\\text\\소설\\정리` manual sign-off checklist passes when available |

## 2. Repro baseline — C, both

Use both deterministic synthetic data and the canonical operator library.

### B — CI synthetic fixture

Add generated fixture support under:

```text
packaging/fixtures/library-large/
```

The repo should not commit 7k generated files. Commit only the generator, manifest, and smoke script.

Required files:

```text
scripts/generate_large_library_fixture.py
scripts/large_library_loading_smoke.py
packaging/fixtures/library-large/manifest.json
```

Fixture requirements:

| Property | Target |
|----------|--------|
| File count | ~7,200 `.txt` files |
| Sizes | mixed small/medium/large text files |
| Exact duplicates | ~30 exact duplicate pairs |
| Stem clusters | ~10 filename/stem clusters |
| Encoding | UTF-8 by default; optional non-UTF-8 samples may be added later |
| Determinism | fixed seed; repeatable filenames and manifest |

Manifest fields:

```json
{
  "expected_file_count": 7200,
  "expected_exact_duplicate_pairs": 30,
  "expected_stem_clusters": 10,
  "generator_seed": 20260605
}
```

Generated data is created on demand in CI/pre-test. A local cache may be reused when the manifest matches.

### A — operator sign-off library

Canonical manual path:

```text
F:\kiwi\text\소설\정리
```

This path is machine-specific and must not be CI-gated. The smoke script accepts:

```bash
python scripts/large_library_loading_smoke.py --folder "F:\kiwi\text\소설\정리"
```

The same measurements and assertions should run, but failure is recorded as operator sign-off failure, not CI failure.

## 3. Instrumentation — Phase 0

Add:

```text
src/application/bridge_timing.py
```

### Span model

```python
BridgeTimingSpan(method: str, t0: float)
```

The implementation should support:

- method name
- elapsed time
- success/failure flag
- exception code/class when failed
- optional structured fields
- DEBUG structured JSON log output
- lightweight aggregate access for smoke testing if useful

### Instrumentation points

| Point | Fields |
|-------|--------|
| `BridgeApi.*` entry/exit | `method`, `elapsed_ms`, `ok`, `error_code` |
| `LibrarySession._lock` waits | `method_or_phase`, `lock_wait_ms`, `holder_phase` when known |
| `SqliteLibraryIndex.query_*` | `query_ms`, `row_count`, `limit`, `offset`, filter summary |
| Post-scan worker | `phase`, `started_at`, `finished_at`, `elapsed_ms` |

### Output

Use existing logging infrastructure and `SessionLogBuffer` with structured DEBUG JSON lines.

Example:

```json
{
  "event": "bridge_timing",
  "method": "query_review_rows",
  "elapsed_ms": 8421,
  "ok": true,
  "lock_wait_ms": 7100,
  "phase": "near_duplicate"
}
```

### No snapshot schema change in Slice 1

Do not add `snapshot.diagnostics` in Slice 1. Logs and smoke measurements are enough. Avoid contract churn until the slow paths are proven.

## 4. Bridge timeout policy — Phase 1

Add a single timeout table:

```text
web/src/bridge/bridgeTimeouts.ts
```

`callBridge` must resolve timeout by bridge method name.

| Method | Timeout | Rationale |
|--------|---------|-----------|
| `get_snapshot` | 5s | poll-heavy; must stay fast |
| `query_file_rows` | 60s | SQLite may be under write load during persist/index |
| `query_review_rows` | 45s | may wait on session lock until C-targeted fix lands |
| `query_quality_rows` | 45s | same class of read query |
| `start_scan` | 10s | fire-and-forget; should return quickly |
| `get_move_preview` | 120s | large selection planning may be slow |
| default | 15s | safer than previous 8s default without masking very slow operations indefinitely |

Acceptance rule: method-specific timeout changes reduce false timeout failures, but do not replace instrumentation or backend fixes.

## 5. UI degraded loading

### Shared behavior

Add a shared hook for query-style bridge reads:

```text
web/src/features/shared/useDegradedBridgeQuery.ts
```

The hook should provide:

- retry state
- timeout classification
- exponential or fixed backoff support
- preservation of last successful rows
- banner state
- optional `isExpectedSlow` flag for background analysis

Backoff for Slice 1:

```text
1s / 3s / 5s, then stop automatic retries
```

Manual refresh can retry after that.

### ShellFileDock

Target file:

```text
web/src/features/shell/ShellFileDock.tsx
```

Behavior:

- timeout does **not** wipe loaded rows
- partial rows remain visible
- auto-retry up to 3 attempts
- show degraded banner instead of hard error
- when `pipelineBusy` or `deepAnalysisStatus === "running"`, treat slow reads as expected degraded loading

Banner copy:

```text
백그라운드 분석 중 — 목록 일부만 표시됨
```

Secondary copy:

```text
계속 불러오는 중입니다. 이미 불러온 항목은 유지됩니다.
```

### Resolve grid

Target file:

```text
web/src/features/work/resolve/ResolveAndOrganizeWorkspace.tsx
```

Behavior:

- remove eager `loadAllFiltered` on mount for large libraries
- threshold: `totalFiltered > 500` means page-at-a-time only
- `totalFiltered <= 500` may keep current load-all behavior
- existing infinite-scroll `loadPage` remains the default path for large data
- timeout preserves loaded rows and shows degraded banner
- when `!deepAnalysisComplete`, banner should explain that analysis is still running

Banner copy:

```text
백그라운드 분석 중 — 검토 목록 일부만 표시됨
```

Secondary copy:

```text
분석이 끝나면 near/relation 결과가 더 채워질 수 있습니다.
```

### Empty-state rule

A timeout must not cause an empty-table state when rows were previously loaded. Empty state is allowed only when the successful result set is actually empty.

## 6. Surgical query fix — minimal C in Slice 1

### Known root cause

`query_file_rows` already bypasses `LibrarySession._lock` and reads SQLite directly. Timeout there is more likely SQLite write contention or single Python/pywebview execution pressure.

`query_review_rows` currently reads in-memory cache under `LibrarySession._lock`. Post-scan relation and near phases hold the same lock across long work. This can block Resolve grid reads.

### Slice 1 backend changes

#### 1. Shrink relation/near lock scope

Refactor relation and near phases so expensive computation happens outside `_lock` where safe. Acquire `_lock` only to publish/apply results to shared session state.

Pattern:

```text
collect immutable inputs under short lock
compute relation/near results outside lock
publish result cache/projection under short lock
```

Do not change the near/relation algorithm in Slice 1.

#### 2. Early review projection sync

After exact index completes, before relation/near background phases, sync review projection once:

```text
_sync_file_review_projection()
```

Goal: make exact duplicate/review information queryable sooner and unblock FileDock duplicate-group sort earlier.

#### 3. Defer full `query_review_rows` SQLite read path

Do not move `query_review_rows` fully to SQLite in Slice 1. That is a larger contract and test expansion and belongs in Slice 2 unless timing data shows it is mandatory.

#### 4. Verify SQLite contention settings

Confirm `SqliteLibraryIndex` enables WAL and an appropriate `busy_timeout` pragma. If missing, add them in Slice 1.

Suggested baseline:

```sql
PRAGMA journal_mode=WAL;
PRAGMA busy_timeout=5000;
```

Exact value may be adjusted after timing data.

## 7. Out of scope — Slice 1

Do not include:

- IA refactor
- wizard vs work-hub decision
- `LibrarySession` split into `ScanSession` / `ReviewSession` / `QualitySession` / `ApplySession`
- scan 100% UX phase redesign
- near/relation algorithm changes
- snapshot diagnostics schema

### Slice 2 preview

Slice 2 should handle scan phase state clarity:

- scan read complete
- persist running
- index ready
- background deep analysis running
- deep analysis complete
- UI gates based on `indexReady` vs `deepAnalysisComplete`

### Slice 3 preview

Slice 3 may split `LibrarySession`, but only where Slice 1 timing spans prove a boundary is needed.

## 8. Verification

### Commands

```bash
python scripts/generate_large_library_fixture.py
python scripts/large_library_loading_smoke.py
pytest tests/test_bridge_contract.py -k "file_rows or review_rows" -v
cd web && npm run lint
cd web && npm run test:contracts
```

### Smoke assertions

| Assertion | Target |
|-----------|--------|
| `query_file_rows` p95 | < 5s after `indexReady` |
| `query_review_rows` first page | < 10s after `indexReady` |
| user-facing timeout errors | 0 in scripted UI-equivalent sequence |
| degraded banner | appears when timeout/retry path is exercised |
| partial rows | preserved across timeout/retry |

### Operator checklist

Run against:

```text
F:\kiwi\text\소설\정리
```

Checklist:

- scan starts and reports progress
- after `indexReady`, ShellFileDock shows first page or degraded banner within 30s
- Resolve grid shows first page within 30s without full preload
- no bare bridge timeout alert is visible to user
- partial rows remain visible during retries
- logs include bridge timing, lock timing, SQLite timing, and post-scan phase transitions

## Implementation sequencing

### Task 1 — Repro and smoke shell

- Add fixture generator.
- Add manifest.
- Add smoke script with `--folder` override.
- Smoke may initially measure current failures and mark expected fail until implementation tasks land.

### Task 2 — Timing spans

- Add `bridge_timing.py`.
- Instrument bridge entry/exit.
- Instrument lock wait and holder phase.
- Instrument SQLite query paths.
- Instrument post-scan phase transitions.

### Task 3 — Timeout table

- Add `bridgeTimeouts.ts`.
- Route `callBridge` timeout selection through method-specific table.
- Preserve existing error semantics for non-timeout failures.

### Task 4 — Degraded UI for ShellFileDock

- Keep previous rows on timeout.
- Add retry/backoff.
- Add degraded banner.
- Ensure empty state is not shown after timeout when rows exist.

### Task 5 — Degraded UI for Resolve

- Remove large-library eager `loadAllFiltered` on mount.
- Use threshold `totalFiltered > 500` for page-at-a-time mode.
- Add degraded banner and partial-row preservation.

### Task 6 — Minimal backend relief

- Shrink relation/near lock scope.
- Add early projection sync after exact index.
- Verify/add SQLite WAL and `busy_timeout`.

### Task 7 — Contract and regression checks

- Update bridge contract tests around file/review row queries.
- Add smoke docs.
- Record operator sign-off result in release smoke record when available.

## Acceptance

Slice 1 is accepted when:

1. Synthetic 7k smoke exits 0.
2. Scripted UI-equivalent sequence reports zero hard timeout errors.
3. ShellFileDock and Resolve preserve partial rows across timeout/retry.
4. Timing logs identify bridge elapsed time, lock wait, SQLite query duration, and post-scan phase transitions.
5. No IA refactor or `LibrarySession` split was introduced.

## Final locked recommendation

```text
Slice 1 = A(instrument) + B(timeouts + degraded UI) + C(lock shrink + early projection)
Repro   = C(both synthetic CI + operator manual)
```
