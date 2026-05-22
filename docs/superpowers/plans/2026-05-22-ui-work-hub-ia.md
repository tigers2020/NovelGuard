# UI Work Screen (Single-Surface IA) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace scattered workflow tabs with one **Work** screen (collapsible sections), a **3-item sidebar** (작업 · 로그 · 설정), a **global Undo/Redo toolbar**, and wired duplicate groups/evidence UI—while keeping the bottom file list and destructive approval flows unchanged.

**Architecture:** Extract existing `ScanTab` / `DuplicateTab` / `MoveOrganizeTab` logic into `gui/views/work/sections/*` widgets that keep current ViewModels. `WorkViewModel` aggregates `FileDataStore` + job status for the summary strip only. `MainWindow` stack shrinks to `work | logs | settings`. Shared stats live in `gui/services/work_stats.py` for header + strip.

**Tech Stack:** Python 3.12, PySide6, existing `ScanViewModel`, `DuplicateViewModel`, `OrganizeByChosungUseCase`, `PreviewWorker`.

**Spec:** [../specs/2026-05-22-ui-work-hub-ia-design.md](../specs/2026-05-22-ui-work-hub-ia-design.md) (approved 2026-05-22)

**Status:** implemented on branch `feature/ui-work-hub-ia` (2026-05-22)

---

## File map (create / modify / delete)

| Path | Responsibility |
|------|----------------|
| `src/gui/services/work_stats.py` | **Create** — `compute_work_stats(file_data_store) -> WorkStats` (4 header fields + extras for strip) |
| `src/gui/view_models/work_dto.py` | **Create** — `WorkSummary`, `WorkStats` dataclasses |
| `src/gui/view_models/work_view_model.py` | **Create** — summary strip refresh signals |
| `src/gui/views/work/work_section.py` | **Create** — collapsible `QGroupBox` wrapper (`section_id`, `set_expanded`) |
| `src/gui/views/work/work_tab.py` | **Create** — scroll area, sections, `scroll_to_section()` |
| `src/gui/views/work/sections/summary_strip.py` | **Create** — metrics + jump buttons |
| `src/gui/views/work/sections/library_section.py` | **Create** — from `scan_tab.py` |
| `src/gui/views/work/sections/duplicate_section.py` | **Create** — from `duplicate_tab.py` + groups/evidence |
| `src/gui/views/work/sections/move_section.py` | **Create** — from `move_organize_tab.py` (no folder browse) |
| `src/gui/views/work/sections/quality_section.py` | **Create** — disabled placeholders |
| `src/gui/views/components/global_action_toolbar.py` | **Create** — Undo/Redo actions |
| `src/gui/views/components/header.py` | **Modify** — 4 stat chips |
| `src/gui/views/components/sidebar.py` | **Modify** — work / logs / settings |
| `src/gui/views/main_window.py` | **Modify** — toolbar, stack, stats helper, folder/preview wiring |
| `src/gui/models/app_state.py` | **Modify** — `current_tab="work"` |
| `src/gui/styles/qss/toolbar.py` or `theme_registry.py` | **Modify** — `#globalActionToolbar` styles |
| `tests/gui/view_models/test_work_view_model.py` | **Create** |
| `tests/gui/views/test_work_tab_sections.py` | **Create** — scroll + collapse smoke |
| **Delete after parity** | `scan_tab.py`, `duplicate_tab.py`, `move_organize_tab.py`, `integrity_tab.py`, `encoding_tab.py`, `small_file_tab.py`, `stats_tab.py`, `undo_tab.py` |

---

### Task 1: Shared work stats + header (4 chips)

**Files:**
- Create: `src/gui/services/work_stats.py`
- Create: `src/gui/view_models/work_dto.py`
- Modify: `src/gui/views/components/header.py`
- Modify: `src/gui/views/main_window.py`
- Test: `tests/gui/services/test_work_stats.py`

- [ ] **Step 1: Write failing test**

