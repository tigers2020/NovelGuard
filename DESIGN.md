---
title: NovelGuard Design System & UX/UI Guidelines
status: active
palette: calm-saas
default_theme: dark
ui_stack: react-tailwind-v4
ui_root: web/
ia_decision: hybrid-mode-resolve-workspace
last_reviewed: 2026-06-01
---

# NovelGuard Design System & UX/UI Guidelines

**Canonical source** for UX/UI principles, design tokens, and React component contracts.

| Layer | Stack | Path (target) |
|-------|--------|----------------|
| **UI** | React + TypeScript + Tailwind CSS v4 | `web/` |
| **Backend** | Python 3.12+ (`src/` layout) | `src/domain`, `application`, `infrastructure` |

Tokens are defined **once** in this file, implemented in `web/src/styles/globals.css` via `@theme`, and consumed in React as Tailwind utilities (`bg-surface`, `text-primary`, …). Do not hardcode hex in components.

**Cursor bridge:** [.cursor/rules/40-web-tailwind.mdc](.cursor/rules/40-web-tailwind.mdc)

---

## How to use this document

| Audience | Use |
|----------|-----|
| GUI (지나) | React layout, IA, states, microcopy, `web/src/components` contracts |
| Frontend | `globals.css` `@theme`, primitives under `components/ui/` |
| Spec / plan authors | P0 IA decision before large UI refactors |

Prefer **Material 3 / Fluent 2 / Carbon** as pattern references — implement with **React + Tailwind primitives**, not full vendor kit imports, unless a spec approves a library.

### External references

