# DESIGN.md UI Rebrand

> Status: approved (2026-05-22, brainstorming sign-off)
> Format: [@google/design.md](https://www.npmjs.com/package/@google/design.md) (alpha) + PySide6 token pipeline

## Problem

- GUI styling is split across `colors.py`, a ~330-line monolithic `dark_theme.py`, and **hardcoded hex** in many tabs (`setStyleSheet("color: #808080")`).
- No machine-readable design source for agents or lint; current palette (indigo gradient, emoji nav) does not match the agreed **Calm SaaS** direction or the user-validated **Material-style dark tokens**.
- `persona/gina-gui.md` requires token-level design references without importing a full web component framework.

## Goals

1. Add repo-root **`DESIGN.md`** that passes `npx @google/design.md lint DESIGN.md` (errors = 0).
2. **Full visual rebrand (scope C):** slim collapsible sidebar with SVG icons, flat header, modular QSS, Pretendard typography.
3. **Theme B:** dark default, light toggle persisted via `QSettings` (`ui/theme`).
4. **Token pipeline (approach 1):** `scripts/sync_design_tokens.py` generates Python color modules and keeps QSS aligned with `DESIGN.md`.
5. Remove inline hex styling from `src/gui/views/**` except generated/token-backed helpers.

## Non-goals

- Changing duplicate-detection, dry-run, or approval **business behavior** (copy and flow unchanged).
- Web UI or Tailwind runtime (export may be used for review only).
- Sidebar **64px icon-only rail** in v1 (228px + section collapse only; rail deferred).
- Bundling Pretendard in git without license file — license must be added under `src/gui/resources/fonts/` before merge.

## Decisions (brainstorming)

| Topic | Choice |
|-------|--------|
| Scope | C — full rebrand |
| Mood | B — Calm SaaS (cards, medium density, soft radius) |
| Theme | B — dark default + light toggle |
| Dark colors | User palette (see below) |
| Navigation | B — 228px sidebar, SVG + short label, collapsible sections |
| Typography | B — Pretendard primary, Noto Sans KR / Segoe UI fallback |
| Implementation | Approach 1 — DESIGN.md + sync script |

## Dark color tokens (normative)

| Token | Hex | Usage |
|-------|-----|--------|
| `background` | `#121212` | App background |
| `surface` | `#1E1E1E` | Cards, sidebar, lists |
| `surface-elevated` | `#242424` | Modals, dropdowns, header bar |
| `on-surface` | `#EAEAEA` | Primary text |
| `on-surface-variant` | `#BDBDBD` | Metadata, labels |
| `muted` | `#8A8A8A` | De-emphasized text |
| `primary` | `#BB86FC` | Primary buttons, key emphasis (limited area) |
| `secondary` | `#81D4FA` | Links, secondary emphasis |
| `selection` | `#3700B3` | **Narrow** selection (see components) |
| `outline` | `#2C2C2C` | Borders, dividers |
| `hover` | `#2A2A2A` | List/button hover |
| `error` | `#CF6679` | Errors, destructive hints |
| `success` | `#80CBC4` | Success states |

### Selection usage rule

Do **not** fill entire table rows or large panels with `#3700B3`. Prefer:

- 4px `border-left: {colors.primary}` + `background: {colors.hover}`, or
- `selection` at ≤20% opacity over `surface`.

This keeps contrast lint warnings manageable and reduces visual fatigue.

## Light color tokens (normative v1)

| Token | Hex | Notes |
|-------|-----|--------|
| `background` | `#FAFAFA` | App background |
| `surface` | `#FFFFFF` | Cards, sidebar |
| `surface-elevated` | `#F5F5F5` | Header, modals |
| `on-surface` | `#1C1B1F` | Primary text |
| `on-surface-variant` | `#49454F` | Metadata |
| `muted` | `#79747E` | De-emphasized |
| `primary` | `#6750A4` | Purple family aligned with dark accent |
| `secondary` | `#0288D1` | Cyan family aligned with `#81D4FA` |
| `selection` | `#E8DEF8` | Wide selection safe on light |
| `outline` | `#E0E0E0` | Borders |
| `hover` | `#F0F0F0` | Hover |
| `error` | `#B3261E` | Errors |
| `success` | `#00695C` | Success |

Light tokens live in the same `DESIGN.md` under a documented naming convention (see **DESIGN.md structure**).

## Typography tokens

| Token | fontFamily | fontSize | fontWeight | lineHeight | Use |
|-------|------------|----------|------------|------------|-----|
| `display` | Pretendard | 24px | 600 | 1.2 | App title in header |
| `title` | Pretendard | 20px | 600 | 1.3 | Page titles |
| `body-md` | Pretendard | 14px | 400 | 1.5 | Default UI |
| `label-sm` | Pretendard | 12px | 500 | 1.4 | Captions, stat labels |
| `mono-sm` | Consolas, monospace | 12px | 400 | 1.4 | Logs, paths |

Load fonts in `src/gui/styles/fonts.py` via `QFontDatabase.addApplicationFont`; set `QApplication` default font to `body-md`.

## Spacing and shape tokens

| Scale | Value |
|-------|-------|
| `spacing.sm` | 8px |
| `spacing.md` | 16px |
| `spacing.lg` | 24px |
| `rounded.sm` | 6px |
| `rounded.md` | 12px |
| `rounded.lg` | 16px |

## DESIGN.md file structure

**Path:** repository root `DESIGN.md`.

- YAML front matter: `version: alpha`, `name: NovelGuard`, dark `colors` + shared `typography`, `rounded`, `spacing`, `components` (dark variants).
- Markdown sections in spec order: Overview → Colors → Typography → Layout → Elevation & Depth → Shapes → Components → Do's and Don'ts.
- Light palette: second YAML block is **not** in the alpha spec; use **suffix keys** in front matter, e.g. `colors-light` map mirroring `colors`, documented in prose under Colors. Linter validates primary `colors` + components; light validated by sync script unit tests.

Component examples (dark):

```yaml
components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "#121212"
    rounded: "{rounded.sm}"
    padding: 12px
  nav-item-active:
    backgroundColor: "{colors.hover}"
    textColor: "{colors.primary}"
  card:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.on-surface}"
    rounded: "{rounded.md}"
```

## Architecture

```
DESIGN.md
    │
    ▼
scripts/sync_design_tokens.py  ──► src/gui/styles/tokens/colors_dark.py
    │                              src/gui/styles/tokens/colors_light.py
    │                              (optional generated QSS fragments)
    ▼
src/gui/styles/theme_registry.py  ──► get_stylesheet(ThemeMode)
src/gui/styles/qss/*.py           ──► modular QSS builders
src/gui/styles/fonts.py           ──► Pretendard load
src/gui/resources/icons/*.svg     ──► nav icons
```

**Dependency rule:** `gui` continues to avoid domain/application imports. Theme mode read/write goes through settings tab + `QSettings` only (no new domain types).

## UI layout changes

### Sidebar (`SidebarWidget`)

- Width: **228px** fixed in v1.
- Remove emoji; use **16–20px SVG** icons with short Korean labels.
- Sections: 「메인 작업」「도구」「시스템」— each collapsible via chevron (`QToolButton` + visibility on child container).
- Active item: left accent bar `{colors.primary}` + `hover` background (not full-width `#3700B3`).

### Header (`HeaderWidget`)

- Remove purple gradient; use `surface-elevated` flat bar.
- Title: `display` typography; stats as compact chips (`label-sm` / `body-md`).
- Remove emoji icon; optional small brand SVG.

### Main window

- Apply theme via `theme_registry.get_stylesheet(mode)` on startup and on change.
- Default mode: **dark**.

### Settings tab

- New group 「모양」: theme `dark` | `light`; persist `ui/theme`; apply immediately.

## Styling rules (Do's and Don'ts)

**Do**

- Use `objectName` hooks documented in QSS modules (`header`, `sidebar`, `navItem`, `card`, etc.).
- Use semantic tokens for result-type colors in tables (duplicate, encoding, etc.) — extend `DESIGN.md` `colors` with `status-*` keys if needed.

**Don't**

- Inline hex in view files (`#808080`, etc.).
- Use `#000000` / `#FFFFFF` for large areas in dark mode.
- Apply `#BB86FC` to large backgrounds (buttons, small accents only).
- Import Material/Qt Material libraries.

## Migration phases

| Phase | Deliverable |
|-------|-------------|
| 1 | `DESIGN.md` + `lint` clean |
| 2 | `sync_design_tokens.py` + `theme_registry` + Pretendard |
| 3 | Sidebar + header restructure |
| 4 | Core QSS modules (buttons, inputs, tables, groupbox, scrollbar) |
| 5 | Tab sweep — remove inline colors |
| 6 | Light theme + settings toggle |
| 7 | `tests/gui/` smoke + `verify_phase_completion.py` |

## Verification

- `npx @google/design.md lint DESIGN.md` — 0 errors (warnings documented if accepted).
- `python scripts/sync_design_tokens.py --check` (to be added) — generated files match `DESIGN.md`.
- `python scripts/verify_phase_completion.py` — full gate green.
- Manual: toggle light/dark; navigate all sidebar entries; confirm no emoji; contrast readable on file tables.

## Risks

| Risk | Mitigation |
|------|------------|
| Pretendard license | Add `LICENSE` / OFL file in fonts dir before merge |
| Many inline styles | Phase 5 grep gate: `ruff` or CI script forbids `#` hex in `src/gui/views` |
| QSS regression | Keep snapshot or minimal `tests/gui/test_theme_registry.py` |
| `@google/design.md` alpha churn | Pin npm version in `package.json`; spec version `alpha` |

## Success criteria

- Root `DESIGN.md` exists and lints with 0 errors.
- Dark UI matches token table above; light toggle works and persists.
- Sidebar 228px, collapsible sections, SVG nav, no emoji.
- No hardcoded hex in `src/gui/views/**/*.py` (except allowlist in sync/generated code).
- Destructive workflows unchanged (dry-run + approval).

## References

- Installed package: `node_modules/@google/design.md`
- Archive note: [P2-2_dark_theme.md](../../archive/refactoring/reports/P2-2_dark_theme.md)
- Persona: [persona/gina-gui.md](../../../persona/gina-gui.md)
