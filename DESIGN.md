---
version: alpha
name: NovelGuard
description: Calm SaaS desktop UI for text novel library cleanup and duplicate management
colors:
  background: "#121212"
  surface: "#1E1E1E"
  surface-elevated: "#242424"
  on-surface: "#EAEAEA"
  on-surface-variant: "#BDBDBD"
  muted: "#8A8A8A"
  primary: "#BB86FC"
  secondary: "#81D4FA"
  selection: "#3700B3"
  outline: "#2C2C2C"
  hover: "#2A2A2A"
  error: "#CF6679"
  success: "#80CBC4"
  status-duplicate-fg: "#BB86FC"
  status-duplicate-bg: "#2D2640"
  status-small-fg: "#81D4FA"
  status-small-bg: "#1A2A33"
  status-encoding-fg: "#CF6679"
  status-encoding-bg: "#331F24"
  status-integrity-fg: "#80CBC4"
  status-integrity-bg: "#1A332F"
colors-light:
  background: "#FAFAFA"
  surface: "#FFFFFF"
  surface-elevated: "#F5F5F5"
  on-surface: "#1C1B1F"
  on-surface-variant: "#49454F"
  muted: "#79747E"
  primary: "#6750A4"
  secondary: "#0288D1"
  selection: "#E8DEF8"
  outline: "#E0E0E0"
  hover: "#F0F0F0"
  error: "#B3261E"
  success: "#00695C"
typography:
  display:
    fontFamily: Pretendard
    fontSize: 24px
    fontWeight: 600
    lineHeight: 1.2
  title:
    fontFamily: Pretendard
    fontSize: 20px
    fontWeight: 600
    lineHeight: 1.3
  body-md:
    fontFamily: Pretendard
    fontSize: 14px
    fontWeight: 400
    lineHeight: 1.5
  label-sm:
    fontFamily: Pretendard
    fontSize: 12px
    fontWeight: 500
    lineHeight: 1.4
  mono-sm:
    fontFamily: Consolas
    fontSize: 12px
    fontWeight: 400
    lineHeight: 1.4
rounded:
  sm: 6px
  md: 12px
  lg: 16px
spacing:
  sm: 8px
  md: 16px
  lg: 24px
components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "#121212"
    rounded: "{rounded.sm}"
    padding: 12px
  button-secondary:
    backgroundColor: transparent
    textColor: "{colors.on-surface}"
    rounded: "{rounded.sm}"
    padding: 12px
  nav-item-active:
    backgroundColor: "{colors.hover}"
    textColor: "{colors.primary}"
    rounded: "{rounded.sm}"
    padding: 12px
  card:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.on-surface}"
    rounded: "{rounded.md}"
    padding: 24px
---

## Overview

NovelGuard helps users scan, detect duplicates, preview cleanup, and organize text novel files safely. The UI follows a **Calm SaaS** posture: clear hierarchy, card-based surfaces, medium information density, and restrained accent usage. Dark mode is the default for long sessions with lists and tables; light mode is available for bright environments. Avoid pure black backgrounds and full-width saturated selection fills.

## Colors

Dark palette (default):

- **Background (#121212):** App shell; reduces glare versus #000000.
- **Surface (#1E1E1E):** Sidebar, cards, and primary panels.
- **Surface elevated (#242424):** Header bar, modals, and dropdowns.
- **On-surface (#EAEAEA):** Body and table text; prefer over #FFFFFF.
- **Primary (#BB86FC):** Primary buttons, active nav accent, key highlights — use sparingly.
- **Secondary (#81D4FA):** Links and secondary emphasis.
- **Selection (#3700B3):** Narrow focus only (border accent or small chips), not full row fills.

Light palette (`colors-light` in front matter): same roles with Material-aligned light values; selection uses **#E8DEF8** for wider safe areas.

## Typography

**Pretendard** is the primary UI family (bundle under `src/gui/resources/fonts/` when available). Fallback: Noto Sans KR, Segoe UI, sans-serif. **mono-sm** is for logs and file paths. Headlines use `display` and `title`; dense tables use `body-md`; metadata uses `label-sm`.

## Layout

- Main window minimum 1400×800.
- Sidebar **228px**, collapsible sections (메인 작업 / 도구 / 시스템).
- Content area uses `spacing.md` (16px) gutters and `spacing.lg` (24px) section breaks.
- Navigation uses icon + short Korean label; no emoji.

## Elevation & Depth

Elevation is expressed through surface steps, not heavy shadows: `background` → `surface` → `surface-elevated`. Modals and popups use `surface-elevated` with `outline` border. Avoid drop shadows in Qt styles unless required for dialogs.

## Shapes

Corner radii: `rounded.sm` (6px) for buttons and inputs, `rounded.md` (12px) for cards and group boxes, `rounded.lg` (16px) for large panels. Buttons are flat or filled primary — no gradient fills on chrome or navigation.

## Components

- **button-primary:** Filled primary CTA; dark text on #BB86FC for contrast.
- **button-secondary:** Outlined/text secondary actions.
- **nav-item-active:** Hover surface + primary text; optional 4px left border in primary (QSS), not full `#3700B3` row background.
- **card:** Surface background, outline border, md radius.

Tables map result types to `status-*` color tokens for badges and row hints.

## Do's and Don'ts

**Do**

- Use role tokens from this file (or generated Python modules) for all new UI.
- Run `npx @google/design.md lint DESIGN.md` before merging theme changes.
- Persist theme via `ui/theme` in QSettings.

**Don't**

- Hardcode hex colors in `src/gui/views/**`.
- Use #000000 / #FFFFFF for large dark-mode areas.
- Apply #BB86FC or #3700B3 to large table row backgrounds.
- Change dry-run, approval, or destructive cleanup flows when restyling.
