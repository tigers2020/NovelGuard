# Workflow Pipeline UI Rev. 3.2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver an **installation-style wizard** on the Work tab (horizontal stepper + single step panel + footer controls), **collapsible file-list dock** (default collapsed), and **one-shot confirm** before auto-run with **no modal chain** during execution.

**Architecture:** Reparent `FileListTable` from `MainWindow` into `WorkTab`'s bottom `QSplitter`. Replace `WorkContextBar` pipeline row with `WizardFooter` (prev/next/run/stop/progress). Add `PipelineRunConfirmSheet` + `compute_pipeline_run_preview()` for pre-flight summary; extend `WorkPipelineRunner.start(..., auto_run=True)` to skip mid-run dialogs. Persist dock/splitter sizes via `QSettings`.

**Tech Stack:** Python 3.12, PySide6, existing `ScanViewModel`, `DuplicateViewModel`, `MoveDuplicateFilesUseCase`, `OrganizeByChosungUseCase`, `WorkPipelineRunner`.

**Spec:** [../specs/2026-05-22-workflow-pipeline-ui-design.md](../specs/2026-05-22-workflow-pipeline-ui-design.md) §7 (approved)

**Baseline:** Rev. 3.1 already landed (`PipelineStepper`, `QStackedWidget`, `WorkPipelineRunner` with modals). This plan is **delta only**.

---

## File map (rev. 3.2)

| Path | Action | Responsibility |
|------|--------|----------------|
| `src/gui/views/work/work_compact_bar.py` | **Create** | Folder + metrics only (no run/stop row) |
| `src/gui/views/work/wizard_footer.py` | **Create** | 이전/다음/전체 실행/중지 + progress |
| `src/gui/views/work/work_file_dock.py` | **Create** | Collapsible header + hosts `FileListTableWidget` |
| `src/gui/views/work/pipeline_run_confirm_sheet.py` | **Create** | One-shot summary + checkbox |
| `src/gui/services/pipeline_run_preview.py` | **Create** | Pre-flight counts for confirm sheet |
| `src/gui/views/work/work_tab.py` | **Modify** | Wizard splitter layout; footer; dock |
| `src/gui/views/main_window.py` | **Modify** | Remove center splitter; pass table into WorkTab |
| `src/gui/services/work_pipeline_runner.py` | **Modify** | `auto_run` skips modal gates |
| `src/gui/views/work/sections/duplicate_section.py` | **Modify** | `pipeline_apply_auto`, inline status |
| `src/gui/views/work/sections/move_section.py` | **Modify** | `pipeline_execute_auto` (no QMessageBox) |
| `src/gui/styles/theme_registry.py` | **Modify** | `wizardFooter`, `workFileDock`, confirm sheet QSS |
| `tests/gui/services/test_pipeline_run_preview.py` | **Create** |
| `tests/gui/views/test_wizard_footer.py` | **Create** |
| `tests/gui/views/test_work_file_dock.py` | **Create** |
| `tests/gui/services/test_work_pipeline_runner_auto.py` | **Create** |
| `tests/gui/views/test_work_tab_wizard_layout.py` | **Create** |

---

### Task 1: Pipeline run preview service

**Files:**
- Create: `src/gui/services/pipeline_run_preview.py`
- Test: `tests/gui/services/test_pipeline_run_preview.py`

- [ ] **Step 1: Write failing test**

```python
# tests/gui/services/test_pipeline_run_preview.py
from pathlib import Path
from unittest.mock import MagicMock

from gui.models.file_data_store import FileDataStore
from gui.services.pipeline_run_preview import PipelineRunPreview, compute_pipeline_run_preview


def test_preview_empty_store() -> None:
    store = FileDataStore()
    preview = compute_pipeline_run_preview(store, scan_folder=None)
    assert preview.duplicate_move_count == 0
    assert preview.organize_dry_run_total == 0


def test_preview_duplicate_move_count(monkeypatch) -> None:
    store = FileDataStore()
    store.scan_folder = Path("/tmp/scan")

    class FakeUseCase:
        def __init__(self, store, log_sink):
            pass

        def execute(self, folder):
            return [object(), object()]

    monkeypatch.setattr(
        "gui.services.pipeline_run_preview.MoveDuplicateFilesUseCase",
        FakeUseCase,
    )
    preview = compute_pipeline_run_preview(store, scan_folder=Path("/tmp/scan"))
    assert preview.duplicate_move_count == 2
```

- [ ] **Step 2: Run test — expect FAIL**

```bash
pytest tests/gui/services/test_pipeline_run_preview.py -v
```

- [ ] **Step 3: Implement**

