---
trigger: linear.labelAdded
phase: todo-spec
project: NovelGuard
commit: false
---

# Todo + auto:research-done -> Spec

Issue `{{ISSUE_IDENTIFIER}}` only. Reason `{{ROUTE_REASON}}`.

Gate: status Todo, label `auto:research-done`, no `## Spec` unless `regenerate spec`.

Do read-only:
1. Load issue/comments. Read `## Research report`.
2. Run `/brainstorming` only if needed.
3. Post missing `## Brainstorm triage report`.
4. Post `## Spec`: caveman summary, AC, scope, files, risks, verify.
5. One Linear call: `save_issue(state=Backlog, labels+=auto:spec-done)`.

No repo edits. No commit. Stop.
