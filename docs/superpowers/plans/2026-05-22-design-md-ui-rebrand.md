# DESIGN.md UI Rebrand Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Adopt `@google/design.md` as the design source of truth and rebrand the PySide6 GUI to Calm SaaS dark-default + light toggle with Pretendard, slim collapsible sidebar, and token-driven QSS.

**Architecture:** Root `DESIGN.md` → `scripts/sync_design_tokens.py` generates `src/gui/styles/tokens/*.py`; `theme_registry` composes modular QSS; views use `objectName` only (no inline hex). Theme persisted via `QSettings` key `ui/theme`.

**Tech Stack:** Python 3.12, PySide6, `@google/design.md` CLI (npm), Pretendard OTF (optional bundle under `src/gui/resources/fonts/`).

**Spec:** [../specs/2026-05-22-design-md-ui-rebrand-design.md](../specs/2026-05-22-design-md-ui-rebrand-design.md)

---

### Task 1: Root `DESIGN.md` and lint gate

**Files:**
- Create: `DESIGN.md` (repo root)
- Modify: `package.json` (add script `"design:lint"`)

- [x] **Step 1:** Create `DESIGN.md` with YAML front matter (`version: alpha`, `name: NovelGuard`, dark `colors`, `typography`, `rounded`, `spacing`, `components`) and markdown sections Overview → Do's and Don'ts per spec.
- [ ] **Step 2:** Document `colors-light` map in Colors prose (parallel keys to dark).
- [ ] **Step 3:** Run lint:

```bash
npx @google/design.md lint DESIGN.md
```

Expected: exit 0, `summary.errors` = 0.

---

### Task 2: Token sync script and generated modules

**Files:**
- Create: `scripts/sync_design_tokens.py`
- Create: `src/gui/styles/tokens/__init__.py`
- Create: `src/gui/styles/tokens/colors_dark.py` (GENERATED header)
- Create: `src/gui/styles/tokens/colors_light.py` (GENERATED header)
- Create: `tests/unit/gui/test_sync_design_tokens.py`

- [ ] **Step 1: Write failing test**

```python
# tests/unit/gui/test_sync_design_tokens.py
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_design_md_exists() -> None:
    assert (REPO_ROOT / "DESIGN.md").is_file()


def test_generated_dark_primary_matches_design() -> None:
    from gui.styles.tokens.colors_dark import PRIMARY

    assert PRIMARY == "#BB86FC"
```

- [ ] **Step 2:** Run `pytest tests/unit/gui/test_sync_design_tokens.py -v` — expect FAIL (import).

- [ ] **Step 3:** Implement `scripts/sync_design_tokens.py`:
  - Parse first YAML front matter from `DESIGN.md` via `yaml.safe_load`.
  - Parse `colors-light:` block (second yaml fence or inline map in front matter per spec).
  - Emit `colors_dark.py` / `colors_light.py` with UPPER_SNAKE aliases mapping spec names (`background` → `BG_BODY`, etc.).
  - CLI: `python scripts/sync_design_tokens.py` (write), `--check` (diff exit 1 if stale).

- [ ] **Step 4:** Run sync then pytest — PASS.

---

### Task 3: Theme registry, fonts, app wiring

**Files:**
- Create: `src/gui/styles/theme_mode.py` (`ThemeMode` enum: `DARK`, `LIGHT`)
- Create: `src/gui/styles/theme_registry.py`
- Create: `src/gui/styles/fonts.py`
- Create: `src/gui/styles/qss/__init__.py`, `base.py`, `sidebar.py`, `header.py`, `controls.py`
- Modify: `src/app/settings/constants.py` — add `SETTINGS_KEY_UI_THEME = "ui/theme"`
- Modify: `src/app/main.py` — `apply_theme(app, load_theme_mode())`
- Modify: `src/gui/views/main_window.py` — remove direct `get_dark_theme_stylesheet()`

- [ ] **Step 1: Test**

```python
def test_theme_registry_dark_contains_primary() -> None:
    from gui.styles.theme_mode import ThemeMode
    from gui.styles.theme_registry import get_stylesheet

    qss = get_stylesheet(ThemeMode.DARK)
    assert "#BB86FC" in qss
    assert "qlineargradient" not in qss  # no legacy header gradient
```

- [ ] **Step 2:** Implement `get_stylesheet(mode)` assembling qss modules using token imports.
- [ ] **Step 3:** `fonts.py` — try load `src/gui/resources/fonts/PretendardVariable.ttf`; on failure use `"Noto Sans KR", "Segoe UI", sans-serif`.
- [ ] **Step 4:** Wire `main.py`; pytest PASS.

---

### Task 4: Modular QSS (replace `dark_theme.py`)

**Files:**
- Modify: `src/gui/styles/dark_theme.py` — deprecate: thin wrapper calling `theme_registry` for backward compat OR delete after call sites migrated
- Migrate selectors from existing `dark_theme.py` into `qss/controls.py` (buttons, inputs, tables, groupbox, scrollbar, progress)

