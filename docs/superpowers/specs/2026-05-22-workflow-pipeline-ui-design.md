# Workflow Pipeline UI (Work Screen Rev. 3)

> Status: **approved** (rev. 3.3 unified step-only UI 2026-05-22; rev. 3.2 wizard shell; supersedes rev. 3.0–3.1 layout/dialog details below)
> Prerequisite: [2026-05-22-ui-work-hub-ia-design.md](2026-05-22-ui-work-hub-ia-design.md) Phase 1–8 complete + verification green
> Related: [2026-05-22-design-md-ui-rebrand-design.md](2026-05-22-design-md-ui-rebrand-design.md) (tokens, button QSS)
> UX source: Desktop UI/UX review (2026-05-22) — information hierarchy and step pipeline

## Problem

After Work Hub IA (rev. 2), the app still reads as **“debug panel + table”** rather than a guided cleanup workflow:

- Header stats and work-area metrics compete; folder context feels detached from numbers.
- Collapsible sections (`library`, `duplicate`, `move`, `quality`) look like parallel panels, not ordered steps.
- Progress bars dominate cards; the file table is visually under-weighted at the bottom.
- Buttons share similar visual weight — risk (stop, apply) is not obvious.
- Quality/integrity lives in a collapsed placeholder section, disconnected from **apply**.

## Goals

1. **Step pipeline UI:** four vertical **StepCards** — `scan` → `duplicate` → `move` → `finalize` — with clear `locked | ready | running | done | blocked` states.
2. **WorkContextBar:** folder path + four metrics + folder/rescan actions in the **work body** (not header corner chips).
3. **Layout split:** work pipeline ~**38%**, `FileListTable` ~**62%** via `QSplitter` (persist ratio in `QSettings` optional).
4. **Finalize bundles apply + integrity:** on **successful apply**, **auto-start** integrity check in the same card (no separate quality section).
5. **Progress de-emphasis:** bar max **70%** card width; primary copy is counts (files, size, errors).
6. **Button semantics:** `btnPrimary` / `btnSecondary` / `btnDanger` / `btnNeutral` per action table.
7. **File table status chips:** canonical, duplicate suspect, move pending (when plan exists), integrity attention.
8. Preserve **dry-run + user approval**, bottom global file list, global Undo/Redo toolbar, 3-item sidebar.
9. **One-button auto pipeline:** `[전체 작업 실행]` runs scan → duplicate → move → finalize in order; **active StepCard scrolls into view**, sidebar stays on **작업**; **global pipeline progress** shows overall + current step (rev. 3.1).

## Non-goals

- Implementing integrity / encoding / small-file **use cases** in this spec (UI hooks only here; **integrity + UTF-8** → [2026-05-22-integrity-check-design.md](2026-05-22-integrity-check-design.md); small-file deferred).
- Changing duplicate-detection, keeper policy, or move business rules.
- Sidebar icon polish, separate log tab, file preview pane, duplicate side-by-side compare view.
- Replacing DESIGN.md color system with ad-hoc hex; rebrand tokens remain normative.
- Undo/redo engine implementation (toolbar shell unchanged).

## User decisions (brainstorming 2026-05-22)

| Topic | Choice |
|-------|--------|
| Timing | **A** — after Work Hub IA migration completes (separate spec/plan) |
| Layout approach | **1 — Vertical StepCard + Splitter** (recommended) |
| Step count | **4** — scan, duplicate, move, finalize |
| Integrity placement | Inside **finalize**; not a 5th step or standalone quality panel |
| Integrity trigger | **A** — auto-start immediately after successful apply |
| Color tokens | **DESIGN.md / rebrand spec** over review palette |
| Auto pipeline | **One button** — sequential run + step focus + overall progress |
| Work area layout (rev. 3.2) | **A** — wizard uses full WorkTab height; file table not fixed at 62% of app |
| File table (rev. 3.2) | **C** — collapsible bottom dock inside WorkTab; **collapsed by default** |
| Dialog policy (rev. 3.2) | **A** — **one consolidated approval** before auto-run; **no modal chain** during run |

