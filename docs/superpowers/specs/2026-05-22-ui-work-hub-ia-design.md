# UI Work Screen & Information Architecture (Single-Surface)

> Status: **approved** (2026-05-22, brainstorming + plan sign-off)
> Related: [2026-05-22-design-md-ui-rebrand-design.md](2026-05-22-design-md-ui-rebrand-design.md) (visual tokens only)
> Follow-on: [2026-05-22-workflow-pipeline-ui-design.md](2026-05-22-workflow-pipeline-ui-design.md) (rev. 3 step pipeline — after this spec ships)
> Supersedes: hub-first + multi-tab workspaces (rev. 1)

## Problem

- Ten sidebar destinations scatter one library workflow (scan → duplicate → move → quality).
- Duplicate actions and folder pickers repeat across tabs; **built** components (`DuplicateGroupsTableView`, `EvidencePanel`) are not mounted in UI.
- Header shows eight stats while a separate Stats tab duplicates summaries.
- Placeholder tabs appear as first-class nav though actions are unwired or disabled.
- Preview scan (MainWindow) vs full scan (ScanTab) is invisible to users.

## Goals

1. **Single work screen:** scan, duplicate review, move/organize, and (future) quality on **one scrollable surface** — no tab-hopping for the main pipeline (user rev. 2).
2. **Minimal navigation:** sidebar **작업 · 로그 · 설정** only; drop Scan / Duplicate / Move / Stats / Small File / Quality / Undo tabs.
3. **Global Undo/Redo toolbar** under header (rev. 2.1) — visible on all main pages; shortcuts Ctrl+Z / Ctrl+Y.
4. **Summary strip** on work screen: compact status + **scroll-to-section** jumps.
5. **Collapsible sections** — **move** and **quality** collapsed by default (confirmed).
6. **Wire duplicate UI** (`DuplicateGroupsTableView`, `EvidencePanel`) inside the duplicate section.
7. Keep **global file list** fixed at bottom (unchanged).
8. **Header** four chips only.
9. Preserve **dry-run + user approval** for destructive work.

## Non-goals

- Changing duplicate-detection algorithms, keeper policy, or move use-case behavior.
- Context-swapping bottom panel.
- Implementing small-file / integrity / encoding logic (UI placeholders only).
- Implementing undo stack / redo engine (toolbar shell only in v1; see §1).

## User decisions (brainstorming + rev. 2)

| Topic | Choice |
|-------|--------|
| Usage | D — rotate scan, duplicate, move, quality |
| Hub model | A — dashboard affordances (rev. 2: **summary strip**, not separate tabs) |
| Bottom panel | A — always global file list |
| IA approach | **Rev. 2 — Single work screen + minimal sidebar** (tabs reduced maximally) |
| Move / quality default | **Collapsed** (confirmed) |
| Undo / Redo | **Global toolbar** under header (rev. 2.1) |

---

## §1 Navigation & layout

### Sidebar (v1) — three destinations

```
작업                  ← WorkTab (default)
────────────────
로그
설정
```

| Removed from sidebar | Handling |
|----------------------|----------|
| 스캔 · 중복 · 이동 · 무결성 · 인코딩 | Sections inside **WorkTab** |
| 작은 파일 | One-line “준비 중” in 품질 section |
| 통계 | Header + summary strip |
| Undo (standalone tab) | **Global toolbar** (see below); `undo_tab.py` deleted |

`MainWindow` `QStackedWidget` entries after migration: **`work`**, **`logs`**, **`settings`** only (3).

### Shell

```
[ Header — 4 chips ]
[ GlobalActionToolbar — Undo · Redo · (stretch) · optional history ▼ ]
[ Sidebar | WorkTab | LogsTab | SettingsTab ]  ← stack, default work
[ FileListTable — always visible ]
```

Toolbar is **global** (same row visible for 작업 / 로그 / 설정) so undo applies after destructive actions regardless of stack page.

### GlobalActionToolbar (new component)

| Control | objectName | v1 behavior |
|---------|------------|-------------|
| Undo | `toolbarUndo` | `QAction` + icon (`SP_ArrowBack` or SVG); **disabled** until undo stack port exists |
| Redo | `toolbarRedo` | `SP_ArrowForward`; disabled until stack wired |
| (future) History | `toolbarHistoryMenu` | Optional `QToolButton` menu listing last N operations — **v1.1**, not required for IA milestone |

