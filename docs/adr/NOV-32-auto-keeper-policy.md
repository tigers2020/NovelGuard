# ADR: NOV-32 Auto-keeper policy (Resolve batch)

## Status

Accepted (locked for NOV-31 epic)

## Context

Resolve workspace needs a deterministic, user-triggered batch flow: filtered unreviewed file rows → auto keeper → batch approve → move preview (never auto-apply).

## Policy

| Rule | Decision |
| --- | --- |
| Scope | `current_query` + `filters.status: ["unreviewed"]` |
| Row types | exact, near, relation — **file rows only** |
| Keeper sort | 1) max `size_bytes` 2) max `modified_at_ns` 3) max `relative_path` (fallback: max `file_id`) |
| Keeper rows | approve → `proposedAction: keep` |
| Non-keeper rows | approve → `move_duplicate`, `targetFolder: duplicate/` |
| Conflict rows | exclude from batch |
| Cap / chunk | 500 cap (`MAX_REVIEW_MUTATIONS`); chunk 200 (`SELECTION_RESOLVE_ROW_CAP`) |
| Preview | required before filesystem apply |
| Library-wide shortcut | deferred |

## Keeper selection (canonical)

```python
keeper = max(members, key=lambda m: (m.size_bytes, m.modified_at_ns, m.relative_path))
```

Implemented in `src/domain/keeper_selection.py` as `pick_keeper_file_id`.

## Migration notes

| Area | Before | After |
| --- | --- | --- |
| Exact keeper | `(size_bytes, relative_path)` | `(size_bytes, modified_at_ns, relative_path)` |
| Near / relation builders | `min(relative_path)` | policy max tuple |
| Near / relation post-approve non-keeper | `proposedAction: ignore` | `move_duplicate` when approved |
| Preview / apply guards | block all near/relation rows | gate on row `proposedAction` + status |

When size is tied and `modified_at_ns` differs, keeper may change vs legacy exact-only picks — expected.

## Consequences

- Shared `pick_keeper_file_id` is the single source of truth for keeper choice.
- `UpdateReviewDecisionsUseCase` must include near/relation group membership.
- Confirm counts come from server `summarizeAutoSelectKeepers` (client must not sort keepers).