---

## §7 Rev. 3.2 — Wizard shell, collapsible file dock, dialog policy (approved)

> **Supersedes** for implementation: §1 MainWindow 38/62 splitter, §1 ContextBar full-width `[전체 작업 실행]`, §2 StepCard vertical stack, §5 R2 38/62, auto-pipeline § DryRunPreviewDialog / per-step `QMessageBox` gates (rows 3–4, 6 in rev. 3.1 sequence).

### Problem (rev. 3.2)

- Horizontal stepper exists but **file table still consumes most of the window** when placed in `MainWindow` splitter (38/62).
- **`[전체 작업 실행]`** as a full-width top button competes with the stepper (not installation-wizard rhythm).
- **Auto-run shows 3+ modals** (`DryRunPreviewDialog`, duplicate apply, move confirm) — flow feels interrupted.

### Layout: Wizard Shell + collapsible dock (A + C)

**`MainWindow`:** `content_stack` only (work | logs | settings) — **no** `FileListTable` at MainWindow level.

**`WorkTab`:** single vertical `QSplitter`:

```text
┌─ WorkTab ─────────────────────────────────────┐
│ [CompactBar: folder + 4 metrics + folder actions]│
│ [PipelineStepper — ① 스캔 — ② 중복 — ③ 이동 — ④ 적용] │
│ ┌─ QStackedWidget (stretch) ─────────────────┐ │
│ │  current step body only                     │ │
│ └─────────────────────────────────────────────┘ │
│ [WizardFooter: ◀ 이전 | 다음 ▶ | 전체 실행 | 중지] │
│ [progress label + thin bar]                      │
├─ ▲ 파일 목록 (collapsible dock) ────────────────┤
│  FileListTableWidget — default collapsed (~48px) │
└────────────────────────────────────────────────┘
```

| Element | Rule |
|---------|------|
| Wizard pane | Default **~88–92%** height; stretch priority |
| File dock | Default **collapsed**; header `▼ 파일 목록 (N)` toggles expand; draggable splitter |
| Persistence | `QSettings` keys `ui/work_wizard_splitter`, `ui/work_file_dock_expanded` |
| Scan step hint | Optional link: `파일 목록 펼치기` after scan completes (expands dock, no modal) |

**Remove:** `WorkContextBar` pipeline row with full-width Primary (moved to footer).

### Wizard footer (normative)

| Control | Class | Behavior |
|---------|-------|----------|
| `이전` | Secondary | Previous step if not `locked` |
| `다음` | Secondary | Next step if `ready`/`done` path allows |
| `전체 작업 실행` | Primary | Opens **run confirm** (below); disabled while running |
| `중지` | Danger | Visible while pipeline `running` |
| Progress | — | `2/4 중복 정리 — …` + `pipelineProgress` (footer, not top) |

### Dialog policy: one-shot approval (A)

**Before** `WorkPipelineRunner.start()` after user clicks `전체 작업 실행`:

Show **`PipelineRunConfirmSheet`** (inline panel or single non-blocking sheet — **not** a chain of modals):

| Block | Content |
|-------|---------|
| Summary | Folder path; estimated file count (from preview/store); duplicate groups if known; **duplicate move count**; **organize move/copy count** (from dry-run compute, sync) |
| Checkbox | `파괴적 작업(이동·삭제)의 결과를 확인했으며 실행합니다` (required) |
| Actions | `[시작]` Primary / `[취소]` Secondary |

**During auto-run (after [시작]):**

| Forbidden | Allowed |
|-----------|---------|
| `DryRunPreviewDialog` | Inline text in duplicate/move step body (“128건 → duplicate/”) |
| `QMessageBox.question` for apply/move | Footer progress + step body status |
| `QMessageBox.information` for empty ops | Footer `detail_message` or `formHint` in step |

| Still allowed | When |
|---------------|------|
| Error modals | Scan/duplicate/move hard failure |
| Manual **Dry Run** button | User-initiated → `DryRunPreviewDialog` OK |
| Manual **적용하기** | Short confirm OK (optional inline in rev. 3.2+) |

