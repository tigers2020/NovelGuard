# Workflow Pipeline UI Rev. 3.3 Stabilization Implementation Plan

> **Status:** **approved** (2026-05-22) — implementation landed; Task 3 manual smoke pending human
> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Confirm rev. 3.3 “step-only execution” is consistent across code, tests, and docs—without adding new UI (no side panel, no layout expansion).

**Architecture:** WorkTab owns step navigation; WizardFooter is the sole Primary execution surface; WorkCompactBar owns folder path + rescan; section bodies are display + Secondary actions only. Auto-pipeline services remain in `gui/services/` for unit tests but are not wired from WorkTab.

**Tech Stack:** Python 3.12, PySide6, pytest, ruff, mypy, black.

**Spec:** [../specs/2026-05-22-workflow-pipeline-ui-design.md](../specs/2026-05-22-workflow-pipeline-ui-design.md) §8 Rev. 3.3

**Baseline (2026-05-22):** Dead views removed (`work_context_bar`, `pipeline_run_confirm_sheet`, `step_card`, `work_section`). Footer step execution landed. `tests/gui/views/` 9 passed (pre-regression pack).

---

## Scope

### In scope

- Audit checklist (7 areas below)
- Regression tests in `tests/gui/views/test_work_tab_rev33_regression.py`
- Dead-code boundary comments on retained services
- Full verification gate
- Doc index update (`docs/superpowers/README.md`)

### Out of scope (rev. 3.4+)

- Right side panel (checklist, log preview)
- CompactBar metric cards / icon buttons visual polish (HTML mockup)
- `WorkPageHeader` (“작업 파이프라인” title row)
- Re-enabling `WorkPipelineRunner` from WorkTab
- New widgets or layout expansion

---

## Acceptance checklist

| # | Area | Requirement | Verify |
|---|------|-------------|--------|
| 1 | WorkTab | No `pipeline_run_confirm_sheet` import/use | Source grep + `test_work_tab_does_not_import_confirm_sheet` |
| 2 | WorkTab | No `전체 작업 실행` CTA | `test_work_tab_has_no_run_all_pipeline_cta` |
| 3 | WorkTab | Single execution path: `execute_step_requested` | `work_tab._on_execute_step` only; no `WorkPipelineRunner` in `work_tab.py` |
| 4 | WorkTab | Running: Primary hidden, `중지` only | `test_footer_hides_primary_while_running` + manual |
| 5 | WizardFooter | Dynamic Primary label per step | `test_footer_primary_label_follows_step` |
| 6 | WizardFooter | Disabled when folder missing / step locked | `_footer_execute_state()` |
| 7 | WizardFooter | Prev / Next / Execute / Cancel roles separated | Code review `wizard_footer.py` |
| 8 | LibrarySection | No folder `QLineEdit`, no folder/scan/stop buttons | `test_library_section_has_no_folder_or_scan_buttons` |
| 9 | LibrarySection | Progress + preview hint only | Visual / `library_section.py` |
| 10 | DuplicateSection | No Primary row; Dry Run Secondary only | Grep: no `btnPrimary` in section |
| 11 | MoveSection | No folder field, no run Primary; Dry Run Secondary | Grep + code review |
| 12 | FinalizeSection | No apply Primary; tools disabled Secondary | Code review |
| 13 | CompactBar | Single folder display + `폴더 변경` / `재스캔` only | `work_compact_bar.py` |
| 14 | Dead code | `WorkPipelineRunner` / `pipeline_run_preview` not imported by WorkTab | Source grep + module docstrings |
| 15 | Tests | View suite green + regression pack | `pytest tests/gui/views/ -v` |

---

## Audit snapshot (2026-05-22)

| Item | Status | Notes |
|------|--------|-------|
| WorkTab confirm sheet | **PASS** | Removed |
| WorkTab run-all CTA | **PASS** | Not in widget tree |
| WorkTab `WorkPipelineRunner` | **PASS** | Not imported; `bind_main_window` no-op |
| Footer step execution | **PASS** | `execute_step_requested` |
| LibrarySection buttons | **PASS** | No scan/folder buttons; label “전체 스캔” on progress title only (copy, not CTA) |
| Section Primary buttons | **PASS** | Only `btnPrimary` on Footer execute |
| CompactBar | **PASS** | Folder + rescan only |
| Runner/preview wiring | **PASS** | Services retained for `tests/gui/services/test_work_pipeline_runner*.py` |

### Known non-issues

- `LibrarySection` progress title text `전체 스캔` — status label, not a button.
- `library_section.select_folder` dialog title `스캔할 폴더 선택` — QFileDialog, invoked from CompactBar only.
- `work_pipeline_runner` log string `전체 스캔 시작…` — service layer only, not UI.

---

## File map

