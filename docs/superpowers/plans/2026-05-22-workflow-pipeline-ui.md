# Workflow Pipeline UI (Rev. 3) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform the Work screen into a **4-step pipeline** (scan → duplicate → move → finalize) with **one-button auto-run** that advances steps, keeps the sidebar on **작업**, scrolls the active step into view, and shows **global pipeline progress**—while preserving dry-run previews and destructive approval dialogs.

**Architecture:** Rev. 2 section widgets stay as step bodies inside new `StepCard`s. `WorkPipelineViewModel` owns step gating and finalize substate. `WorkPipelineRunner` (QObject) sequences existing `ScanViewModel` / `DuplicateViewModel` jobs and section approval helpers; it emits `PipelineRunProgress` to `WorkContextBar`. `MainWindow` uses a vertical `QSplitter` (38/62) and slim header without stat chips.

**Tech Stack:** Python 3.12, PySide6, existing `QtJobManager`, `ScanViewModel`, `DuplicateViewModel`, `OrganizeByChosungUseCase`, `MoveDuplicateFilesUseCase`, `FileMoveWorker`.

**Spec:** [../specs/2026-05-22-workflow-pipeline-ui-design.md](../specs/2026-05-22-workflow-pipeline-ui-design.md) (approved; rev. 3.1 auto-pipeline)

**Prerequisite:** [2026-05-22-ui-work-hub-ia.md](2026-05-22-ui-work-hub-ia.md) manual checklist complete + `python scripts/verify_phase_completion.py` PASS.

---

## File map

| Path | Responsibility |
|------|----------------|
| `src/gui/view_models/work_pipeline_dto.py` | **Create** — `StepState`, `PipelineSnapshot`, `PipelineRunProgress`, `PipelinePhase` |
| `src/gui/view_models/work_pipeline_view_model.py` | **Create** — step gating, active step, runner progress relay |
| `src/gui/services/work_pipeline_runner.py` | **Create** — one-button orchestrator |
| `src/gui/views/work/work_context_bar.py` | **Create** — folder, metrics, run/stop, global progress |
| `src/gui/views/work/step_card.py` | **Create** — numbered card, state pill, `set_active` |
| `src/gui/views/work/sections/finalize_section.py` | **Create** — apply + integrity auto |
| `src/gui/views/work/work_tab.py` | **Modify** — StepCards, `set_active_step`, drop scroll/quality/summary |
| `src/gui/views/work/sections/library_section.py` | **Modify** — `pipeline_scan_*` hooks |
| `src/gui/views/work/sections/duplicate_section.py` | **Modify** — `pipeline_duplicate_*` + approval helpers |
| `src/gui/views/work/sections/move_section.py` | **Modify** — `pipeline_move_*` + run confirmation |
| `src/gui/views/components/header.py` | **Modify** — remove stat chips, add subtitle |
| `src/gui/views/main_window.py` | **Modify** — splitter, context bar stats, `run_pipeline` wiring |
| `src/gui/styles/qss/buttons.py` | **Modify** — `btnDanger`, `btnNeutral` |
| `tests/gui/view_models/test_work_pipeline_view_model.py` | **Create** |
| `tests/gui/services/test_work_pipeline_runner.py` | **Create** |
| `tests/gui/views/test_work_context_bar.py` | **Create** |
| `tests/gui/views/test_step_card.py` | **Create** |
| **Delete** | `summary_strip.py`, `quality_section.py` (after R6) |

---

### Task 1: Pipeline DTOs

**Files:**
- Create: `src/gui/view_models/work_pipeline_dto.py`
- Test: `tests/gui/view_models/test_work_pipeline_dto.py`

- [ ] **Step 1: Write failing test**