**Runner sequence (rev. 3.2 happy path):**

1. User passes `PipelineRunConfirmSheet` → runner `start()`.
2. Scan → duplicate detect → **apply duplicate moves without dialog** (pre-approved).
3. Move dry-run result → **execute without dialog** (pre-approved).
4. Finalize apply → integrity auto.

If pre-flight dry-run compute fails: show error in confirm sheet; do not start runner.

### Components (rev. 3.2 additions)

| Path | Responsibility |
|------|----------------|
| `gui/views/work/wizard_footer.py` | **Create** — prev/next/run/stop/progress |
| `gui/views/work/pipeline_run_confirm_sheet.py` | **Create** — one-shot summary + checkbox |
| `gui/views/work/pipeline_stepper.py` | **Keep** — horizontal step rail |
| `gui/views/work/work_tab.py` | **Modify** — internal splitter + dock; footer; no top run button |
| `gui/views/main_window.py` | **Modify** — move `FileListTable` into WorkTab; remove center 38/62 |
| `gui/services/work_pipeline_runner.py` | **Modify** — `auto_run=True` skips modal gates |

### Migration phases (rev. 3.2 — after rev. 3.1 code landed)

| Phase | Deliverable |
|-------|-------------|
| W1 | `FileListTable` reparent to WorkTab dock; remove MainWindow splitter |
| W2 | `WizardFooter`; compact bar; stepper + stack layout |
| W3 | `PipelineRunConfirmSheet` + runner `auto_run` path (no mid-run modals) |
| W4 | Dock collapse/expand + settings persistence |
| W5 | Tests + manual checklist + `verify_phase_completion.py` |

### Manual checklist (rev. 3.2)

- [ ] Work tab: step body uses **most of the height**; file table **collapsed** by default.
- [ ] `전체 작업 실행` is in **footer**, not full-width under metrics.
- [ ] Auto-run: **one** confirm sheet at start; **no** Dry Run dialog mid-run.
- [ ] Manual Dry Run still opens preview dialog.
- [ ] Dock expands to show file list; splitter remembers size.

### Architecture (rev. 3.2)

```text
[ Header + GlobalActionToolbar ]
┌────────┬──────────────────────────────────┐
│ Sidebar│ WorkTab                          │
│        │  CompactBar | Stepper | Stack    │
│        │  WizardFooter                    │
│        │  ── collapsible FileListTable ── │
└────────┴──────────────────────────────────┘
```

---

## §1 Shell & information hierarchy (rev. 3.0 — partial supersede by §7)

> **Note:** §7 rev. 3.2 replaces MainWindow layout and ContextBar pipeline row described here.

### Header (slim)

- **Keep:** `NovelGuard` title + subtitle `텍스트 소설 파일 정리 · 중복 탐지 · 안전 이동`.
- **Remove:** four stat chips (moved to `WorkContextBar`).
- **Keep:** `GlobalActionToolbar` directly under header (unchanged from rev. 2).

### WorkContextBar (new)

Placed at top of `WorkTab` (above step cards).

| Element | Content |
|---------|---------|
| Folder row | `대상 폴더: {path}` + `[폴더 변경]` `btnNeutral` + `[재스캔]` `btnSecondary` |
| Metrics row | `[파일 N]` `[총 용량 X GB]` `[중복 그룹 N]` `[이슈 N]` |
| Pipeline row | `[전체 작업 실행]` `btnPrimary` + `[중지]` `btnDanger` (visible while running) + **global** `QProgressBar` (100% width of bar row) + label `2/4 중복 정리 — 1,240/7,491 파일` |
| Data source | `compute_work_stats(file_data_store)` + `AppState.scan_folder` (same as rev. 2 header helper) |

`MainWindow` updates context bar on store/job signals (same hooks as header today).

### MainWindow center layout

Replace `center_layout` stretch `2:1` (stack vs table) with:

```text
QSplitter (vertical)
  ├─ WorkTab          (initial stretch ~38, min height ~280px)
  └─ FileListTable    (initial stretch ~62, min height ~200px)
```

