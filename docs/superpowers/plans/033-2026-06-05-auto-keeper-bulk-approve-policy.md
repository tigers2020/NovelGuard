# NOV-32: Auto-keeper + bulk approve policy — Plan

**Spec:** [033](../specs/033-2026-06-05-auto-keeper-bulk-approve-policy.md) · **Status:** Done (2026-06-05) · **Linear:** [NOV-32](https://linear.app/zkaufman/issue/NOV-32)

Policy lock only — no `src/` / `web/` product code in this issue.

## Tasks

- [x] T1 — Create spec file from approved Linear `## Spec` (status `locked`)
- [x] T2 — Cross-ref validation: code deltas match; Linear links in spec footer
- [x] T3 — `python scripts/verify_phase_completion.py` exit 0
- [x] T4 — Sign-off comment on NOV-32; request human reviewer ack

## Self-review (plan vs spec)

| Spec requirement | Task |
|------------------|------|
| Policy table refs NOV-16 | T1 |
| Exact/Near/Relation + conflict excluded | T1 |
| Keeper tie-break documented | T1 |
| Preview-required gate | T1 |
| Reviewer sign-off | T4 |
| Repo spec file | T1 |
| No product code in NOV-32 | Architecture note |