```python
# tests/gui/view_models/test_work_pipeline_dto.py
from gui.view_models.work_pipeline_dto import (
    PipelineRunProgress,
    StepId,
    StepState,
    compute_overall_percent,
)


def test_compute_overall_percent_scan_half() -> None:
    assert compute_overall_percent(step_index=0, step_count=4, intra_step_ratio=0.5) == 12


def test_pipeline_run_progress_frozen() -> None:
    p = PipelineRunProgress(
        run_id="r1",
        current_step_id=StepId.SCAN,
        step_index=0,
        step_label="스캔",
        detail_message="1,000 files",
        overall_percent=12,
        phase="running",
    )
    assert p.phase == "running"
```

- [ ] **Step 2: Run test — expect FAIL**

```bash
pytest tests/gui/view_models/test_work_pipeline_dto.py -v
```

- [ ] **Step 3: Implement DTOs**

```python
# src/gui/view_models/work_pipeline_dto.py
from dataclasses import dataclass
from enum import Enum
from typing import Literal

StepState = Literal["locked", "ready", "running", "done", "skipped", "blocked"]
PipelinePhase = Literal["running", "awaiting_approval", "completed", "failed", "cancelled"]
FinalizeSubstate = Literal[
    "idle", "applying", "apply_done", "integrity_running", "integrity_done", "apply_failed"
]


class StepId(str, Enum):
    SCAN = "scan"
    DUPLICATE = "duplicate"
    MOVE = "move"
    FINALIZE = "finalize"


STEP_ORDER: tuple[StepId, ...] = (
    StepId.SCAN,
    StepId.DUPLICATE,
    StepId.MOVE,
    StepId.FINALIZE,
)


def compute_overall_percent(step_index: int, step_count: int, intra_step_ratio: float) -> int:
    if step_count <= 0:
        return 0
    bucket = 100 / step_count
    return min(100, int(step_index * bucket + intra_step_ratio * bucket))


@dataclass(frozen=True)
class PipelineSnapshot:
    steps: dict[str, StepState]
    active_step_id: str | None
    finalize_substate: FinalizeSubstate


@dataclass(frozen=True)
class PipelineRunProgress:
    run_id: str
    current_step_id: str
    step_index: int
    step_label: str
    detail_message: str
    overall_percent: int
    phase: PipelinePhase
```

- [ ] **Step 4: pytest PASS**

- [ ] **Step 5: Commit** `[gui] add work pipeline DTOs`

---

### Task 2: WorkPipelineViewModel

**Files:**
- Create: `src/gui/view_models/work_pipeline_view_model.py`
- Test: `tests/gui/view_models/test_work_pipeline_view_model.py`

- [ ] **Step 1: Failing test — scan done unlocks duplicate**

```python
# tests/gui/view_models/test_work_pipeline_view_model.py
from gui.view_models.work_pipeline_view_model import WorkPipelineViewModel
from gui.models.app_state import AppState


def test_duplicate_locked_until_scan_done(qapp) -> None:
    vm = WorkPipelineViewModel(app_state=AppState())
    snap = vm.build_snapshot(scan_done=False, duplicate_done=False, move_done=False)
    assert snap.steps["duplicate"] == "locked"
    snap2 = vm.build_snapshot(scan_done=True, duplicate_done=False, move_done=False)
    assert snap2.steps["duplicate"] == "ready"
```

- [ ] **Step 2: Run — FAIL**

- [ ] **Step 3: Implement**

```python
# src/gui/view_models/work_pipeline_view_model.py (core)
class WorkPipelineViewModel(QObject):
    snapshot_changed = Signal(object)  # PipelineSnapshot
    run_progress_changed = Signal(object)  # PipelineRunProgress | None

    def build_snapshot(
        self,
        *,
        scan_done: bool,
        duplicate_done: bool,
        duplicate_skipped: bool,
        move_done: bool,
        move_skipped: bool,
        active_step_id: str | None = None,
        finalize_substate: FinalizeSubstate = "idle",
    ) -> PipelineSnapshot:
        steps: dict[str, StepState] = {
            "scan": "done" if scan_done else "ready",
            "duplicate": (
                "skipped" if duplicate_skipped else "done" if duplicate_done
                else "ready" if scan_done else "locked"
            ),
            "move": (
                "skipped" if move_skipped else "done" if move_done
                else "ready" if (duplicate_done or duplicate_skipped) else "locked"
            ),
            "finalize": (
                "ready" if (move_done or move_skipped) else "locked"
            ),
        }
        return PipelineSnapshot(steps=steps, active_step_id=active_step_id, finalize_substate=finalize_substate)
```