```python
# src/gui/services/pipeline_run_preview.py
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from application.use_cases.move_duplicate_files import MoveDuplicateFilesUseCase
from application.use_cases.organize_by_chosung import OrganizeByChosungUseCase
from gui.models.file_data_store import FileDataStore


@dataclass(frozen=True)
class PipelineRunPreview:
    folder_path: str | None
    total_files: int
    duplicate_groups: int
    duplicate_move_count: int
    organize_dry_run_total: int
    error_message: str | None = None


def compute_pipeline_run_preview(
    store: FileDataStore,
    *,
    scan_folder: Optional[Path],
    log_sink=None,
) -> PipelineRunPreview:
    folder = scan_folder or store.scan_folder
    stats_files = len(store.get_all_files()) if hasattr(store, "get_all_files") else 0
    groups = len({f.duplicate_group_id for f in store.iter_files() if f.duplicate_group_id})
    dup_count = 0
    org_total = 0
    err: str | None = None
    if folder and folder.is_dir():
        try:
            dup_count = len(MoveDuplicateFilesUseCase(store, log_sink).execute(folder))
        except Exception as e:
            err = str(e)
        try:
            org_total = OrganizeByChosungUseCase(log_sink=log_sink).execute(
                root_path=folder, move=True, dry_run=True
            ).total_processed
        except Exception as e:
            err = err or str(e)
    return PipelineRunPreview(
        folder_path=str(folder) if folder else None,
        total_files=stats_files,
        duplicate_groups=groups,
        duplicate_move_count=dup_count,
        organize_dry_run_total=org_total,
        error_message=err,
    )
```

Adjust `store.iter_files()` / `get_all_files()` to match actual `FileDataStore` API (grep before implement).

- [ ] **Step 4: pytest PASS**

- [ ] **Step 5: Commit** `[gui] add pipeline run preview for confirm sheet`

---

### Task 2: PipelineRunConfirmSheet

**Files:**
- Create: `src/gui/views/work/pipeline_run_confirm_sheet.py`
- Test: `tests/gui/views/test_pipeline_run_confirm_sheet.py`

- [ ] **Step 1: Failing test**

```python
# tests/gui/views/test_pipeline_run_confirm_sheet.py
from gui.services.pipeline_run_preview import PipelineRunPreview
from gui.views.work.pipeline_run_confirm_sheet import PipelineRunConfirmSheet


def test_confirm_requires_checkbox(qapp) -> None:
    sheet = PipelineRunConfirmSheet()
    preview = PipelineRunPreview(
        folder_path="/tmp/x",
        total_files=10,
        duplicate_groups=1,
        duplicate_move_count=3,
        organize_dry_run_total=5,
    )
    sheet.set_preview(preview)
    assert not sheet.is_confirmed()
    sheet._confirm_check.setChecked(True)
    assert sheet.is_confirmed()
```

- [ ] **Step 2: Run — FAIL**

- [ ] **Step 3: Implement `PipelineRunConfirmSheet`**

- `set_preview(PipelineRunPreview)` fills labels
- `confirmed = Signal()` emitted on [시작] when checkbox checked
- `cancelled = Signal()` on [취소]
- `objectName` `pipelineRunConfirmSheet`; shown in `QStackedWidget` overlay index or replaces step stack top — **implement as stacked page index 4** `confirm` on WorkTab wizard stack OR modal-free widget inserted above footer

**WorkTab pattern:** temporary `QStackedWidget` layer:

```python
# In WorkTab._show_confirm_sheet(preview):
self._confirm_sheet.set_preview(preview)
self._wizard_stack.setCurrentWidget(self._confirm_sheet)  # confirm is 5th widget in inner stack
```

- [ ] **Step 4: pytest PASS**

- [ ] **Step 5: Commit** `[gui] PipelineRunConfirmSheet one-shot approval UI`

---

### Task 3: WorkCompactBar + WizardFooter

**Files:**
- Create: `src/gui/views/work/work_compact_bar.py`
- Create: `src/gui/views/work/wizard_footer.py`
- Test: `tests/gui/views/test_wizard_footer.py`
- Modify: `src/gui/views/work/work_context_bar.py` — **delete** or deprecate; migrate callers to compact+footer

- [ ] **Step 1: `WorkCompactBar`** — folder row + metrics row only (extract from `work_context_bar.py` lines 35-65 without pipeline row)

- [ ] **Step 2: `WizardFooter`**