- Shortcuts: **Ctrl+Z** (undo), **Ctrl+Y** / **Ctrl+Shift+Z** (redo) registered on `MainWindow`.
- Tooltips: Korean primary label + “미구현” suffix in v1 (matches current `UndoTab` honesty).
- Styling: `surface-elevated` bar, `btnSecondary` / flat tool buttons per `DESIGN.md`; height ~40px, horizontal padding `spacing.md`.
- Wiring target (future): `application` undo port or move-operation journal — **out of scope** for IA phase; toolbar is UI shell only in v1.

Do **not** duplicate undo buttons inside work sections (single global entry point).

### WorkTab — single scroll surface

One `QScrollArea` containing ordered **sections** (`QGroupBox` or custom `WorkSection` with chevron collapse):

| Order | Section ID | Default state | Contents (from existing tabs) |
|-------|------------|---------------|-------------------------------|
| 0 | `summary` | Always visible | Folder path, 4 mini-metrics, jump buttons → scroll to section |
| 1 | `library` | **Expanded** | Folder pick, preview status, full scan start/stop, read-only path |
| 2 | `duplicate` | Expanded when groups > 0 else collapsed | Detect, Dry Run, apply; `DuplicateGroupsTableView`; `EvidencePanel` |
| 3 | `move` | **Collapsed** | MoveOrganize controls (target folder, dry run, run) |
| 4 | `quality` | **Collapsed**, mostly disabled | Integrity + encoding stubs; small-file “준비 중” line |

**Scroll-to-section:** summary strip buttons call `WorkTab.scroll_to_section(section_id)` (ensureWidgetVisible).

**No `card_open_requested → switch_tab`** for workflow steps; only `logs` / `settings` leave the work surface.

### Section height rules

- `duplicate` section: `DuplicateGroupsTableView` min height **240px**; evidence panel below (collapsible if needed).
- Long content scrolls inside WorkTab, not the main window.

### Header (8 → 4)

| Keep | Drop |
|------|------|
| 총 파일 | 처리 완료, 총 용량, 중복 파일 수, 작은 파일 수 |
| 중복 그룹 | (detail in summary strip + duplicate section) |
| 절감 용량 | |
| 이슈 파일 | |

Shared stats helper used by `HeaderWidget` and `WorkViewModel` (summary strip).

---

## §2 Data, ViewModels, action ownership

### `WorkTab` composition

- Owns or holds references to existing ViewModels (no merge into one god VM):
  - `ScanViewModel`
  - `DuplicateViewModel`
  - Move organize: existing use case wiring from `MoveOrganizeTab`
- New: `WorkViewModel` — summary strip snapshot only (same DTOs as rev. 1 hub cards, renamed conceptually to **section summaries**).

```python
@dataclass
class WorkSummary:
    folder_path: str | None
    total_files: int
    duplicate_groups: int
    saved_gb: float
    integrity_issues: int
    library_state: Literal["idle", "previewing", "scanning", "ready"]
    duplicate_state: Literal["idle", "running", "ready", "empty"]
```

### Action ownership (single screen)

| Action | Location |
|--------|----------|
| Folder pick | `library` section only |
| Preview scan | `library` section + MainWindow `PreviewWorker` |
| Full scan start/stop | `library` section |
| Duplicate detect / Dry Run / apply | `duplicate` section only |
| Move dry run / run | `move` section only |
| Settings (extensions, subdirs) | `settings` tab; link in `library` section |
| Undo / Redo | `GlobalActionToolbar` only |

### Preview vs full scan

- `library` section shows labeled rows: **빠른 미리보기** / **전체 스캔** with live status text.

### Layer rules

- Section widgets live under `gui/views/work/sections/` (new package).
- ViewModels unchanged in `gui/view_models/`; sections subscribe to same signals as old tabs.
- `application` use cases invoked only through existing VMs / tab logic moved verbatim.

### Deprecation

| File | Fate |
|------|------|
| `scan_tab.py`, `duplicate_tab.py`, `move_organize_tab.py` | Logic extracted to sections; files **deleted** after parity |
| `integrity_tab.py`, `encoding_tab.py`, `small_file_tab.py` | Replaced by `quality_section.py`; delete stubs |
| `stats_tab.py`, `undo_tab.py` | Remove; undo/redo → `global_action_toolbar.py` |
| `hub_tab.py` | **Not created**; `work_tab.py` instead |

`AppState.current_tab` default: `"work"`.

---

## §3 Migration phases

### Phase 1 — Work shell + sidebar

