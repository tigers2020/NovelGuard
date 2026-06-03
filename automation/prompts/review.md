@AGENTS.md @.cursor/rules/10-runner-safety.mdc

Review the current git diff. Do not modify files.

Focus:
- correctness and regression risk
- architecture / layer violations
- missing tests
- unsafe file operations
- scope creep

Return blocking issues first, then suggestions.

Job context: {{TASK}}
