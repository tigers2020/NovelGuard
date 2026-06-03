@AGENTS.md @.cursor/rules/00-automation-core.mdc @.cursor/rules/10-runner-safety.mdc

You are working in this repository only on branch {{BRANCH}}.

Task:
{{TASK}}

Rules:
- Do not commit unless the job payload sets commit: true.
- Do not modify unrelated files.
- Follow AGENTS.md and .cursor/rules.
- Run the smallest relevant verification.
- If tests fail, report the exact command and cause.

Return:
1. changed files
2. implementation summary
3. tests/commands run with pass/fail
4. risks
5. recommended next step