- [ ] **Step 4: pytest PASS**

- [ ] **Step 5: Commit** `[gui] add WorkPipelineViewModel`

---

### Task 3: StepCard + WorkTab active step scroll

**Files:**
- Create: `src/gui/views/work/step_card.py`
- Modify: `src/gui/views/work/work_tab.py`
- Test: `tests/gui/views/test_step_card.py`

- [ ] **Step 1: Failing test**

```python
# tests/gui/views/test_step_card.py
from gui.views.work.step_card import StepCard


def test_step_card_active_property(qapp) -> None:
    card = StepCard("scan", "1", "스캔")
    card.set_active(True)
    assert card.property("active") is True
```

- [ ] **Step 2: Implement `StepCard`**

- Header: `QLabel` badge + title + state pill (`대기`/`진행중`/…)
- `set_state(StepState)`, `set_active(bool)` → dynamic property `active` for QSS `#stepCard[active="true"]`
- Body `QVBoxLayout` for section widget

- [ ] **Step 3: `WorkTab.set_active_step(step_id)`**

```python
def set_active_step(self, step_id: str) -> None:
    for sid, card in self._step_cards.items():
        card.set_active(sid == step_id)
    scroll = self.findChild(QScrollArea)
    card = self._step_cards.get(step_id)
    if scroll and card:
        scroll.ensureWidgetVisible(card)
```

- [ ] **Step 4: pytest PASS**

- [ ] **Step 5: Commit** `[gui] StepCard and active step scroll`

---

### Task 4: WorkContextBar (metrics + global pipeline progress)

**Files:**
- Create: `src/gui/views/work/work_context_bar.py`
- Test: `tests/gui/views/test_work_context_bar.py`

- [ ] **Step 1: Failing test**

```python
def test_context_bar_run_button_emits_signal(qapp, qtbot) -> None:
    from gui.views.work.work_context_bar import WorkContextBar
    bar = WorkContextBar()
    with qtbot.waitSignal(bar.run_pipeline_requested, timeout=1000):
        qtbot.mouseClick(bar._run_btn, Qt.MouseButton.LeftButton)
```

- [ ] **Step 2: Implement**

Signals: `run_pipeline_requested`, `cancel_pipeline_requested`, `folder_change_requested`, `rescan_requested`.

Widgets:
- Row1: folder label + neutral/secondary buttons
- Row2: four metric labels (reuse `WorkSummary` fields)
- Row3: `btnPrimary` "전체 작업 실행", `btnDanger` "중지" (hidden when idle), `QProgressBar` `objectName=pipelineProgress`, `QLabel` `pipelineProgressLabel`

Methods: `update_summary(WorkSummary)`, `update_pipeline_progress(PipelineRunProgress | None)`, `set_pipeline_running(bool)`.

- [ ] **Step 3: pytest PASS**

- [ ] **Step 4: Commit** `[gui] WorkContextBar with pipeline progress row`

---

### Task 5: Slim header

**Files:**
- Modify: `src/gui/views/components/header.py`
- Modify: `src/gui/views/main_window.py` (stop passing stats to header)

- [ ] Remove four `_create_stat_item` widgets; add subtitle `QLabel` `headerSubtitle`.
- [ ] Delete `update_stats` calls from `main_window._update_header_stats_from_store`; route to `WorkTab.context_bar` only.
- [ ] Manual: header shows title + subtitle only.

- [ ] **Commit** `[gui] slim header; stats on context bar only`

---

### Task 6: MainWindow QSplitter 38/62

**Files:**
- Modify: `src/gui/views/main_window.py`

- [ ] Replace `center_layout.addWidget(stack, 2)` + `addWidget(table, 1)` with:

```python
splitter = QSplitter(Qt.Orientation.Vertical)
splitter.addWidget(self._content_stack)
splitter.addWidget(self._file_list_table)
splitter.setStretchFactor(0, 38)
splitter.setStretchFactor(1, 62)
splitter.setSizes([380, 620])  # tune on first show
center_layout.addWidget(splitter)
```

- [ ] Optional: persist `ui/work_splitter_state` via `QSettings`.

- [ ] **Commit** `[gui] vertical splitter for work vs file table`

---

### Task 7: Section pipeline ports

**Files:**
- Modify: `library_section.py`, `duplicate_section.py`, `move_section.py`

Expose imperative API for runner (no duplicate use-case logic):

**LibrarySection**
- `scan_view_model: ScanViewModel` property
- `request_full_scan() -> None` — calls existing `_on_start_scan` preconditions
- `cancel_scan() -> None`

**DuplicateSection**
- `request_detection() -> None`
- `duplicate_dry_run_and_preview(parent) -> bool` — opens `DryRunPreviewDialog`; returns True if user OK to continue (or no ops)
- `duplicate_apply_with_confirmation(parent) -> bool` — wraps existing `_on_apply` QMessageBox; returns True on Yes
- `cancel_detection() -> None`

**MoveSection**
- `run_dry_run_sync() -> bool` — returns False on error
- `run_execute_with_confirmation(parent) -> bool` — **add** `QMessageBox.question` before `dry_run=False` (spec safety)
- Signals or callbacks: `move_finished` for runner await

- [ ] Wire `duplicate_completed` / `scan_completed` to runner (Task 8).

- [ ] **Commit** `[gui] section pipeline port methods`

---

### Task 8: WorkPipelineRunner

**Files:**
- Create: `src/gui/services/work_pipeline_runner.py`
- Test: `tests/gui/services/test_work_pipeline_runner.py`

- [ ] **Step 1: Failing test (mock sections with signals)**

```python
def test_runner_starts_on_scan_and_emits_progress(qapp, qtbot) -> None:
    # Use stub ScanViewModel emitting scan_completed with ScanResult(total_files=1, ...)
    # Assert run_progress_changed step_index 0 then 1 after complete
```

- [ ] **Step 2: Implement runner state machine**

```python
class WorkPipelineRunner(QObject):
    progress_changed = Signal(object)  # PipelineRunProgress
    finished = Signal(str)  # completed | failed | cancelled
    step_changed = Signal(str)  # StepId value

    def __init__(
        self,
        *,
        scan_vm: ScanViewModel,
        duplicate_vm: DuplicateViewModel,
        library: LibrarySection,
        duplicate: DuplicateSection,
        move: MoveSection,
        finalize: FinalizeSection,
        parent: QObject | None = None,
    ) -> None: ...

    def start(self, folder: Path) -> None: ...
    def cancel(self) -> None: ...
```

**`start` sequence:**
1. Emit `step_changed("scan")`, progress phase `running`, step 0.
2. `library.request_full_scan()`; connect one-shot `scan_vm.scan_completed` → `_after_scan`.
3. `_after_scan`: if cancelled stop. Else step 1 → `duplicate.request_detection()`; wait `duplicate_vm.duplicate_completed`.
4. If `len(results)==0`: mark duplicate `skipped`, jump to move.
5. Else: `duplicate_dry_run_and_preview` → if False: `finished("cancelled")`.
6. `duplicate_apply_with_confirmation` → if False: stop.
7. `move.run_dry_run_sync()` → `move.run_execute_with_confirmation`.
8. `finalize.run_apply_and_integrity_auto()` (Task 9).
9. `finished("completed")`.

**Progress:** on each `JobProgress`, call `compute_overall_percent(step_index, 4, ratio)`; emit `PipelineRunProgress`.

**Cancel:** set `_cancelled=True`, call scan/duplicate cancel on job_manager if API exists.

- [ ] **Step 3: pytest with mocks PASS**

- [ ] **Step 4: Commit** `[gui] WorkPipelineRunner one-button sequence`

---

### Task 9: FinalizeSection + integrity auto