```python
# tests/gui/services/test_work_stats.py
from gui.models.file_data_store import FileData, FileDataStore
from gui.services.work_stats import compute_work_stats


def test_compute_work_stats_empty_store() -> None:
    store = FileDataStore()
    stats = compute_work_stats(store)
    assert stats.total_files == 0
    assert stats.duplicate_groups == 0
    assert stats.saved_gb == 0.0
    assert stats.integrity_issues == 0


def test_compute_work_stats_counts_duplicate_groups() -> None:
    store = FileDataStore()
    store.add_files_batch(
        [
            FileData(file_id=1, path="/a.txt", size=100, mtime=None, extension=".txt",
                     duplicate_group_id=1, is_canonical=True),
            FileData(file_id=2, path="/b.txt", size=200, mtime=None, extension=".txt",
                     duplicate_group_id=1, is_canonical=False),
        ]
    )
    stats = compute_work_stats(store)
    assert stats.total_files == 2
    assert stats.duplicate_groups == 1
    assert stats.saved_gb > 0
```

- [ ] **Step 2: Run test — expect FAIL**

```bash
pytest tests/gui/services/test_work_stats.py -v
```

- [ ] **Step 3: Implement `work_dto.py` + `work_stats.py`**

Move aggregation logic from `MainWindow._calculate_stats()` into `compute_work_stats()` returning:

```python
@dataclass(frozen=True)
class WorkStats:
    total_files: int
    duplicate_groups: int
    saved_gb: float
    integrity_issues: int
    # optional for strip (not header chips):
    processed_files: int
    duplicate_files: int
    total_size_gb: float
    small_files: int
```

- [ ] **Step 4: Slim `header.py` to four `_create_stat_item` widgets; `update_stats(total_files, duplicate_groups, saved_gb, integrity_issues)`**

- [ ] **Step 5: `main_window._update_header_stats_from_store` calls `compute_work_stats` then `header.update_stats(...)`**

- [ ] **Step 6: pytest PASS; commit** `[gui] extract work stats and slim header`

---

### Task 2: Global Undo/Redo toolbar

**Files:**
- Create: `src/gui/views/components/global_action_toolbar.py`
- Modify: `src/gui/views/main_window.py`
- Modify: `src/gui/styles/theme_registry.py` (or `qss/base.py`) — toolbar QSS
- Test: `tests/gui/views/test_global_action_toolbar.py`

- [ ] **Step 1: Write failing test**

```python
# tests/gui/views/test_global_action_toolbar.py
from PySide6.QtWidgets import QWidget
from gui.views.components.global_action_toolbar import GlobalActionToolbar


def test_toolbar_undo_redo_disabled_by_default(qapp) -> None:
    parent = QWidget()
    bar = GlobalActionToolbar(parent)
    assert not bar.undo_action.isEnabled()
    assert not bar.redo_action.isEnabled()
    assert "미구현" in bar.undo_action.toolTip()
```

- [ ] **Step 2: Run test — FAIL**

- [ ] **Step 3: Implement toolbar**

```python
class GlobalActionToolbar(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("globalActionToolbar")
        self.undo_action = QAction("실행 취소", self)
        self.undo_action.setObjectName("toolbarUndo")
        self.undo_action.setShortcut("Ctrl+Z")
        self.undo_action.setEnabled(False)
        self.undo_action.setToolTip("실행 취소 (미구현)")
        # redo: Ctrl+Y + Ctrl+Shift+Z
```

Use `QToolBar` or `QHBoxLayout` with `QToolButton` tied to actions.

- [ ] **Step 4: `main_window._setup_ui` — insert toolbar between `_header` and `content_widget`**

- [ ] **Step 5: pytest PASS; commit** `[gui] add global undo/redo toolbar shell`

---

### Task 3: WorkSection base + WorkViewModel

**Files:**
- Create: `src/gui/views/work/work_section.py`
- Create: `src/gui/view_models/work_view_model.py`
- Test: `tests/gui/view_models/test_work_view_model.py`

- [ ] **Step 1: Failing test for summary when folder set**

```python
# tests/gui/view_models/test_work_view_model.py
from gui.view_models.work_view_model import WorkViewModel
from gui.models.app_state import AppState


def test_work_view_model_library_idle_without_folder(qapp) -> None:
    state = AppState()
    vm = WorkViewModel(app_state=state, job_manager=None, log_sink=None)
    snap = vm.build_summary()
    assert snap.folder_path is None
    assert snap.library_state == "idle"
```

- [ ] **Step 2: Implement `WorkSummary` in `work_dto.py` (if not done) and `WorkViewModel.build_summary()`** using `compute_work_stats` + `app_state.scan_folder` + detecting flags from job_manager status when available.

- [ ] **Step 3: Implement `WorkSection(QGroupBox)`** with `section_id: str`, `set_expanded(bool)`, `is_expanded() -> bool`, checkable title via `QToolButton` or `toggle` on group title.

