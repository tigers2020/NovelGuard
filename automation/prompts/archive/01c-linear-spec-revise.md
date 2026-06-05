---
trigger: linear.labelAdded
phase: todo-spec-revision
project: NovelGuard
commit: false
---

# Todo + auto:grill-needs-revision -> Revise Spec

Issue `{{ISSUE_IDENTIFIER}}` only. Reason `{{ROUTE_REASON}}`.

Gate: status Todo, label `auto:grill-needs-revision`.

Do read-only:
1. Load issue/comments.
2. Read latest `## Spec` and `## Grill-me verdict`.
3. Fix spec blockers only; do not create plan.
4. Post `## Spec (revised)` with caveman summary and changed decisions.
5. One Linear call: `save_issue(state=Backlog, labels+=auto:spec-done)`.

No repo edits. No commit. Stop.
