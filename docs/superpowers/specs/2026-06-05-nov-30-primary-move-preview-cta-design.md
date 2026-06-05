---
title: NOV-30 Resolve primary move preview CTA for Exact-ready rows
status: approved
date: 2026-06-05
linear: NOV-30
parent: NOV-25
branch: ai/NOV-30-primary-move-preview-cta
---

# NOV-30: Resolve primary move preview CTA for Exact-ready rows

## Summary (caveman)

- Add **primary** preview button in `ResolveGridToolbar` row 1 — entry chrome, not footer batch bar only.
- Show when `rowTypeFilter === exact`; **hidden** on near/relation/all (NOV-29 banner covers review-only guidance).
- Reuse existing `onOpenPreview(previewSelection)` → `ApplySubflowDialog` — no new apply flow.
- Eligibility: existing `previewBlockedReason` + `hasExecutableMovePreviewRows` — no rule changes.
- Copy via `previewCtaCopy.ts` helper — allowed KO strings only; optional `Exact N건…` when count > 0.
- Batch bar keeps `batch-preview-open` but **outline** style so toolbar owns primary emphasis.
- E2E: `resolve-preview-primary` → click → `apply-subflow-dialog` visible.

## Goal

Parent NOV-25 requires a **primary** move preview call-to-action at Resolve workspace **entry** when the user is on Exact filter with executable `move_duplicate` rows. Today preview lives only in the bottom `BatchActionBar` (`batch-preview-open`) — easy to miss after scan. This issue adds a prominent entry CTA without changing preview/apply safety guards.

## Non-goals

| Item | Reason |
|------|--------|
| New apply / preview bridge methods | Reuse `get_move_preview` subflow |
| Changing `reviewOnlyBlockedReasonForFilter` rules | Safety regression risk (same as NOV-29) |
| Removing batch bar preview button | Keep regression path; demote visual weight only |
| DetailPanel changes | Row-level guidance already exists |
| i18n framework | Inline KO strings per issue AC |

---

## User-visible behavior

### Primary CTA placement (`ResolveGridToolbar` row 1)

Add a primary-styled button in the top toolbar row, grouped with `resolve-open-finalize` on the right (`ml-auto` flex group):

```
[Resolve & Organize] [Queue] [Groups] …     [이동 계획 미리보기] [최종 검증]
```

`data-testid="resolve-preview-primary"`.

### Visibility matrix

| `rowTypeFilter` | Executable rows in loaded set | Primary CTA |
|-----------------|--------------------------------|-------------|
| `exact` | yes, `previewBlockedReason` undefined | **Enabled**, Exact-oriented label |
| `exact` | no executables | **Disabled**, `title` = existing no-executable reason |
| `exact` | `filteredCount === 0` | **Disabled**, `title` = empty-filter reason |
| `near` / `relation` / `all` | any | **Hidden** (not disabled — avoids duplicate disabled buttons; NOV-29 banner explains) |

### Click behavior

Identical to batch bar:

```tsx
onClick={() => onOpenPreview(previewSelection)}
```

Opens existing `ApplySubflowDialog` with `current_query` selection scope.

### Copy (`previewCtaCopy.ts`)

Allowed button labels (issue AC):

| Condition | Label |
|-----------|-------|
| Default (exact, count unknown or 0) | `이동 계획 미리보기` |
| Exact filter, no count variant | `Exact 중복 이동 계획 미리보기` |
| Exact filter, executable count N > 0 | `Exact N건 이동 계획 미리보기` |

**Count source:** Prefer snapshot `resolve.moveReadyCount` when NOV-27 lands; until then use `countExecutableMovePreviewRows(rows)` on the loaded row set. When partial load warning is active (`loadedCount < filteredCount`), N reflects loaded executables only (same caveat as batch bar partial-load warning).

**Forbidden substrings** (must not appear in any label): `자동 정리 시작`, `중복 파일 처리`, `바로 이동`.

