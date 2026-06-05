---
trigger: linear.labelAdded
phase: backlog-plan
project: NovelGuard
commit: false
---

# Backlog + auto:spec-done -> Grill + Plan

Issue `{{ISSUE_IDENTIFIER}}` only. Reason `{{ROUTE_REASON}}`.

Gate: status Backlog, label `auto:spec-done`, no `auto:plan-done` unless `regenerate plan`.

Do read-only:
1. Load issue/comments. Read latest `## Spec`.
2. Run `/grill-me`; post `## Grill-me verdict`.
3. Blockers: `save_issue(state=Todo, labels+=auto:grill-needs-revision)`, stop.
4. Approved: run `/writing-plans`; post `## Implementation Plan` with tasks, files, tests, risks.
5. One Linear call: `save_issue(state=Todo, labels+=auto:plan-done)`.

No product edits. No commit.