- Optional: `QSettings` key `ui/work_splitter_ratio` (float 0.35–0.45).
- Sidebar + stack (`work | logs | settings`) unchanged.

### Progress bar rules (all steps)

- `QProgressBar` max width = **70%** of card content width (`maximumWidth` or layout stretch).
- Primary line: human summary (e.g. `7,491개 파일 · 33.8 GB · 0개 오류`).
- Bar is secondary visual; hide when idle.

---

## §2 Step pipeline & state machine

### StepCard component (new)

| Property | Description |
|----------|-------------|
| `step_id` | `scan` \| `duplicate` \| `move` \| `finalize` |
| `title` | Korean label (see table) |
| `state` | `locked` \| `ready` \| `running` \| `done` \| `blocked` |
| `body` | Existing section widget content (ported from rev. 2 sections) |

Visual: numbered badge `1–4`, state pill (대기 / 준비 / 진행중 / 완료 / 차단), `objectName` `stepCard`, `stepCard--{state}` for QSS.

**Remove in rev. 3:** `WorkSection` chevron collapse, `SummaryStrip` jump buttons, standalone `quality` section.

### Steps

| # | ID | Title | Body source (rev. 2) | Unlock when |
|---|-----|-------|------------------------|-------------|
| 1 | `scan` | 스캔 | `LibrarySection` | always `ready` |
| 2 | `duplicate` | 중복 정리 | `DuplicateSection` + groups/evidence | `scan` → `done` |
| 3 | `move` | 이동 계획 | `MoveSection` | `duplicate` → `done` or `skipped`* |
| 4 | `finalize` | 적용 · 검증 | new `FinalizeSection` | `move` → `done` or `skipped`* |

\*`skipped`: user completed scan with zero groups and chose to proceed to move (explicit “건너뛰기” or auto when duplicate groups = 0 and move not required — product default: **auto-skip duplicate UI focus**, step 3 `ready` when scan done and groups = 0).

### Pipeline coordinator

New `WorkPipelineViewModel` (or extend `WorkViewModel`):

- Inputs: `AppState`, `FileDataStore`, job manager status, per-step VM flags.
- Output: `PipelineSnapshot` — per-step `state`, `finalize_substate`, active step highlight.
- **No business logic** in GUI beyond gating enablement; use cases unchanged.

### Finalize sub-state machine

```text
idle
  → applying          (user: 적용하기, Primary)
  → apply_done        (success)
  → integrity_running (auto-enqueue integrity job)
  → integrity_done
  → apply_failed      (blocked; retry enabled)
```

| Substate | UI |
|----------|-----|
| `idle` | `[적용하기]` Primary enabled when move `done` |
| `applying` | Progress + disable destructive |
| `apply_done` | Success line; integrity auto-starts (no extra click) |
| `integrity_running` | “무결성 검사 중…” + progress |
| `integrity_done` | Summary: `적용 ✓ · 무결성 N건`; refresh context bar 이슈 |
| `apply_failed` | Error text; `[재시도]` Secondary |

**Integrity auto-run:**

- On `apply_done`, call integrity job port if registered; else set `integrity_done` with tooltip “무결성 검사 (미구현)” and log once.
- On apply failure/cancel: **do not** start integrity.

**Finalize secondary row (placeholders OK):**

- `[인코딩 분석]` `[UTF-8 변환]` — `btnSecondary`, disabled + “미구현” until use cases exist.
- Small-file notice: single `formHint` line (from rev. 2 quality copy).

### Action → button class (normative)

| Action | Class |
|--------|-------|
| 전체 스캔, 중복 탐지 시작, 적용하기, **전체 작업 실행** | Primary |
| Dry Run, 재스캔, 인코딩 분석 | Secondary |
| 스캔 중지, 실행 취소, **파이프라인 중지** | Danger |
| 폴더 선택, 폴더 변경 | Neutral |

### Auto pipeline orchestrator (rev. 3.1)

**Entry:** `WorkContextBar` → `[전체 작업 실행]`.