| System | Role |
|--------|------|
| [Material Design 3](https://m3.material.io/) | Components, motion, density |
| [Fluent 2](https://fluent2.microsoft.design/) | Desktop web density, focus, a11y |
| [IBM Carbon](https://carbondesignsystem.com/) | Data tables, filters |
| [Apple HIG](https://developer.apple.com/design/human-interface-guidelines) | macOS WebView / Electron shell cues when applicable |

### Cross-cutting rules

| Lens | Application |
|------|-------------|
| Platform | Desktop-first layout; responsive down to tablet width only if spec requires |
| Tokens | All color/spacing/type/radius from `@theme` |
| Components | Shared primitives — no copy-pasted long `className` strings |
| Accessibility | WCAG AA, focus visible, keyboard paths, `aria-*` on icon-only controls |
| States | `empty` · `ready` · `running` · `success` · `warning` · `error` · `disabled` · `awaiting-approval` |
| Microcopy | Korean UI copy; verb labels; status includes next action |

---

## UX foundations

**Morville honeycomb:** prioritize **Useful + Credible** (correct duplicate verdicts) and **Accessible**.

**Product invariant (AGENTS.md):** destructive file ops → **dry-run preview → user approval → apply**. React flows use explicit steps/modals — never a single undifferentiated “실행”.

---

## Frontend layout (target)

```
web/
├── src/
│   ├── styles/globals.css      # @import "tailwindcss" + @theme
│   ├── components/
│   │   ├── ui/                 # Button, Card, Table, Dialog, …
│   │   └── layout/             # AppShell, Sidebar, …
│   ├── features/               # work, duplicates, settings, logs
│   └── app/                    # routes, providers
├── package.json
└── index.html
```

- **Feature components** compose `components/ui` + hooks; they do not define new colors.
- **Data** from Python API / local bridge — no duplicate-detection logic in UI files.

---

## Information architecture (IA)

- **Locked (2026-06-01):** Hybrid **mode-based Work** — Scan · Resolve & Organize · Quality. Spec: [docs/superpowers/specs/2026-06-01-novelguard-ui-overhaul-design.md](docs/superpowers/specs/2026-06-01-novelguard-ui-overhaul-design.md).
- Primary review UI is **Resolve & Organize** (virtualized, query-backed grid) — not a four-card dashboard.
- Wizard / stepper: **subflow only**; progress: **GlobalCommandBar** only.
- File list: shell **summary strip** + full table in Work-owned workspace (not modal sheet as primary UI).

### App shell (React)

```tsx
<AppShell className="grid min-h-screen grid-rows-[auto_1fr_auto] bg-background text-on-surface">
  <AppHeader /> {/* status metrics */}
  <div className="grid grid-cols-[228px_1fr]">
    <AppSidebar />
    <WorkSurface>
      <PrimaryWorkflow />
      <EvidencePanel /> {/* master-detail / drawer */}
      <FileDock />
    </WorkSurface>
  </div>
  <GlobalCommandBar /> {/* single primary progress source */}
</AppShell>
```

**Work route (planned):** `WorkModeTabs`, `ScanWorkspace`, `ResolveAndOrganizeWorkspace` (FacetPanel + VirtualizedReviewGrid + DetailPanel + BatchActionBar), `QualityWorkspace`. Reference mock: `Sample/MockUp/MockUp.jsx`.

---

## Layout rules

- Regions: **Header / Nav / Content / Utility / Status**
- One **primary** progress indicator per view
- Lists, logs, evidence → `ResizablePanel`, `Sheet`, or split master–detail
- Tables: default columns in grid; detail in `<DetailPanel />`

---

## Design tokens → Tailwind v4

Edit tokens here first, then mirror in `web/src/styles/globals.css` `@theme`.

### `globals.css` (authoritative implementation)

```css
@import "tailwindcss";

@theme {
  --color-background: #121212;
  --color-surface: #1e1e1e;
  --color-surface-elevated: #242424;
  --color-on-surface: #eaeaea;
  --color-on-surface-variant: #bdbdbd;
  --color-muted: #8a8a8a;
  --color-primary: #bb86fc;
  --color-secondary: #81d4fa;
  --color-selection: #3700b3;
  --color-outline: #2c2c2c;
  --color-hover: #2a2a2a;
  --color-error: #cf6679;
  --color-success: #80cbc4;

  --color-background-light: #fafafa;
  --color-surface-light: #ffffff;
  --color-primary-light: #6750a4;

  --font-family-sans: "Pretendard", "Noto Sans KR", "Segoe UI", system-ui, sans-serif;
  --font-family-mono: ui-monospace, Consolas, monospace;

  --radius-sm: 6px;
  --radius-md: 12px;
  --radius-lg: 16px;

  --spacing-sm: 8px;
  --spacing-md: 16px;
  --spacing-lg: 24px;
}
```

Usage in JSX: `bg-background`, `bg-surface`, `text-on-surface`, `border-outline`, `rounded-md`, `gap-md` (map custom spacing in `@theme` if needed).

### Colors — dark (default)

| Token | Hex | Tailwind |
|-------|-----|----------|
| background | `#121212` | `bg-background` |
| surface | `#1e1e1e` | `bg-surface` |
| surface-elevated | `#242424` | `bg-surface-elevated` |
| on-surface | `#eaeaea` | `text-on-surface` |
| on-surface-variant | `#bdbdbd` | `text-on-surface-variant` |
| muted | `#8a8a8a` | `text-muted` |
| primary | `#bb86fc` | `bg-primary`, `text-primary` |
| secondary | `#81d4fa` | `text-secondary` |
| error | `#cf6679` | `text-error`, danger accents |
| success | `#80cbc4` | `text-success` |

### Colors — light

| Token | Hex |
|-------|-----|
| background-light | `#fafafa` |
| surface-light | `#ffffff` |
| primary-light | `#6750a4` |

Ship light mode with `class` strategy: `<html class="dark">` default; `dark:` utilities for overrides when both themes exist. Contrast ≥ WCAG AA.

### Typography & spacing

| Token | Value |
|-------|-------|
| sans | Pretendard, Noto Sans KR, Segoe UI, system-ui |
| mono | ui-monospace, Consolas |
| spacing.sm / md / lg | 8 / 16 / 24 px |
| rounded.sm / md / lg | 6 / 12 / 16 px |
| sidebar width | `228px` → `grid-cols-[228px_1fr]` or `w-[228px]` |

---

## React component contract

Implement under `web/src/components/ui/`. Use **`class-variance-authority` (cva)** or equivalent for variants; export typed props.

### Button (`<Button variant="…" />`)

**At most one `variant="primary"` per view.**

| variant | Role | Tailwind sketch |
|---------|------|-----------------|
| `primary` | Core forward action | `bg-primary text-background hover:bg-primary/90` |
| `secondary` | Supporting | `border border-outline bg-surface hover:bg-hover` |
| `neutral` | Cancel, back | `text-on-surface-variant hover:bg-hover` |
| `danger` | Destructive apply | `bg-error/15 text-error border border-error/40` |

```tsx
import { cva, type VariantProps } from "class-variance-authority";

const buttonVariants = cva(
  "inline-flex items-center justify-center rounded-sm px-4 py-2 text-sm font-medium " +
    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary disabled:opacity-50",
  {
    variants: {
      variant: {
        primary: "bg-primary text-background hover:bg-primary/90",
        secondary: "border border-outline bg-surface hover:bg-hover",
        neutral: "text-on-surface-variant hover:bg-hover",
        danger: "border border-error/40 bg-error/15 text-error hover:bg-error/25",
      },
    },
    defaultVariants: { variant: "secondary" },
  },
);
```

- Destructive **apply** still requires preview + confirm dialog — `danger` is not a shortcut.
- `disabled` + `title` or inline text for **why** disabled.

### Layout & data primitives

| Component | File | `data-slot` (tests) | Notes |
|-----------|------|---------------------|--------|
| `Card` | `card.tsx` | `card` | `rounded-md border border-outline bg-surface p-md` |
| `DataTableCard` | `data-table-card.tsx` | `data-table` | Table wrapper + sticky header |
| `StatChip` | `stat-chip.tsx` | `stat-chip` | Metric pill in header |
| `PipelineProgress` | `pipeline-progress.tsx` | `pipeline-progress` | Single primary progress block |
| `FilterChip` | `filter-chip.tsx` | `filter-chip` | Toggle filters for duplicate review |
| `Dialog` | `dialog.tsx` | `dialog` | Confirm / dry-run preview |
| `Sheet` | `sheet.tsx` | `sheet` | Evidence drawer |

Add new primitives to this table **before** use. Prefer composition over new variants.

### Surface states

Expose `data-state` on feature roots for styling and tests:

```tsx
<section data-state={state} className="data-[state=empty]:…">
```

| `data-state` | UI |
|--------------|-----|
| `empty` | Message + primary next action |
| `ready` | Actions enabled |
| `running` | `<PipelineProgress />` + cancel |
| `success` | Summary + next step |
| `warning` | Inline alert, can continue |
| `error` | Cause + recovery + link to logs |
| `disabled` | Reason visible |
| `awaiting-approval` | Preview panel + confirm/cancel |

---

## Interaction & microcopy

| Avoid | Prefer |
|-------|--------|
| `실행` | `중복 파일 이동 적용`, `UTF-8 변환 시작` |
| `Dry Run` | `이동 계획 미리보기` |
| `Apply` | `선택한 이동 적용` |
| `Finalize` | `적용 · 검증` |
| `Copy JSON` | `JSON 복사` |
| `No files` | `아직 스캔된 파일이 없습니다. 폴더를 선택하세요.` |

Dialogs: use `@headlessui/react` or Radix primitives — focus trap, `aria-labelledby`, ESC to close (non-destructive only).

---

## Accessibility

- Focus ring: `focus-visible:ring-2 focus-visible:ring-primary` — never `outline-none` without replacement
- Icon-only: `aria-label` required
- Status: not color-only — add text/icon
- Tables: `<th scope="col">`, sort `aria-sort`, row `aria-selected`

---

## Duplicate & data review UX

- Default columns: name, path, size, mtime, status
- Detail: `Sheet` or right panel — verdict reason, keeper, move targets
- JSON evidence: summary card + `<Collapsible />` raw
- Filters: `FilterChip` — 전체, exact, near, relation, 적용 예정, 경고 있음

---

## Settings UX (target)

- Simple / expert toggle
- Category nav or search (`<SettingsNav />`)
- Save vs live settings labeled
- Active settings as `StatChip` on work surface when they affect a run

---

## Checklist

- [ ] ≤1 `Button variant="primary"` per screen
- [ ] Step + next action visible
- [ ] Single primary progress source
- [ ] Destructive: preview → confirm → apply
- [ ] All `data-state`s implemented
- [ ] Table default vs detail split
- [ ] Dark/light contrast checked
- [ ] Keyboard order logical
- [ ] Korean copy consistent
- [ ] New tokens in `@theme` + this file

### Priority backlog

| Priority | Work |
|----------|------|
| **P0** | IA spec approved → implement per [ui-overhaul spec](docs/superpowers/specs/2026-06-01-novelguard-ui-overhaul-design.md) |
| **P1** | Scaffold `web/` (Vite + React + TS + Tailwind v4) |
| **P1** | `components/ui` primitives: Button, Card, Table, Dialog, PipelineProgress |
| **P2** | Duplicate review master–detail |
| **P2** | File dock column density |
| **P2** | Unified dry-run / confirm dialogs |
| **P3** | Structured logs table |
| **P3** | Settings nav + simple/expert |

---

## Changelog

| Date | Change |
|------|--------|
| 2026-06-01 | Initial guidelines + Calm SaaS tokens; IA P0 open |
| 2026-06-01 | **React + Tailwind v4** as sole UI implementation target; removed Qt/QSS dual contract |
