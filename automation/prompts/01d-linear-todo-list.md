---
trigger: linear.labelAdded
phase: todo-list
project: NovelGuard
commit: false
---

# Todo + auto:plan-done -> Todo List

Issue `{{ISSUE_IDENTIFIER}}` only. Reason `{{ROUTE_REASON}}`.

Gate: status Todo, label `auto:plan-done`, valid `## Spec` and `## Implementation Plan`.

Do:
1. Convert plan into `## Todo list`: checkbox tasks, order, files, verify commands.
2. Do not edit product code.
3. One Linear call: `save_issue(state=In Progress, labels+=auto:todo-list-done)`.

Stop. This triggers `02-linear-in-progress-implement.md`.
