---
title: Work Layout Pane Hierarchy (Minimal)
status: approved
approved: 2026-06-03
risk: safe
date: 2026-06-03
authors: brainstorm session — Resolve layout / FileDock competition
parent_spec: docs/superpowers/specs/000-2026-06-01-novelguard-ui-overhaul-design.md
related_specs:
  - docs/superpowers/specs/013-2026-06-02-shell-filedock-design.md
  - docs/superpowers/specs/021-2026-06-02-feature-fullstack-shell-ia-reconciliation-design.md
  - docs/superpowers/specs/024-2026-06-02-feature-ui-shell-filedock-global-design.md
parent_roadmap: docs/superpowers/roadmap/003-2026-06-02-platform-release-gate-roadmap.md
plan: docs/superpowers/plans/047-2026-06-03-feature-ui-layout-pane-hierarchy-minimal.md
---

# 029 — Work Layout Pane Hierarchy (Minimal)

## Status

**Approved** (2026-06-03) — brainstorm lock. Scope: **A-minimal** — mode-aware auto-collapse + Resolve compact grid toolbar + 3-pane preserved. No side sheet, no overlay, no bridge changes.

## Scope sentence

Fix **pane proliferation** on the Work route: one **primary table per mode**, `ShellFileDock` as ambient strip (not a second primary on Resolve/Quality). Reclaim vertical space by **auto-collapsing** the dock on Resolve/Quality entry and **moving Resolve page chrome into the grid toolbar** inside the horizontal 3-pane body. **CSS/layout + React composition only.**

## Problem

| Symptom | Cause |
|---------|--------|
| Resolve review grid has almost no row height | Expanded `ShellFileDock` (`shrink-0` + fixed `heightPx`) competes with Work content inside `AppShell` main column |
| File list shows headers + “더 보기” only | Dock expanded with heavy header/toolbar leaving ~0px for table body |
| Layout feels “stacked” and messy | Resolve adds a large **page header block** (title, 4× StatChip, filters, search) **above** the 3-pane region, violating M3 body-in-pane guidance |