- [ ] Port `navItem` checked state to left-border accent + `hover` (no gradient).
- [ ] Port `QWidget#header` to flat `surface-elevated`.
- [ ] Map legacy `colors.py` usages: re-export from `tokens/colors_dark` in `colors.py` for gradual migration or replace imports project-wide.

---

### Task 5: Sidebar rebrand

**Files:**
- Modify: `src/gui/views/components/sidebar.py`
- Create: `src/gui/resources/icons/nav/*.svg` (minimal 16px stroke icons) OR `src/gui/styles/icon_registry.py` using `QStyle.StandardPixmap` until SVGs land
- Modify: `src/gui/styles/qss/sidebar.py` — `navSection`, `navSectionToggle`, `navItem`, `navItem:checked`

- [ ] Width `228`; sections 「메인 작업」「도구」「시스템」— rename 「관리」→「시스템」.
- [ ] Collapsible: `QToolButton` chevron toggles `QWidget` visibility for section body.
- [ ] Remove emoji; `QPushButton` text = label only; icon from `QIcon`.
- [ ] Manual: click all nav items, signals unchanged.

---

### Task 6: Header rebrand

**Files:**
- Modify: `src/gui/views/components/header.py`
- Modify: `src/gui/styles/qss/header.py`

- [ ] Remove emoji icon; flat header bar.
- [ ] Stats as compact chips (`statChip`, `statLabel`, `statValue` objectNames).

---

### Task 7: Settings — theme toggle

**Files:**
- Modify: `src/gui/views/tabs/settings_tab.py`
- Create: `src/gui/styles/theme_apply.py` — `apply_theme_to_app(mode: ThemeMode) -> None`

- [ ] New QGroupBox 「모양」with `QComboBox` dark/light.
- [ ] Load/save `SETTINGS_KEY_UI_THEME`; on change call `apply_theme_to_app`.
- [ ] Test: `tests/unit/gui/test_ui_theme_settings.py` — mock QSettings round-trip.

---

### Task 8: Remove inline hex from views

**Files:**
- Modify: `src/gui/views/tabs/*.py`, `src/gui/views/components/evidence_panel.py`, `src/gui/views/tabs/base_tab.py`
- Modify: `src/gui/styles/qss/controls.py` — add `#placeholder`, `#progressInfo`, `#statCard` rules

- [ ] Grep: `rg '#[0-9A-Fa-f]{3,8}' src/gui/views` → 0 matches.
- [ ] Replace with `objectName` + QSS or `ThemeColors` helper from tokens.

---

### Task 9: Status / table semantic colors

**Files:**
- Modify: `DESIGN.md` — add `status-duplicate`, `status-small`, etc.
- Modify: `sync_design_tokens.py` + `file_list_constants.py` / table delegates if needed

- [ ] Map existing `TYPE_*` in `colors.py` to new status tokens; run sync.

---

### Task 10: Pretendard asset (optional but recommended)

**Files:**
- Create: `src/gui/resources/fonts/README.md` (download instructions + OFL license link)
- Optionally: `PretendardVariable.ttf` (user-added; gitignore if large)

- [ ] Document in `DESIGN.md` Typography section.
- [ ] Do not fail CI if font file absent (fallback fonts).

---

### Task 11: Verification and docs

**Files:**
- Modify: `docs/superpowers/README.md` (plan link)
- Modify: `scripts/verify_phase_completion.py` OR document manual `design:lint` in AGENTS (optional step)

- [ ] `npx @google/design.md lint DESIGN.md`
- [ ] `python scripts/sync_design_tokens.py --check`
- [ ] `python scripts/verify_phase_completion.py`
- [ ] Manual smoke: `python src/main.py` — theme toggle, all tabs.

---

## Spec coverage checklist

| Spec requirement | Task |
|------------------|------|
| Root DESIGN.md + lint | 1 |
| sync pipeline | 2 |
| theme_registry dark/light | 3, 7 |
| Modular QSS | 4 |
| Sidebar 228 collapsible | 5 |
| Flat header | 6 |
| No inline hex | 8 |
| Pretendard | 3, 10 |
| QSettings ui/theme | 7 |
| Selection narrow rule | 4, 5 |
| Business flows unchanged | (no task — verify manual) |

---

**Plan complete.** Inline execution completed 2026-05-22 (Tasks 1–9 core; Pretendard bundle optional per `src/gui/resources/fonts/README.md`).

### Completion notes

- `DESIGN.md` at repo root; `npm run design:lint` passes.
- Token sync: `python scripts/sync_design_tokens.py` / `--check`.
- Theme: dark default, light via 설정 → 모양.
- Verification: `python scripts/verify_phase_completion.py` — 139 passed, ruff/mypy/black pass.
