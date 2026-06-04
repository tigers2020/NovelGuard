---
id: "pr-50-2026-06-04"
status: "review"
priority: "high"
assignee: null
epic: null
dueDate: null
created: "2026-06-04T10:43:11.000Z"
modified: "2026-06-04T20:00:00.000Z"
completedAt: null
labels: []
order: "a0"
---
# PR-50 — Relation detection v2

## Review

**Scope:** Relation v2 core merged via PR #26; follow-up on `feat/pr50-relation-v2` (GitHub PR #27).

| Command | Result |
|---------|--------|
| `pytest tests/test_bridge_contract.py -k relation` | 13 passed, 1 skipped (prior run) |
| `cd web && npm run lint` | PASS (prior run) |
| `cd web && npm run test:contracts` | 88 passed (prior run) |
| `python scripts/verify_phase_completion.py` | Re-run before merge |

**Next:** Merge PR #27 → move card to **done** → advance `current_query` to PR-51.

| Field | Value |
|-------|-------|
| **Track** | 007 |
| **Spec** | [032](../../../docs/superpowers/specs/032-2026-06-03-domain-relation-v2-design.md) |
| **Plan** | [050](../../../docs/superpowers/plans/050-2026-06-03-domain-relation-pr50-relation-v2.md) |
| **Branch** | `feat/pr50-relation-v2` |
| **PR** | #27 (open); #26 merged |