Material 3 large-screen guidance: prefer **two- to three-pane horizontal composition**; filters/sort in **body pane**; **do not exceed three panes** ([Applying layout — large/extra-large](https://m3.material.io/foundations/layout/applying-layout/large-extra-large)).

`DESIGN.md` IA: shell **summary strip** + Work-owned primary grid; lists in **master–detail** split (`ResizablePanel` / `DetailPanel`), not a second full table stacked under the workspace.

## Decision summary

| Topic | Lock |
|-------|------|
| Approach | **A-minimal** — no new overlay/sheet surfaces |
| Primary table | **One per Work mode** (see LOCK-LAYOUT-1) |
| ShellFileDock on Resolve/Quality | **Auto-collapse on mode entry**; strip remains visible |
| Resolve structure | **3 horizontal panes only**; chrome → grid toolbar |
| Bridge / query | **No changes** |
| Side sheet / overlay file viewer | **Deferred** |

---

## Locked decisions

### LOCK-LAYOUT-1 — Primary table per mode

```text
Scan     → ShellFileDock / File inventory (expanded allowed)
Resolve  → VirtualizedReviewGrid
Quality  → VirtualizedQualityGrid (issue list)
Move     → Move preview table (Apply subflow)
Finalize → Validation / checklist (Finalize subflow)
```

### LOCK-LAYOUT-2 — ShellFileDock ambient policy

```text
Scan     → expanded allowed (existing scan-open-file-dock, LOCK-38-3)
Resolve  → auto-collapse on mode entry
Quality  → auto-collapse on mode entry
Move     → collapsed (subflow overlay; no expand nudge)
Finalize → collapsed (subflow overlay)
```

Persistence keys unchanged (`novelguard.shellFileDock.v1.*`, LOCK-38-5).

Auto-collapse updates UI state to `expanded: false` and **writes `expanded: false` to persistence**. This **intentionally resets** the previous expanded preference (e.g. Scan expanded → Resolve entry → persistence false). **Per-mode dock persistence is deferred** (follow-up).

**MVP limitation (explicit):** User may still **manually** re-expand the dock on Resolve/Quality via the strip toggle. Re-expansion recreates vertical competition; **preventing manual expand on non-Scan modes is out of MVP scope** (follow-up: LOCK-LAYOUT-2B).

**MVP Scan return behavior:** Returning to Scan after Resolve/Quality does **not** auto-expand the dock; user re-expands manually or uses `scan-open-file-dock`. Accepted for this PR.

### LOCK-LAYOUT-3 — Resolve horizontal panes only

```text
┌────────────┬──────────────────────────────────┬─────────────┐
│ FacetPanel │  ResolveGridToolbar (compact)    │ DetailPanel │
│  ~256px    │  VirtualizedReviewGrid (flex-1)  │  ~360px lg+ │
└────────────┴──────────────────────────────────┴─────────────┘
│ BatchActionBar (sticky footer, full width below 3-pane row)   │
└───────────────────────────────────────────────────────────────┘
```

- **Remove** the current top `shrink-0 border-b p-4` hero block (title, 4-column StatChip grid, separate filter row, full-width search below).
- **Relocate** into `ResolveGridToolbar` sitting **inside** the center column, **above** `VirtualizedReviewGrid`, **below** mobile detail strip (if any).
- Toolbar contents (compact, 1–2 rows max):
  - Mode label + short title (single line, optional)
  - Inline StatChips: Queue, Groups, Conflicts, Approved
  - Type filter pills (`resolve-type-filter` testids preserved)
  - Search input (full width of center column or flex-1)
  - `최종 검증` (`resolve-open-finalize`) as tertiary toolbar action
  - Query error / loading inline (same testids: `resolve-query-error`, `resolve-query-retry`)
- **FacetPanel**, **VirtualizedReviewGrid**, **DetailPanel** behavior unchanged except height gain.
- **BatchActionBar** stays `shrink-0` footer; not moved into toolbar.

### LOCK-LAYOUT-4 — Terminology mapping

| Design name | Current implementation |
|-------------|------------------------|
| ReviewGrid / DuplicateGroupsTableView | `VirtualizedReviewGrid` |
| EvidencePanel | `DetailPanel` |
| Shell ambient strip | `ShellFileDock` collapsed header |

No rename in MVP; mapping is documentation-only unless a follow-up PR renames for clarity.

---

## Implementation outline

### 1. Mode-aware auto-collapse (`App.tsx`)

- Subscribe to `snapshot.work.activeMode` (after bridge refresh / optimistic settle).
- When `activeMode` transitions **into** `resolve` or `quality`:
  - If `fileDockExpanded === true`, set `false` and `persistShellFileDockState({ ...loadShellFileDockState(), expanded: false })`.
- Do **not** auto-expand on Scan entry. After Resolve/Quality collapse, persisted `expanded: false` means Scan opens with dock collapsed until user re-expands.
- `handleRevealFileDock` from Scan remains valid (sets expanded true and persists).

Optional extract: `useShellFileDockModePolicy(activeMode)` in `web/src/components/layout/` for unit test.

### 2. Resolve compact toolbar (`ResolveAndOrganizeWorkspace.tsx`)

- New presentational component: `ResolveGridToolbar.tsx` under `web/src/features/work/resolve/`.
- Parent layout: outer `<main>` keeps `data-testid="resolve-workspace"`; **only** one `flex min-h-0 flex-1` row for 3-pane + BatchActionBar below.
- Ensure center column: `flex min-h-0 flex-1 flex-col` → toolbar `shrink-0` → grid `min-h-0 flex-1`.

### 3. No AppShell structural change

`AppShell.tsx` slot order unchanged (children → fileDock → commandBar). Fix is **policy + Resolve internal chrome**, not new grid rows.

### 4. Quality workspace

No toolbar refactor in MVP. Only dock auto-collapse on Quality entry (same as Resolve).

---

## Out of scope (deferred)

| Item | Notes |
|------|--------|
| Side sheet for full file inventory on Resolve | LOCK-LAYOUT-2 follow-up |
| Overlay / modal file viewer | Deferred |
| Disable dock expand on Resolve/Quality | LOCK-LAYOUT-2B |
| Scan mode dock as flex-primary (height reallocation) | Scan already allows expand; no change |
| Rename DetailPanel → EvidencePanel | Docs only |
| VirtualizedDataGrid generic `toolbar` prop | Use workspace wrapper unless reuse proves necessary |
| Bridge / `queryFileRows` / review query changes | None |
| Per-mode dock persistence | Deferred |
| Conversational/LLM shell, glassmorphism, mobile-first reflow, decorative motion | Non-goals — desktop productivity IA per `DESIGN.md` |

---

## Testing

### Unit / component (Vitest)

- `useShellFileDockModePolicy` or `App` effect: entering `resolve` / `quality` collapses expanded dock and persists `expanded: false`.
- Entering `scan` does not force collapse when already expanded.
- `ResolveGridToolbar` renders preserved `data-testid`s: `resolve-type-filter-*`, `resolve-open-finalize`, `resolve-query-error`.

### Existing gates

- `cd web && npm run lint`
- `cd web && npm run test:contracts` (if layout touches snapshot consumers — unlikely)
- Targeted vitest for new policy helper / Resolve layout smoke
- E2e: Resolve path — dock `data-state="collapsed"` after switching to 검토·정리; `resolve-review-grid` visible with usable height (smoke assertion on grid container bounding box or row visibility)

### Manual

1. Expand file dock on Scan → switch to Resolve → dock collapses, review grid fills space.
2. Resolve: type filters + search work; detail panel selection unchanged.
3. Switch to Quality → dock collapsed; quality grid primary.

---

## Acceptance criteria

- [ ] LOCK-LAYOUT-1..4 implemented as specified
- [ ] Resolve workspace has **no** hero header block above the 3-pane row
- [ ] Auto-collapse on Resolve and Quality mode entry with persistence update (`expanded: false`, resets prior preference)
- [ ] Returning to Scan after Resolve does not auto-expand the dock; accepted MVP behavior
- [ ] All listed `data-testid`s preserved or documented if moved one level
- [ ] No bridge or Python changes
- [ ] Lint + targeted tests pass; e2e Resolve dock state check added or updated

---

## Risks

| Risk | Mitigation |
|------|------------|
| User re-expands dock on Resolve | Document MVP limitation; follow-up LOCK-LAYOUT-2B |
| Scan expanded preference lost after Resolve visit | Intentional MVP; per-mode persistence deferred |
| Toolbar too dense on narrow width | Wrap filters; FacetPanel unchanged; mobile detail sheet unchanged |
| E2e assumed expanded dock on Resolve | Update smoke to expect collapsed after mode switch |

---

## References

- Brainstorm: pane hierarchy vs vertical stacking; M3 two-pane / max-three-pane
- `DESIGN.md` — IA, master–detail, FileDock summary strip
- Spec 013 / 024 — ShellFileDock ownership and LOCK-38 persistence
