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

## Automated regression (developer / CI)

```bash
python scripts/verify_phase_completion.py
pytest tests/test_bridge_contract.py -q
cd web && npm run test -- src/bridge/bridgeParity.test.ts
```

## Result

PASS / FAIL:

Notes (timings, file count, anomalies):
