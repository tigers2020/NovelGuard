# Large-library scan smoke record (PR-48)

Use this template for **operator sign-off** on streaming scan ([spec 028](../superpowers/specs/028-2026-06-03-infra-scan-streaming-phases-design.md)).  
Not a substitute for packaging smoke — see [smoke-record-template.md](smoke-record-template.md).

Date:
Operator:
Machine:
Windows version:
Library folder path (~7k files, or staging copy):
Commit under test:

## Preconditions

- [ ] Build or dev host matches commit under test
- [ ] Folder is a **copy** or dedicated staging path (not production-only original unless approved)
- [ ] No other NovelGuard instance scanning the same folder
- [ ] WebView2 runtime available (packaged exe) or dev `npm run dev` + `python src/main.py`

## Checklist (028 / PR-46 operator criteria)

1. [ ] Select folder and start scan.
2. [ ] **ShellFileDock** shows increasing file count **before** scan section reaches full success (first batch ~400 files or sooner on small staging).
3. [ ] During persist / tail persist, pipeline label shows **`인덱스 저장`** (or `인덱스 저장 중…`) — **not** `스캔 중` at 100% progress.
4. [ ] Scan section reaches success; `deepAnalysisStatus` becomes `complete` **or** error banner is shown with actionable message.
5. [ ] Resolve tab loads duplicate groups after deep analysis completes (smoke sample: open one group).

## Slice 1 (NOV-36 / [NOV-42](https://linear.app/zkaufman/issue/NOV-42)) — degraded loading

Canonical operator path: `F:\kiwi\text\소설\정리` (machine-specific; never run in CI).  
Design reference: [spec 034 §8](../superpowers/specs/034-2026-06-05-infra-large-library-loading-stability-design.md).

1. [ ] Select `F:\kiwi\text\소설\정리` (or approved staging copy) and start scan.
2. [ ] **FileDock** first page within 30s of `indexReady` **or** degraded banner (`백그라운드 분석 중 — 목록 일부만 표시됨`); no hard timeout alert.
3. [ ] Open **Resolve**; first page within 30s; no full-preload stall when `totalFiltered > 500`.
4. [ ] Partial rows remain visible during bridge retry (no empty-table wipe on timeout).
5. [ ] UI shows **no bare** `BridgeCallError code=timeout` strings (banner only).
6. [ ] DEBUG logs contain `bridge_timing`, `lock_wait`, `sqlite_query`, `post_scan_phase` events.

Post checklist: record `## Operator sign-off` on [NOV-42](https://linear.app/zkaufman/issue/NOV-42) with PASS/FAIL and notes.

## Automated regression (developer / CI)

```bash
python scripts/generate_large_library_fixture.py
python scripts/large_library_loading_smoke.py
python scripts/verify_phase_completion.py
pytest tests/test_bridge_contract.py -q
cd web && npm run test -- src/bridge/bridgeParity.test.ts
```

## Result

PASS / FAIL:

Notes (timings, file count, anomalies):