| Path | Action | Responsibility |
|------|--------|----------------|
| `src/gui/views/work/work_tab.py` | Verify | Step footer orchestration, no auto-pipeline UI |
| `src/gui/views/work/wizard_footer.py` | Verify | Step CTA + cancel + summary |
| `src/gui/views/work/work_compact_bar.py` | Verify | Folder + metrics |
| `src/gui/views/work/sections/library_section.py` | Verify | Slim scan body |
| `src/gui/views/work/sections/duplicate_section.py` | Verify | Dry Run + tables; footer hooks |
| `src/gui/views/work/sections/move_section.py` | Verify | Options + Dry Run |
| `src/gui/views/work/sections/finalize_section.py` | Verify | Status only |
| `src/gui/services/work_pipeline_runner.py` | Doc | Future-reserved; not WorkTab-wired |
| `src/gui/services/pipeline_run_preview.py` | Doc | Future-reserved; not WorkTab-wired |
| `tests/gui/views/test_work_tab_rev33_regression.py` | **Create** | Regression pack |
| `docs/superpowers/README.md` | Modify | Index rev. 3.3 plan + spec note |

### Deleted (do not restore)

- `src/gui/views/work/work_context_bar.py`
- `src/gui/views/work/pipeline_run_confirm_sheet.py`
- `src/gui/views/work/step_card.py`
- `src/gui/views/work/work_section.py`

---

## Task 1: Regression test pack

**Files:**
- Create: `tests/gui/views/test_work_tab_rev33_regression.py`

- [x] **Step 1:** Add tests (a)–(d) per spec §8
- [x] **Step 2:** `pytest tests/gui/views/ -v` → 14 passed
- [ ] **Step 3:** Commit `[gui] rev 3.3 view regression tests` (when user requests commit)

---

## Task 2: Dead-code boundary documentation

**Files:**
- Modify: `src/gui/services/work_pipeline_runner.py` (module docstring)
- Modify: `src/gui/services/pipeline_run_preview.py` (module docstring)

- [x] **Step 1:** State “not wired from WorkTab since rev. 3.3; kept for service unit tests”
- [ ] **Step 2:** Commit `[gui] document pipeline runner reserve boundary`

---

## Task 3: Manual smoke (Work tab)

- [ ] Open app → **작업** tab
- [ ] CompactBar: folder change / rescan only; no second path field in scan step
- [ ] Footer: `스캔 실행` on step 1; no `전체 작업 실행`
- [ ] Start scan → Primary hides, `중지` visible
- [ ] After scan → step 2 label `중복 탐지`; duplicate body has Dry Run only
- [ ] Prev/Next navigate enabled steps only

---

## Task 4: Full verification gate

**Commands:**

```bash
pytest tests/gui/views/ -v
python scripts/verify_phase_completion.py
```

**Expected:**

- `tests/gui/views/`: 14 passed (9 existing + 5 regression)
- `verify_phase_completion.py`: pytest → ruff → mypy → black all exit 0

- [x] **Step 1:** `pytest` 177 passed; `verify_phase_completion.py` all 4 steps PASS (2026-05-22)
- [x] **Step 2:** black fix on `move_section.py` (trailing whitespace from `_on_run` removal)

---

## Task 5: Doc index

**Files:**
- Modify: `docs/superpowers/README.md`

- [x] Update workflow-pipeline spec line to cite **rev. 3.3** step-only
- [x] Add plan link: `2026-05-22-workflow-pipeline-ui-rev33-stabilization.md`

---

## Deferred to rev. 3.4

| Item | Rationale |
|------|-----------|
| `WorkSidePanel` (checklist + log preview) | New information architecture; needs mockup + spec slice |
| CompactBar metric card layout / icon buttons | Visual polish after behavior stable |
| `WorkPageHeader` caption row | Optional chrome |
| Optional reintroduction of “run all” as Secondary ghost | Product decision; currently excluded by §8 A |
| Remove or archive `WorkPipelineRunner` | Only after explicit product drop of auto-pipeline |

---

## Completion report (2026-05-22)

```
Changed:
  src/gui/views/work/* (work_tab, wizard_footer, sections/*)
  deleted: work_context_bar, pipeline_run_confirm_sheet, step_card, work_section
  tests/gui/views/test_work_tab_rev33_regression.py (new)
  docs/superpowers/specs/...-workflow-pipeline-ui-design.md §8
  docs/superpowers/README.md
  src/gui/services/work_pipeline_runner.py, pipeline_run_preview.py (docstrings)

pytest tests/gui/views/ -v: 14 passed
verify_phase_completion.py: 4/4 PASS (pytest 177, ruff, mypy, black)

Risks: Task 3 manual smoke not run in CI
Next: human smoke → commit → rev 3.4 side panel brainstorming
```

---

## Post-approval execution

| Task | State | Owner |
|------|-------|-------|
| 1 Regression tests | Done | — |
| 2 Dead-code docs | Done | — |
| 3 Manual smoke | **Pending** | Human (run `python src/main.py`, checklist in Task 3) |
| 4 Verification gate | Done | — |
| 5 Doc index | Done | — |
| Git commit | **Pending** | On request |