**Files:**
- Create: `src/gui/views/work/sections/finalize_section.py`
- Test: `tests/gui/views/test_finalize_section.py`

- [ ] Apply button (Primary) when move done; on success emit `apply_succeeded`.
- [ ] Slot on `apply_succeeded`: start integrity job via port stub or no-op with tooltip.
- [ ] `run_apply_and_integrity_auto(parent) -> bool` for runner — chains apply confirm + auto integrity.

- [ ] **Commit** `[gui] finalize section apply and integrity auto`

---

### Task 10: Wire WorkTab + MainWindow to runner

**Files:**
- Modify: `work_tab.py`, `main_window.py`

- [ ] `WorkTab` builds `WorkPipelineRunner` with section refs; connects:
  - `runner.progress_changed` → `context_bar.update_pipeline_progress`
  - `runner.step_changed` → `set_active_step` + `pipeline_vm.build_snapshot(..., active_step_id=...)`
  - `context_bar.run_pipeline_requested` → `main_window._on_run_full_pipeline`
- [ ] `_on_run_full_pipeline`:
  - `self._switch_tab("work")`
  - validate `scan_folder`
  - `runner.start(folder)`
  - disable per-step Primary buttons while running
- [ ] `cancel` → `runner.cancel()`

- [ ] **Commit** `[gui] wire full pipeline run to context bar`

---

### Task 11: Migrate WorkTab layout (StepCards replace WorkSection)

**Files:**
- Modify: `work_tab.py` — remove `SummaryStrip`, `QualitySection`, `WorkSection` chevrons
- Mount: ContextBar → StepCard×4 → stretch removed (splitter handles table height)

- [ ] Port bodies from existing sections unchanged.
- [ ] Cap per-card `QProgressBar` max width 70% (layout constraint).

- [ ] **Commit** `[gui] WorkTab step pipeline layout`

---

### Task 12: Button QSS + table status chips

**Files:**
- Modify: `gui/styles/qss/buttons.py`, `file_list_table.py`

- [ ] Add `#btnDanger`, `#btnNeutral` per DESIGN.md error/outline tokens.
- [ ] Add **상태** column delegate rendering chip pills (`대표 파일`, `중복 의심`, `검사 필요`).

- [ ] **Commit** `[gui] danger/neutral buttons and file status chips`

---

### Task 13: Cleanup + docs

**Files:**
- Delete: `summary_strip.py`, `quality_section.py`
- Modify: `docs/superpowers/README.md` — add plan link

- [ ] `rg summary_strip quality_section` → fix imports.

- [ ] **Commit** `[gui] remove summary strip and quality section`

---

### Task 14: Verification

- [ ] `pytest tests/gui/view_models/test_work_pipeline_dto.py tests/gui/view_models/test_work_pipeline_view_model.py tests/gui/services/test_work_pipeline_runner.py tests/gui/views/test_work_context_bar.py tests/gui/views/test_step_card.py -v`
- [ ] `python scripts/verify_phase_completion.py`
- [ ] Manual spec §6 checklist including auto-pipeline items.

---

## Spec coverage (self-review)

| Spec requirement | Task |
|------------------|------|
| WorkContextBar + metrics | 4, 5 |
| Slim header | 5 |
| Splitter 38/62 | 6 |
| StepCard pipeline | 3, 11 |
| Finalize apply→integrity auto | 9 |
| One-button auto-run + UI step sync | 7, 8, 10 |
| Global pipeline progress | 4, 8 |
| MainWindow stays on 작업 | 10 |
| Approval gates not skipped | 7, 8 |
| btnDanger/Neutral | 12 |
| File chips | 12 |
| Delete quality/summary | 13 |
| Progress bar 70% in cards | 11 |

## Execution handoff

Plan complete and saved to `docs/superpowers/plans/2026-05-22-workflow-pipeline-ui.md`.

**Two execution options:**

1. **Subagent-Driven (recommended)** — fresh subagent per task, review between tasks  
2. **Inline Execution** — execute in this session via `executing-plans` with checkpoints  

Which approach?
