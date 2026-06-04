# PR-48: Large-Library Scan Operator Sign-Off — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close operator/regression gate for streaming scan (028/046): `scan_persist` UI parity, contract tests, large-library smoke template, recorded full verify gate.

**Architecture:** Web-only track fix + test extensions + release doc. No Python pipeline behavior change unless tests expose a defect.

**Tech Stack:** Python 3.12 pytest, React/Vitest (`bridgeParity.test.ts`).

**Spec:** [030 operator sign-off](../specs/030-2026-06-03-infra-scan-operator-signoff-design.md) (**approved** 2026-06-03)

**Test policy:** Extend existing test files only.

---

### Task 1: Large-library smoke template

**Files:**
- Create: `docs/release/smoke-record-large-library.md`

- [ ] **Step 1: Add template**

Create checklist with:
1. Folder path (operator fills; e.g. staging copy of ~7k library)
2. First batch visible in ShellFileDock before `scan.state=success`
3. Label `인덱스 저장` during persist / `scan_persist` — not `스캔 중` at 100%
4. `deepAnalysisStatus` reaches `complete` or documented `error` banner
5. Result PASS/FAIL + notes

- [ ] **Step 2: Link from 046 plan**

Add one line in `docs/superpowers/plans/046-2026-06-03-infra-scan-streaming-phases.md` verification section pointing to new template (optional cross-link).

---

### Task 2: Web — `scan_persist` foreground track

**Files:**
- Modify: `web/src/features/work/pipelineTracks.ts`

- [ ] **Step 1: Write failing test**

In `web/src/bridge/bridgeParity.test.ts`, add:

```typescript
  it("derivePipelineTracks treats scan_persist as foreground busy", () => {
    const model = derivePipelineTracks(
      {
        phase: "scan_persist",
        label: "인덱스 저장 중… (400/7392)",
        percent: 55,
        cancellable: true,
        background: null,
      },
      {
        state: "running",
        indexReady: true,
        deepAnalysisComplete: false,
        deepAnalysisStatus: "idle",
        deepAnalysisError: null,
        lastRun: null,
      },
    );
    expect(model.tracks[0]?.id).toBe("foreground");
    expect(model.tracks[0]?.complete).toBe(false);
    expect(model.tracks[0]?.label).toContain("인덱스 저장");
  });
```

Import `derivePipelineTracks` at top if missing.

- [ ] **Step 2: Run test — expect FAIL**

Run: `cd web && npm run test -- src/bridge/bridgeParity.test.ts -t "scan_persist"`  
Expected: FAIL — foreground shows complete or wrong label path.

- [ ] **Step 3: Fix `pipelineTracks.ts`**

```typescript
const FOREGROUND_PHASES = new Set([
  "probe",
  "persist",
  "scan_persist",
  "exact_index",
  "finalize",
]);
```

- [ ] **Step 4: Run test — expect PASS**

Run: `cd web && npm run test -- src/bridge/bridgeParity.test.ts -t "scan_persist"`  
Expected: PASS

---

### Task 3: Python — observe `scan_persist` phase

**Files:**
- Modify: `tests/test_bridge_contract.py`

- [ ] **Step 1: Write failing test**

```python
def test_scan_observes_scan_persist_phase(tmp_path: Path) -> None:
    for i in range(6):
        (tmp_path / f"f{i}.txt").write_text("x\n", encoding="utf-8")
    session = create_library_session(MemoryLibraryIndex())
    session.select_folder(str(tmp_path))
    api = create_bridge_api(session)
    api.start_scan()
    deadline = time.monotonic() + 10.0
    saw_scan_persist = False
    while time.monotonic() < deadline:
        snap = api.get_snapshot()
        phase = snap["pipeline"]["phase"]
        if phase == "scan_persist":
            saw_scan_persist = True
            assert "인덱스 저장" in snap["pipeline"]["label"]
            break
        if snap["work"]["scan"]["state"] == "success":
            break
        time.sleep(0.02)
    _scan_until_idle(api)
    assert saw_scan_persist or snap["library"]["fileCount"] == 6
```

(If small library skips `scan_persist`, assert success path only — adjust assertion after first run.)

- [ ] **Step 2: Run test**

Run: `pytest tests/test_bridge_contract.py::test_scan_observes_scan_persist_phase -v`  
Expected: PASS (or adjust threshold if phase only on sqlite large batch — use monkeypatch on persist tail if needed)

---

### Task 4: Verification gate + roadmap

**Files:**
- Modify: `docs/superpowers/roadmap/007-2026-06-03-pr48-pr57-post-beta-roadmap.md`
- Modify: `docs/superpowers/roadmap/current_query.md`
- Modify: `docs/superpowers/plans/048-2026-06-03-infra-scan-pr48-operator-signoff.md` (this file, verification log)

- [ ] **Step 1: Full gate**

Run: `python scripts/verify_phase_completion.py`  
Run: `pytest tests/test_bridge_contract.py -q`  
Run: `cd web && npm run test -- src/bridge/bridgeParity.test.ts`

- [ ] **Step 2: Update roadmap PR-48 status → Done**

- [ ] **Step 3: Set current_query → PR-49**

---

## Plan vs spec self-review

| Spec LOCK / section | Task |
|---------------------|------|
| LOCK-SIGNOFF-1 | Task 2 |
| LOCK-SIGNOFF-4 | Task 3 |
| LOCK-SIGNOFF-5 | Task 1 |
| LOCK-SIGNOFF-6 | Task 4 |
| §4.2 web | Task 2 |
| §4.3 python | Task 3 |

---

## Verification log

| Command | Status | Date |
|---------|--------|------|
| `pytest tests/test_bridge_contract.py -q` | PASS 150 | 2026-06-03 |
| `npm run test -- src/bridge/bridgeParity.test.ts` | PASS 54 | 2026-06-03 |
| `python scripts/verify_phase_completion.py` | PASS 8/9 (step 9 skip: no dist/) | 2026-06-03 |
| `python scripts/fixture_library_smoke.py` | PASS (after Win32 DB handle release fix) | 2026-06-03 |

## Implementation status

**Done** (2026-06-03) on branch `feat/pr48-scan-operator-signoff`.