**Preconditions:** `AppState.scan_folder` set; no other pipeline run in progress.

**On start:**

1. `MainWindow._switch_tab("work")` (sidebar **작업** — never auto-switch to 로그/설정).
2. `WorkPipelineRunner.start()` — async state machine (GUI layer only; invokes existing VMs / section ports).

**Sequence (happy path):**

| Order | Step UI | Action | UI sync |
|-------|---------|--------|---------|
| 1 | `scan` | Full scan via `ScanViewModel.start_scan` | `set_active_step("scan")`, scroll into view; forward scan progress to global bar |
| 2 | `duplicate` | `DuplicateViewModel.start_duplicate_detection` | Active step → `duplicate`; on 0 groups → skip to move (step marked `skipped`) |
| 3 | `duplicate` | Dry-run preview (`DryRunPreviewDialog`) if operations > 0 | Runner **pauses** `awaiting_approval`; dialog modal; No → `blocked` + stop |
| 4 | `duplicate` | Apply duplicate moves (`QMessageBox.question`) | Pause until Yes; No → stop |
| 5 | `move` | Move dry-run (sync) | Active step → `move`; show result label |
| 6 | `move` | Move execute (`QMessageBox.question` before destructive run) | Pause until Yes |
| 7 | `finalize` | Apply (if separate from move) + integrity auto | Active step → `finalize`; integrity auto per §2 |

**Progress model:**

```python
@dataclass(frozen=True)
class PipelineRunProgress:
    run_id: str
    current_step_id: str      # scan | duplicate | move | finalize
    step_index: int           # 0..3
    step_label: str           # Korean
    detail_message: str
    overall_percent: int      # 0..100 (4 equal step buckets + intra-step from JobProgress)
    phase: Literal["running", "awaiting_approval", "completed", "failed", "cancelled"]
```

- Overall %: each step = 25% base; within step, map `JobProgress.processed/total` when total known, else indeterminate pulse on global bar.
- Step cards mirror runner: `running` step highlighted (`stepCard--active`); completed steps `done`.

**Cancel:** `[중지]` cancels current job (`ScanViewModel.cancel` / duplicate cancel) and sets runner `cancelled`; partial step states remain honest (`blocked` on current).

**Manual steps still work** while idle; when runner active, per-step Primary buttons disabled except Danger cancel.

**Runner location:** `gui/services/work_pipeline_runner.py` (QObject, signals). Sections expose thin `run_*_for_pipeline()` methods that return bool / emit `step_finished` — no duplicate business logic.

---

## §3 File table status chips

Extend table delegate (or dedicated `StatusChipDelegate`) on **상태** column (add column if missing; do not remove existing duplicate/integrity text columns in v1 — chips are additive or replace text in rev. 3 only).

| Chip label | Rule |
|------------|------|
| `대표 파일` | `is_canonical` |
| `중복 의심` | `duplicate_group_id` set and not canonical |
| `이동 예정` | move plan marks file (when DTO wired; else omit chip) |
| `검사 필요` | `integrity_severity` in (`WARN`, `ERROR`) |

QSS: reuse DESIGN.md `status-duplicate-*`, `status-integrity-*`; no inline hex.

Multiple chips per row allowed (priority: canonical > duplicate > move > integrity).

---

## §4 Components & file map

| Path | Responsibility |
|------|----------------|
| `gui/views/work/work_context_bar.py` | **Create** — folder + metrics + actions |
| `gui/views/work/step_card.py` | **Create** — numbered card + state pill |
| `gui/views/work/sections/finalize_section.py` | **Create** — apply + integrity auto UI |
| `gui/services/work_pipeline_runner.py` | **Create** — one-button sequential orchestrator |
| `gui/view_models/work_pipeline_view_model.py` | **Create** — pipeline gating + finalize substate + runner progress |
| `gui/view_models/work_pipeline_dto.py` | **Create** — `StepState`, `FinalizeSubstate`, `PipelineSnapshot`, `PipelineRunProgress` |
| `gui/views/work/work_tab.py` | **Modify** — StepCards, remove scroll+jump+quality |
| `gui/views/main_window.py` | **Modify** — splitter, context bar stats wiring |
| `gui/views/components/header.py` | **Modify** — remove stat chips |
| `gui/views/components/file_list_table.py` | **Modify** — status chips |
| `gui/styles/qss/buttons.py` (or theme) | **Modify** — `btnDanger`, `btnNeutral` |
| `tests/gui/view_models/test_work_pipeline_view_model.py` | **Create** |
| `tests/gui/views/test_work_context_bar.py` | **Create** |
| **Delete** | `summary_strip.py`, `quality_section.py` (after finalize absorbs copy) |