- [ ] **Step 4: pytest PASS; commit** `[gui] add WorkSection and WorkViewModel`

---

### Task 4: WorkTab shell + sidebar + MainWindow stack

**Files:**
- Create: `src/gui/views/work/work_tab.py`, `src/gui/views/work/__init__.py`
- Create: `src/gui/views/work/sections/__init__.py`
- Create: `src/gui/views/work/sections/summary_strip.py` (placeholder metrics + jump buttons)
- Modify: `src/gui/views/components/sidebar.py`
- Modify: `src/gui/views/main_window.py`
- Modify: `src/gui/models/app_state.py`
- Test: `tests/gui/views/test_work_tab_sections.py`

- [ ] **Step 1: Failing test — default section collapse**

```python
def test_work_tab_move_and_quality_collapsed_by_default(qapp) -> None:
    from gui.views.work.work_tab import WorkTab
    tab = WorkTab()
    assert not tab.section("move").is_expanded()
    assert not tab.section("quality").is_expanded()
    assert tab.section("library").is_expanded()
```

- [ ] **Step 2: Implement `WorkTab` skeleton** — `QScrollArea`, register sections dict, stub section bodies as empty `WorkSection` widgets.

- [ ] **Step 3: `scroll_to_section(section_id)`** — `QScrollArea.ensureWidgetVisible(section)`.

- [ ] **Step 4: Sidebar** — only `("work", "작업")`, `("logs", "로그")`, `("settings", "설정")`; remove emoji labels per rebrand if already done.

- [ ] **Step 5: `main_window._setup_tabs`** — stack only `work`, `logs`, `settings`; `_switch_tab("work")`; keep `_get_scan_tab` replaced with `_get_work_tab` / `_get_library_section` for folder wiring (temporary: library section accessor).

- [ ] **Step 6: pytest PASS; commit** `[gui] WorkTab shell and 3-item sidebar`

---

### Task 5: Library section (scan + folder + preview signal)

**Files:**
- Create: `src/gui/views/work/sections/library_section.py`
- Modify: `src/gui/views/work/work_tab.py` — mount real library section
- Modify: `src/gui/views/main_window.py` — `folder_selected` from library; remove scan tab registration

- [ ] **Step 1: Copy `ScanTab` logic** into `LibrarySection(QWidget)`:
  - Keeps `ScanViewModel`, `folder_selected = Signal(Path)`, progress UI, start/stop scan.
  - **Only place** with folder `QFileDialog` button.
  - Emit `folder_selected` on pick (MainWindow connects preview).

- [ ] **Step 2: Summary strip** — bind folder path label to `AppState.scan_folder`; jump buttons call `work_tab.scroll_to_section("library"|"duplicate"|"move")`.

- [ ] **Step 3: `main_window._restore_settings` / `_on_folder_selected`** — use `work_tab.library_section.set_scan_folder` instead of `ScanTab`.

- [ ] **Step 4: Manual smoke** — `python src/main.py`, pick folder, preview + full scan from library section.

- [ ] **Step 5: commit** `[gui] library section replaces scan tab`

---

### Task 6: Duplicate section (groups + evidence)

**Files:**
- Create: `src/gui/views/work/sections/duplicate_section.py`
- Modify: `src/gui/views/work/work_tab.py`

- [ ] **Step 1: Extract `DuplicateTab` handlers** into `DuplicateSection` — same `DuplicateViewModel` deps (`job_manager`, `index_repository`, `log_sink`).

- [ ] **Step 2: Layout order** — action bar → progress → `DuplicateGroupsTableView` (min height 240) → `EvidencePanel`.

- [ ] **Step 3: Wire results**

```python
def _on_results_updated(self) -> None:
    self._groups_view.set_results(self._view_model.results)

def _on_duplicate_completed(self, results: list) -> None:
    # existing batch update + json save
    self._groups_view.set_results(results)
    if results:
        self._work_tab.section("duplicate").set_expanded(True)
```

- [ ] **Step 4: Wire selection**

```python
def _on_group_selected(self, group_id: int) -> None:
    result = self._view_model.get_group_by_id(group_id)
    if result:
        self._evidence_panel.set_group(result)
```

Connect `DuplicateGroupsTableView.group_selected` and/or `DuplicateViewModel.group_selected`.

- [ ] **Step 5: Run existing VM tests**

```bash
pytest tests/gui/view_models/test_duplicate_view_model_jobs.py -v
```