Unit tests assert allowed variants and absence of forbidden phrases.

### Batch bar adjustment

Keep `batch-preview-open` with same enable/disable logic. Change button class from `bg-primary` to **outline** (`border border-outline … hover:bg-hover`) so toolbar CTA is the single primary emphasis. Label may reuse `previewCtaLabel()` for consistency or stay fixed `이동 계획 미리보기` — prefer shared helper.

---

## Architecture

```
ResolveAndOrganizeWorkspace
  ├─ previewBlockedReason (existing)
  ├─ previewSelection (existing)
  ├─ countExecutableMovePreviewRows(rows) → executableCount
  ├─ previewCtaLabel({ filter, executableCount }) → label
  ├─ showPreviewCta = rowTypeFilter === 'exact'
  │
  ├─ ResolveGridToolbar (+ onPreview, showPreviewCta, previewDisabled, previewDisabledReason, previewLabel)
  └─ BatchActionBar (unchanged props; outline styling + optional shared label)
```

### New / modified files

| File | Change |
|------|--------|
| `web/src/features/work/resolve/previewCtaCopy.ts` | **New** — `previewCtaLabel()`, forbidden-pattern guard |
| `web/src/features/work/resolve/previewCtaCopy.test.ts` | **New** — label variants + forbidden absent |
| `web/src/features/work/resolve/previewEligibility.ts` | Add `countExecutableMovePreviewRows(rows)` |
| `web/src/features/work/resolve/previewEligibility.test.ts` | Count helper tests |
| `web/src/features/work/resolve/ResolveGridToolbar.tsx` | Primary CTA button + new props |
| `web/src/features/work/ResolveAndOrganizeWorkspace.tsx` | Wire props from existing eligibility |
| `web/src/features/work/resolve/BatchActionBar.tsx` | Outline style; optional shared label |
| `web/e2e/smoke.spec.ts` | NOV-30 test: resolve tab → primary CTA → dialog |

### Props added to `ResolveGridToolbar`

```tsx
showPreviewCta?: boolean;
onPreview?: () => void;
previewDisabled?: boolean;
previewDisabledReason?: string;
previewLabel?: string;
```

When `showPreviewCta` is false, render no preview button.

---

## Sibling coordination

| Issue | Relationship |
|-------|--------------|
| NOV-29 | Review-only banner in batch area; primary CTA hidden on those filters — no overlap |
| NOV-27 | Soft dep — enhances N count source via snapshot; local count OK until merged |
| NOV-22 | Exact default filter + current_query preview already shipped — this adds entry CTA only |

---

## Acceptance criteria mapping

| AC | Implementation |
|----|----------------|
| CTA visible when Exact + executable | `showPreviewCta && !previewDisabled` |
| Hidden/disabled + reason when blocked | Hidden on review-only filters; disabled + `title` on exact with block reason |
| Opens existing move preview dialog | `onOpenPreview(previewSelection)` |
| Copy does not imply immediate apply | `previewCtaCopy` enforces allowed strings |
| E2E scan → resolve → CTA → dialog | Playwright with `resolve-preview-primary` |

---

## Verification

```bash
cd web && npx vitest run src/features/work/resolve/previewCtaCopy.test.ts src/features/work/resolve/previewEligibility.test.ts
cd web && npm run lint
cd web && npm run test:contracts
cd web && npm run test:e2e -- --grep "NOV-30"
```

---

## Risks

| Risk | Mitigation |
|------|------------|
| Two preview buttons visible on Exact | Toolbar primary + batch outline secondary |
| N count vs loaded rows mismatch | Partial-load warning already in batch bar; document count = loaded executables until NOV-27 |
| E2E click intercepted by grid | Use `.evaluate(click)` like existing `batch-preview-open` tests |

## Approval

- [x] 2026-06-05 — Brainstorm Phase 1 (automation router)