Rev. 2 section internals (`library_section`, `duplicate_section`, `move_section`) are **rehosted** inside StepCards with minimal logic change.

---

## §5 Migration phases (rev. 3 only)

| Phase | Deliverable |
|-------|-------------|
| R1 | Slim header; `WorkContextBar`; stats wiring moved off header |
| R2 | `QSplitter` 38/62; remove old stretch ratio |
| R3 | `StepCard` + `WorkPipelineViewModel`; port scan/duplicate/move bodies |
| R4 | `FinalizeSection` + apply→integrity auto hook (or honest no-op) |
| R5 | Progress width cap; `btnDanger` / `btnNeutral` QSS |
| R6 | File table status chips; delete `summary_strip`, `quality_section` |
| R7 | `WorkPipelineRunner` + context bar global progress + step auto-scroll |
| R8 | Tests + manual checklist + `verify_phase_completion.py` |

**Gate:** Do not start R1 until [ui-work-hub-ia plan](../plans/2026-05-22-ui-work-hub-ia.md) manual checklist is complete.

---

## §6 Verification & success criteria

### Tests

| Area | Test |
|------|------|
| `WorkPipelineViewModel` | Step locks until scan done; finalize substate transitions on mocked apply success |
| `WorkPipelineRunner` | Mock VMs: scan→duplicate→move order; pauses on approval gate; cancel stops at current job |
| `WorkContextBar` | Updates metrics when store batch changes |
| `FinalizeSection` | Auto integrity trigger called once after apply success (mock port) |
| Regression | `verify_phase_completion.py` |

### Manual checklist

- [ ] Header shows title + subtitle only (no stat chips).
- [ ] Context bar shows folder + four metrics; matches former header values.
- [ ] Steps 1–4 read as ordered pipeline; step 4 runs integrity automatically after successful apply.
- [ ] No standalone “품질 점검” section or summary jump row.
- [ ] File table occupies ~60%+ of center column; splitter draggable.
- [ ] Primary vs Danger buttons visually distinct on scan stop and apply.
- [ ] Status chips visible on representative rows after duplicate/integrity data present.
- [ ] **Rev. 3.2:** One confirm sheet before auto-run; no mid-run modal chain (§7).
- [ ] **Rev. 3.2:** Wizard full height; file dock collapsed by default (§7).
- [ ] `[전체 작업 실행]` keeps sidebar on **작업**, updates step stack + footer progress through all 4 steps.
- [ ] Manual Dry Run / manual apply may still use dialogs; auto-run does not.

### Risks

| Risk | Mitigation |
|------|------------|
| Duplicate table cramped in card | Card body min height 240px; internal scroll |
| Integrity port missing | Auto-run no-op + tooltip; no fake success counts |
| Double migration churn | Strict prerequisite gate on rev. 2 completion |

### Success criteria

- User can describe workflow as **스캔 → 중복 → 이동 → 적용·검증** without opening collapsed panels.
- **Rev. 3.2:** Wizard pane is the dominant visual anchor; file table is optional via dock.
- Integrity is never a forgotten fifth panel; it follows apply in step 4.
- Verification gate green.

---

## Architecture diagram