```python
# src/gui/views/work/wizard_footer.py (signals)
class WizardFooter(QWidget):
    prev_clicked = Signal()
    next_clicked = Signal()
    run_pipeline_requested = Signal()
    cancel_pipeline_requested = Signal()

    def update_pipeline_progress(self, progress: PipelineRunProgress | None) -> None: ...
    def set_pipeline_running(self, running: bool) -> None: ...
```

- [ ] **Step 3: Test footer run signal**

```python
def test_footer_run_emits(qapp) -> None:
    from gui.views.work.wizard_footer import WizardFooter
    footer = WizardFooter()
    got: list[bool] = []
    footer.run_pipeline_requested.connect(lambda: got.append(True))
    footer._run_btn.click()
    assert got
```

- [ ] **Step 4: pytest PASS; commit** `[gui] WorkCompactBar and WizardFooter`

---

### Task 4: WorkFileDock + reparent table (W1)

**Files:**
- Create: `src/gui/views/work/work_file_dock.py`
- Modify: `src/gui/views/work/work_tab.py`
- Modify: `src/gui/views/main_window.py`
- Test: `tests/gui/views/test_work_file_dock.py`

- [ ] **Step 1: Failing test**

```python
def test_dock_collapsed_by_default(qapp) -> None:
    from gui.views.work.work_file_dock import WorkFileDock
    from gui.models.file_data_store import FileDataStore
    from gui.views.components.file_list_table import FileListTableWidget
    dock = WorkFileDock(FileListTableWidget(FileDataStore()))
    assert dock.is_collapsed()
```

- [ ] **Step 2: Implement `WorkFileDock`**

- Header button `▼ 파일 목록 (N)` toggles collapsed state
- When collapsed: `setSizes` on parent splitter → table section ~48px
- `collapse()` / `expand()` methods
- `file_count` updates label

- [ ] **Step 3: `WorkTab` layout**

```python
self._splitter = QSplitter(Qt.Orientation.Vertical)
wizard = QWidget()
wizard_layout = QVBoxLayout(wizard)
wizard_layout.addWidget(self._compact_bar)
wizard_layout.addWidget(self._stepper)
wizard_layout.addWidget(self._step_stack, stretch=1)
wizard_layout.addWidget(self._footer)
self._file_dock = WorkFileDock(file_table, parent=self)
self._splitter.addWidget(wizard)
self._splitter.addWidget(self._file_dock)
self._splitter.setStretchFactor(0, 9)
self._splitter.setStretchFactor(1, 1)
self._splitter.setSizes([720, 48])  # collapsed default
```

- [ ] **Step 4: `MainWindow`**

```python
# Remove _file_list_table from center splitter; only content_stack in center_layout
self._work_tab.set_file_list_table(
    FileListTableWidget(self._app_state.file_data_store, self._work_tab)
)
```

Add `WorkTab.set_file_list_table(table)` called from `_setup_tabs` after work tab created.

- [ ] **Step 5: pytest PASS; commit** `[gui] file list dock inside WorkTab`

---

### Task 5: Wire footer navigation + confirm flow (W2)

**Files:**
- Modify: `src/gui/views/work/work_tab.py`

- [ ] **Step 1: Footer `이전`/`다음`**

```python
STEP_IDS = [s.value for s in STEP_ORDER]

def _on_prev(self) -> None:
    idx = STEP_IDS.index(self._current_step_id)
    if idx > 0:
        self.set_active_step(STEP_IDS[idx - 1])

def _on_next(self) -> None:
    idx = STEP_IDS.index(self._current_step_id)
    if idx < len(STEP_IDS) - 1:
        next_id = STEP_IDS[idx + 1]
        if self._stepper._steps[next_id]._apply_enabled(True):  # or use pipeline_vm snapshot
            self.set_active_step(next_id)
```

Expose `PipelineStepper.set_step_enabled(step_id, bool)` if needed.

- [ ] **Step 2: Run button opens confirm sheet**

```python
def _on_run_pipeline_requested(self) -> None:
    folder = self._library_section_widget.get_scan_folder()
    if not folder:
        QMessageBox.warning(self, "폴더 필요", "먼저 스캔할 폴더를 선택하세요.")
        return
    preview = compute_pipeline_run_preview(
        self._app_state.file_data_store,
        scan_folder=folder,
        log_sink=self._log_sink,
    )
    if preview.error_message:
        self._confirm_sheet.show_error(preview.error_message)
    self._confirm_sheet.set_preview(preview)
    self._wizard_stack.setCurrentWidget(self._confirm_sheet)
```

On `confirmed` signal → `self._pipeline_runner.start(folder, auto_run=True)` and restore wizard stack widget.

- [ ] **Step 3: Move progress wiring from context bar to footer**

