---
title: Large-library scan operator sign-off
status: approved
risk: safe
grill_me: 2026-06-03
approved: 2026-06-03
date: 2026-06-03
pr_label: PR-48
parent_spec: docs/superpowers/specs/028-2026-06-03-infra-scan-streaming-phases-design.md
plan: docs/superpowers/plans/048-2026-06-03-infra-scan-pr48-operator-signoff.md
roadmap: docs/superpowers/roadmap/007-2026-06-03-pr48-pr57-post-beta-roadmap.md
---

# 030 — Large-Library Scan Operator Sign-Off

## Scope sentence

Close the **operator and regression gate** for [028 streaming scan](028-2026-06-03-infra-scan-streaming-phases-design.md) on `main`: document 7k manual smoke, align web pipeline UX for `scan_persist`, extend contract tests, record `verify_phase_completion.py` on the plan. **No new scan algorithms, bridge methods, or Work IA changes.**

---

## 1. Problem

PR-46 ([046 plan](../plans/046-2026-06-03-infra-scan-streaming-phases.md)) landed streaming persist and snapshot flags. Remaining gaps:

| Gap | Impact |
|-----|--------|
| Manual 7k checklist in 046 plan Step 5 still open | Product sign-off blocked |
| `pipeline.phase=scan_persist` not in web foreground track set | Dual-track UI may show “idle” foreground during tail persist |
| `verify_phase_completion` not recorded on 046 verification log | Release gate evidence incomplete |
| No dedicated large-library smoke record template | Operators reuse packaging template incorrectly |

---

## 2. Grill-me resolutions (self, 2026-06-03)

| Question | Decision |
|----------|----------|
| Run real 7k scan in CI? | **No** — manual record only; fixture/contract tests in CI |
| New test file for web pipeline? | **No** — extend `bridgeParity.test.ts` only |
| Rename `scan_persist` → `persist` in Python? | **No** — keep wire value; fix web `FOREGROUND_PHASES` |
| Block PR-48 on operator filling F: drive path? | **No** — template + agent-filled **fixture-scale** automated proof; operator section blank |
| Update spec 028? | **No** — 030 is sign-off overlay only |

---

## 3. Design LOCKs

| ID | LOCK |
|----|------|
| **LOCK-SIGNOFF-1** | `scan_persist` is a **foreground** busy phase in `derivePipelineTracks` (same class as `persist`). |
| **LOCK-SIGNOFF-2** | `normalizePipelinePhase("scan")` → `probe` (unchanged). `pipelinePhaseLabel` uses bridge `pipeline.label` for `scan_persist`. |
| **LOCK-SIGNOFF-3** | Python must not emit `phase="scan"`. Contract test remains. |
| **LOCK-SIGNOFF-4** | Extend `test_bridge_contract.py` only — assert `scan_persist` appears during scan and label contains `인덱스 저장`. |
| **LOCK-SIGNOFF-5** | Add `docs/release/smoke-record-large-library.md` — 7k checklist separate from packaging smoke. |
| **LOCK-SIGNOFF-6** | Record `verify_phase_completion.py` PASS on plan 048 verification log. |

---

## 4. Deliverables

### 4.1 Documentation

- `docs/release/smoke-record-large-library.md` — operator checklist (7k criteria from 028 §11 / 046 Step 5).
- Update [007 roadmap](../roadmap/007-2026-06-03-pr48-pr57-post-beta-roadmap.md) PR-48 row → **Done** when plan complete.
- [current_query.md](../roadmap/current_query.md) → PR-49 after merge.

### 4.2 Web

- `web/src/features/work/pipelineTracks.ts`: include `scan_persist` in foreground busy phases.
- `web/src/bridge/bridgeParity.test.ts`: case for `scan_persist` + dual-track foreground busy.

### 4.3 Python

- `tests/test_bridge_contract.py`: `test_scan_observes_scan_persist_phase` (monkeypatch slow tail persist if needed).

### 4.4 Verification

```bash
python scripts/verify_phase_completion.py
pytest tests/test_bridge_contract.py -q
cd web && npm run test -- src/bridge/bridgeParity.test.ts
```

---

## 5. Out of scope

- PR-49 FileDock per-mode persistence  
- New bridge RPCs  
- Changing `SCAN_PERSIST_BATCH_SIZE` defaults  
- Packaged exe 7k run in CI  

---

## 6. Acceptance

- [x] Spec approved (2026-06-03)  
- [ ] Plan 048 verification log includes full gate PASS  
- [ ] Web foreground track busy during `scan_persist`  
- [ ] Large-library smoke template published  
- [ ] Roadmap 007 PR-48 marked Done  

---

## 7. Spec self-review

| Check | Result |
|-------|--------|
| Placeholders | None |
| Consistency with 028 | Sign-off only; no LOCK conflicts |
| Scope | Single PR; no decomposition |
| Ambiguity | Manual 7k optional for merge; automated tests required |
