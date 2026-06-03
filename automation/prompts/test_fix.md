@AGENTS.md @.cursor/rules/00-automation-core.mdc @.cursor/rules/30-verify-gates.mdc

Fix failing tests or verification for this repository only.

Failure / task:
{{TASK}}

Rules:
- Do not commit unless commit: true in job payload.
- Minimal diff; no unrelated files.
- Re-run the failing command and related checks.
- Report exact commands and output on failure.

Return: changed files, root cause, fixes applied, verification results, risks.