- [ ] **Step 4: Manual test; commit** `[gui] wizard footer navigation and confirm gate`

---

### Task 6: Runner `auto_run` — no mid-run modals (W3)

**Files:**
- Modify: `src/gui/services/work_pipeline_runner.py`
- Modify: `src/gui/views/work/sections/duplicate_section.py`
- Modify: `src/gui/views/work/sections/move_section.py`
- Test: `tests/gui/services/test_work_pipeline_runner_auto.py`

- [ ] **Step 1: Failing test**

```python
def test_auto_run_skips_dry_run_dialog(qapp, monkeypatch) -> None:
    # Mock duplicate.pipeline_dry_run_preview — must NOT be called when auto_run=True
    calls = []
    monkeypatch.setattr(
        "gui.services.work_pipeline_runner.DuplicateSection.pipeline_dry_run_preview",
        lambda self, parent: calls.append(1) or True,
    )
    # ... build runner with mocks, start(folder, auto_run=True)
    # assert calls == []
```

- [ ] **Step 2: Add APIs**

```python
# duplicate_section.py
def pipeline_apply_auto(self) -> bool:
    """Apply duplicate moves without QMessageBox; returns success."""
    # same worker path as pipeline_start_apply but no question dialog

# move_section.py
def pipeline_execute_auto(self) -> bool:
    """Execute move/copy without QMessageBox."""
```

- [ ] **Step 3: Runner**

```python
def start(self, folder: Path, *, auto_run: bool = False) -> None:
    self._auto_run = auto_run
    ...

def _on_duplicate_completed(self, results: list) -> None:
    ...
    if self._auto_run:
        self._duplicate.show_auto_apply_status(len(results))  # optional label
        self._connect_once(self._duplicate.pipeline_apply_finished, self._on_duplicate_apply_done)
        if not self._duplicate.pipeline_apply_auto():
            ...
        return
    # existing modal path for manual run_all with auto_run=False
```

```python
def _begin_move(self) -> None:
    if not self._move.pipeline_dry_run_sync():
        ...
    if self._auto_run:
        if not self._move.pipeline_execute_auto():
            self.finished.emit("failed")
            return
    elif not self._move.pipeline_execute_with_confirmation(...):
        ...
```

- [ ] **Step 4: pytest PASS; commit** `[gui] pipeline auto_run without modal chain`

---

### Task 7: QSettings persistence (W4)

**Files:**
- Modify: `src/gui/views/work/work_tab.py`
- Modify: `src/gui/views/work/work_file_dock.py`

- [ ] **Step 1: On show, restore `ui/work_wizard_splitter` sizes and `ui/work_file_dock_expanded` bool

- [ ] **Step 2: On splitter moved / dock toggle, save settings

- [ ] **Step 3: Commit** `[gui] persist wizard splitter and dock state`

---

### Task 8: QSS polish

**Files:**
- Modify: `src/gui/styles/theme_registry.py`

- [ ] Add `#wizardFooter`, `#workFileDock`, `#pipelineRunConfirmSheet`, `#pipelineStepStack`

- [ ] **Commit** `[gui] rev32 wizard shell QSS`

---

### Task 9: Verification

- [ ] `pytest tests/gui/services/test_pipeline_run_preview.py tests/gui/views/test_wizard_footer.py tests/gui/views/test_work_file_dock.py tests/gui/services/test_work_pipeline_runner_auto.py tests/gui/views/test_work_tab_wizard_layout.py -v`
- [ ] `python scripts/verify_phase_completion.py`
- [ ] Manual §7 checklist:
  - [ ] Work tab: wizard uses most of height; dock collapsed
  - [ ] Footer has run/prev/next; no full-width top run button
  - [ ] Auto-run: one confirm sheet only; no DryRun dialog mid-run
  - [ ] Manual Dry Run still opens dialog

---

## Spec coverage (self-review)

| §7 requirement | Task |
|----------------|------|
| MainWindow no file table | 4 |
| WorkTab splitter wizard/dock | 4 |
| Compact bar | 3 |
| Wizard footer | 3, 5 |
| One-shot confirm | 1, 2, 5 |
| auto_run no modals | 6 |
| Dock collapsed default | 4, 7 |
| QSettings | 7 |
| Scan hint expand dock | 5 (optional link in library_section on scan complete) |

## Execution handoff

Plan complete and saved to `docs/superpowers/plans/2026-05-22-workflow-pipeline-ui-rev32.md`.

**Two execution options:**

1. **Subagent-Driven (recommended)** — fresh subagent per task, review between tasks  
2. **Inline Execution** — execute in this session via `executing-plans` with checkpoints  

Which approach?