- [ ] **Step 6: commit** `[gui] duplicate section with groups and evidence`

---

### Task 7: Move + quality sections

**Files:**
- Create: `src/gui/views/work/sections/move_section.py`
- Create: `src/gui/views/work/sections/quality_section.py`

- [ ] **Step 1: `MoveSection`** — port `MoveOrganizeTab` but **remove** `browse_btn`; `_folder_edit` read-only bound to `AppState.scan_folder` (refresh on `folder_selected` / store signals). Default section collapsed.

- [ ] **Step 2: `QualitySection`** — single disabled group: integrity/encoding buttons `setEnabled(False)`, tooltips "미구현"; QLabel for small-file "준비 중". Collapsed default.

- [ ] **Step 3: Manual** — expand move, dry-run still shows dialog; no second folder picker on screen.

- [ ] **Step 4: commit** `[gui] move and quality sections`

---

### Task 8: Remove legacy tabs + cleanup imports

**Files:**
- Delete: `src/gui/views/tabs/scan_tab.py`, `duplicate_tab.py`, `move_organize_tab.py`, `integrity_tab.py`, `encoding_tab.py`, `small_file_tab.py`, `stats_tab.py`, `undo_tab.py`
- Modify: `src/gui/views/tabs/__init__.py` (if exports)
- Modify: `src/gui/views/main_window.py` — remove dead imports and `_get_scan_tab` / `_get_settings_tab` helpers (keep settings tab getter)
- Modify: `src/gui/styles/icon_registry.py` — drop unused nav keys or map `work` icon

- [ ] **Step 1: Grep for removed modules**

```bash
rg "scan_tab|duplicate_tab|undo_tab|stats_tab" src tests
```

Fix all references.

- [ ] **Step 2: Delete files**

- [ ] **Step 3: Full gate**

```bash
python scripts/verify_phase_completion.py
```

Expected: all stages PASS.

- [ ] **Step 4: commit** `[gui] remove legacy workflow tabs`

---

### Task 9: WorkViewModel integration + summary strip live data

**Files:**
- Modify: `src/gui/views/work/sections/summary_strip.py`
- Modify: `src/gui/views/work/work_tab.py`

- [ ] **Step 1: Connect `FileDataStore` signals + job events to `WorkViewModel.refresh()` → `summary_strip.update(summary)`**

- [ ] **Step 2: Display mini-metrics**: total files, duplicate groups, saved GB, integrity issues on strip (matches header subset).

- [ ] **Step 3: Test `test_work_view_model` extended** — duplicate_state `ready` when groups > 0.

- [ ] **Step 4: commit** `[gui] live summary strip`

---

### Task 10: Spec status + manual QA checklist

**Files:**
- Modify: `docs/superpowers/specs/2026-05-22-ui-work-hub-ia-design.md` — Status: **approved**
- Modify: `docs/superpowers/README.md` — plan link + spec approved

- [ ] Run manual checklist from spec §4 (all items).
- [ ] Mark spec approved date in header.

---

## Spec coverage (self-review)

| Spec requirement | Task |
|------------------|------|
| Single work screen | 4–7 |
| Sidebar 작업·로그·설정 | 4, 8 |
| Global toolbar | 2 |
| Summary strip + scroll | 4, 5, 9 |
| Move/quality collapsed | 4, 7 |
| Duplicate groups + evidence | 6 |
| Bottom file list unchanged | no stack change to file table |
| Header 4 chips | 1 |
| No undo in sections | 2, 7 |
| Folder pick once | 5, 7 (move read-only) |
| Delete legacy tabs | 8 |
| Dry-run unchanged | 6–7 (port handlers verbatim) |

## Coordination with UI rebrand plan

If [2026-05-22-design-md-ui-rebrand.md](2026-05-22-design-md-ui-rebrand.md) is active in parallel:

- Use `objectName` from DESIGN.md on new sections (`card`, `btnPrimary`, `globalActionToolbar`).
- Do not reintroduce inline hex in `gui/views/work/**`.
- Sidebar width/icons can follow rebrand Task 5 when merged.

## Execution handoff

Plan complete and saved to `docs/superpowers/plans/2026-05-22-ui-work-hub-ia.md`.

**Two execution options:**

1. **Subagent-Driven (recommended)** — fresh subagent per task, review between tasks  
2. **Inline Execution** — run tasks in this session via `executing-plans` with checkpoints  

Which approach do you want?