```text
[ Header — brand only ]
[ GlobalActionToolbar ]
┌────────┬─────────────────────────────────────────────┐
│ Sidebar│ QSplitter                                   │
│        │  ┌ WorkTab ─────────────────────────────┐  │
│        │  │ WorkContextBar (folder + 4 metrics)   │  │
│        │  │ StepCard 1 scan    (LibrarySection) │  │
│        │  │ StepCard 2 duplicate                 │  │
│        │  │ StepCard 3 move                      │  │
│        │  │ StepCard 4 finalize (apply→integrity)│  │
│        │  └──────────────────────────────────────┘  │
│        │  ┌ FileListTable (+ status chips) ─────┐  │
│        │  └──────────────────────────────────────┘  │
└────────┴─────────────────────────────────────────────┘
```

## §8 Rev. 3.3 — Unified controls, step-only execution (approved 2026-05-22)

> **Supersedes** for Work UI: Goal #9 auto-pipeline, §7 `PipelineRunConfirmSheet`, §7 WizardFooter `전체 작업 실행`, duplicate `WorkContextBar` / `StepCard` / `WorkSection` widgets.

### User decisions

| Topic | Choice |
|-------|--------|
| Execution | **A** — `현재 단계 실행` only (no `전체 작업 실행` in UI) |
| Layout reference | User HTML mockup 2026-05-22 |
| Folder / rescan | **CompactBar only** (icon buttons) |
| Step primary actions | **WizardFooter only** |
| Auto pipeline UI | **Removed** (`PipelineRunConfirmSheet` deleted; `WorkPipelineRunner` not wired from WorkTab) |

### Deleted view modules

- `work_context_bar.py` (replaced by `work_compact_bar.py` + `wizard_footer.py`)
- `pipeline_run_confirm_sheet.py`
- `step_card.py` (replaced by `pipeline_stepper.py`)
- `work_section.py` (rev. 2 collapsible wrapper)

### Footer step actions

| Step | Primary label | Invokes |
|------|---------------|---------|
| scan | `스캔 실행` | `LibrarySection.request_full_scan()` |
| duplicate | `중복 탐지` → `적용하기` | detect → apply (confirm dialog) |
| move | `정리 실행` | `MoveSection.execute_organize()` |
| finalize | `적용·검증` | `FinalizeSection.run_apply_and_integrity_auto()` |

Running: hide Primary, show `중지` only. Secondary Dry Run stays in step body.

### Section bodies (slim)

- **LibrarySection:** preview status + progress panel only (no folder field, no scan buttons).
- **DuplicateSection:** Dry Run + tables (no detect/apply buttons).
- **MoveSection:** move/copy options + Dry Run (no folder field, no run button).
- **FinalizeSection:** status + hints (no apply button row).

---

## §9 Rev. 3.9 — Auto-only execution (approved 2026-05-22)

> **Supersedes** §8 Rev. 3.3 step-only execution. **Retains** §8 slim sections + CompactBar.

### User decisions

| Topic | Choice |
|-------|--------|
| Execution | **Auto-only** — `전체 작업 실행` replaces per-step footer Primary |
| Confirm | **One-shot** `PipelineRunConfirmSheet` before run (§7 policy) |
| During run | **Prev/Next enabled** — browse step bodies while runner active |
| During run | Primary hidden, **중지** only |
| Section bodies | **Unchanged** from §8 (no duplicate CTAs in bodies) |

### Footer

| Control | Behavior |
|---------|----------|
| `전체 작업 실행` | Primary; opens confirm sheet |
| `중지` | Visible while pipeline running |
| `이전` / `다음` | Enabled during run for step browse (does not drive runner) |
| Progress | `update_pipeline_progress` from `WorkPipelineRunner` |

### Restored components

- `pipeline_run_confirm_sheet.py`
- `WorkTab` ↔ `WorkPipelineRunner` (`auto_run=True`)
- `WizardFooter.run_pipeline_requested`

---

## References

- [2026-05-22-ui-work-hub-ia-design.md](2026-05-22-ui-work-hub-ia-design.md)
- [DESIGN.md](../../../DESIGN.md)
- [persona/gina-gui.md](../../../persona/gina-gui.md)
- `gui/views/work/work_tab.py`, `gui/services/work_stats.py`