- Add `gui/views/work/work_tab.py`, `work_tab.py` registers as `work` in stack.
- Sidebar: 작업 / 로그 / 설정 only.
- `main_window.py`: default `_switch_tab("work")`; remove old tab registrations from stack (or feature-flag behind single work tab first).

### Phase 2 — Library section

- `sections/library_section.py` ← extract from `ScanTab` (folder, scan, progress).
- MainWindow `folder_selected` / preview from library section.
- Delete folder UI from any other section.

### Phase 3 — Duplicate section

- `sections/duplicate_section.py` ← `DuplicateTab` actions + progress.
- Mount `DuplicateGroupsTableView`, `EvidencePanel`; wire `set_results` / selection.
- Auto-expand `duplicate` section on `duplicate_completed` when groups > 0.

### Phase 4 — Move + quality sections

- `sections/move_section.py` ← `MoveOrganizeTab` (collapsed default).
- `sections/quality_section.py` ← disabled integrity/encoding + small-file notice.

### Phase 5 — Global toolbar + header

- Add `gui/views/components/global_action_toolbar.py`; mount in `main_window.py` under header.
- Register Ctrl+Z / Ctrl+Y actions (disabled handlers OK in v1).
- `header.py`: four chips; shared stats helper.
- Remove `stats_tab`, `undo_tab` from stack and repo when tests updated.

### Phase 6 — Delete legacy tabs + polish

- Remove deprecated tab modules; update `tests/gui` imports.
- Summary strip jump buttons; `DESIGN.md` tokens on sections.
- Manual + `verify_phase_completion.py`.

Rebrand spec may run in parallel; section `objectName`s align with `card`, `btnPrimary`, etc.

---

## §4 Verification, risks, success criteria

### Tests

| Area | Test |
|------|------|
| `WorkViewModel` | Summary states from mocked store/job |
| `WorkTab` | Section expand/collapse; scroll_to_section smoke |
| Duplicate section | Results → table; selection → evidence |
| Regression | `python scripts/verify_phase_completion.py` |

### Manual checklist

- [ ] App opens on **작업**; scan → duplicate → dry-run doable **without changing sidebar item**.
- [ ] Summary strip jumps scroll to library / duplicate / move sections.
- [ ] Folder pick appears once (library section).
- [ ] Groups + evidence visible after detect; file list still at bottom.
- [ ] Move section works when expanded; quality disabled with tooltips.
- [ ] Undo/Redo visible on toolbar (disabled OK v1); shortcuts registered.
- [ ] Sidebar: 작업 / 로그 / 설정 only.
- [ ] Header shows four chips.

### Risks

| Risk | Mitigation |
|------|------------|
| Very long scroll page | Collapsed move/quality; duplicate auto-expand only when needed |
| Extracting tabs breaks signals | Move code mechanically; keep ViewModels; run existing VM tests |
| Undo harder to find | Standard toolbar placement + Ctrl+Z; tooltip explains scope when wired |
| Table too small | Min height + stretch factor inside duplicate section |

### Success criteria

- **≤3** stack destinations (`work`, `logs`, `settings`).
- Full cleanup pipeline on **one work screen** without workflow tabs.
- No duplicate folder buttons.
- Groups + evidence wired; destructive flows unchanged.
- Verification gate green.

---

## Architecture diagram (rev. 2)

```text
[ Header ]  [ GlobalActionToolbar: Undo | Redo ]
┌──────────────────────────────────────────────────────────┐
│ WorkTab (single QScrollArea)                             │
│  [ summary strip — jump links ]                          │
│  ┌ library section ──── ScanViewModel                   │
│  ┌ duplicate section ─ DuplicateViewModel + Groups/Evidence│
│  ┌ move section (collapsed) ─ MoveOrganize use case      │
│  └ quality section (collapsed, disabled)               │
└───────────────────────────┬──────────────────────────────┘
                            │
                   ┌────────▼────────┐
                   │ MainWindow      │◄── PreviewWorker
                   │ stack: work|logs|settings
                   └────────┬────────┘
                            │
                   ┌────────▼────────┐
                   │ FileDataStore   │
                   └────────┬────────┘
                   ┌────────▼────────┐
                   │ FileListTable   │
                   └─────────────────┘
```

## References

- [docs/current_architecture.md](../../current_architecture.md)
- [DESIGN.md](../../../DESIGN.md)
- [persona/gina-gui.md](../../../persona/gina-gui.md)
- Legacy tabs to extract: `scan_tab.py`, `duplicate_tab.py`, `move_organize_tab.py`
