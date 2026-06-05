---
title: NOV-29 Resolve review-only filters inline guidance + tab labels
status: approved
date: 2026-06-05
linear: NOV-29
parent: NOV-25
branch: ai/NOV-29-resolve-review-only-inline-guidance
---

# NOV-29: Resolve review-only filters — inline guidance + tab labels

## Goal

When Resolve row type filter is **Near**, **Relation**, or **All types**, show a persistent **inline guidance banner** in the BatchActionBar area explaining why move preview is disabled and directing users to the **Exact (이동)** tab. Rename type-filter tab labels with Korean role hints. **No change** to preview eligibility or apply safety guards (PR-19/PR-20).

## Non-goals

| Item | Reason |
|------|--------|
| Changing `reviewOnlyBlockedReasonForFilter` disable rules | Safety regression risk |
| Bridge / apply guard changes | Out of scope |
| DetailPanel banner changes | Already has row-level guidance |
| New i18n framework | Inline label strings only |

---

## User-visible behavior

### Type filter tab labels (`ResolveGridToolbar`)

| Filter id | Current label | New label |
|-----------|---------------|-----------|
| `exact` | Exact only | **Exact (이동)** |
| `near` | Near only | **Near (참고)** |
| `relation` | Relation only | **Relation (참고)** |
| `all` | All types | **All types** (unchanged) |

`data-testid` values (`resolve-type-filter-exact`, etc.) stay unchanged so existing E2E selectors remain stable.

### Inline guidance banner (`BatchActionBar`)

| Filter | Banner |
|--------|--------|
| `exact` | Hidden |
| `near` | Visible |
| `relation` | Visible |
| `all` | Visible |

**Placement:** Full-width banner row **above** the existing BatchActionBar counts/actions row (same visual band, border-t container).

**Styling:** Match `DetailPanel` review-only banner:

```tsx
className="rounded-md border border-secondary/40 bg-secondary/10 p-3 text-sm text-on-surface"
role="status"
data-testid="batch-review-only-banner"
```

**Copy source:** New helper `reviewOnlyGuidanceBannerForFilter()` in `previewEligibility.ts` — banner text may be slightly longer than tooltip strings and must explicitly mention switching to **Exact (이동)** for move preview. Tooltip strings from `reviewOnlyBlockedReasonForFilter()` remain unchanged for button `title` attributes.

Proposed banner copy:

| Filter | Banner text |
|--------|-------------|
| `near` | Near 중복은 검토 전용입니다. 이동 미리보기·적용은 **Exact (이동)** 탭에서만 가능합니다. |
| `relation` | Relation 그룹은 검토 전용입니다. 이동 미리보기·적용은 **Exact (이동)** 탭에서만 가능합니다. |
| `all` | 현재 필터에 검토 전용 유형이 포함되어 있습니다. 이동 미리보기는 **Exact (이동)** 탭을 선택하세요. |

(Plain text — no markdown bold in UI.)

### Unchanged behavior

- Preview button `disabled` when `previewBlockedReason` set (includes review-only filters).
- Bulk exclude disabled when `reviewOnlyBlockedReason` set.
- Button `title` tooltips continue using `reviewOnlyBlockedReasonForFilter()` strings.

---

## Architecture

```
ResolveAndOrganizeWorkspace
  rowTypeFilter
    ├─ reviewOnlyBlockedReasonForFilter() → preview/bulk disabled + tooltips
    └─ reviewOnlyGuidanceBannerForFilter() → BatchActionBar.reviewOnlyGuidance

BatchActionBar
  reviewOnlyGuidance?: string
    └─ if set → render batch-review-only-banner above bar row

ResolveGridToolbar
  TYPE_FILTERS labels updated (display only)
```

Display-only path — banner prop does not feed back into eligibility.

---

## Files to change

| File | Change |
|------|--------|
| `web/src/features/work/resolve/previewEligibility.ts` | Add `reviewOnlyGuidanceBannerForFilter()` |
| `web/src/features/work/resolve/previewEligibility.test.ts` | Unit tests for banner strings (near/relation/all → string; exact → undefined) |
| `web/src/features/work/resolve/ResolveGridToolbar.tsx` | Update `TYPE_FILTERS` labels |
| `web/src/features/work/resolve/BatchActionBar.tsx` | Optional `reviewOnlyGuidance` prop; conditional banner |
| `web/src/features/work/resolve/BatchActionBar.test.tsx` | Banner visible when guidance set; absent when undefined |
| `web/src/features/work/ResolveAndOrganizeWorkspace.tsx` | Pass `reviewOnlyGuidance={reviewOnlyGuidanceBannerForFilter(rowTypeFilter)}` |
| `web/e2e/smoke.spec.ts` | NOV-29 E2E: banner on near/all; absent on exact default |

---

## Acceptance criteria (from Linear)

- [ ] Banner visible when row type filter is near, relation, or all; hidden on exact
- [ ] Banner explains read-only nature and directs user to Exact for move preview
- [ ] Preview button still disabled on review-only filters (no apply regression)
- [ ] Tab labels updated in Resolve grid toolbar
- [ ] E2E or unit test asserts banner text on near/relation/all

---

## Verification

```bash
cd web && npm run test -- src/features/work/resolve/previewEligibility.test.ts src/features/work/resolve/BatchActionBar.test.tsx -v
cd web && npm run lint
cd web && npm run test:e2e -- e2e/smoke.spec.ts -g "NOV-29"
```

---

## Risks

| Risk | Mitigation |
|------|------------|
| Accidental eligibility change | Banner prop display-only; no edits to `previewBlockedReason` logic |
| E2E breakage on label rename | Tests use `data-testid`, not label text |
| Copy drift tooltip vs banner | Separate functions; unit tests lock both |

---

## Approval

- [x] 2026-06-05 — Phase 1 automation spec (NOV-29)
