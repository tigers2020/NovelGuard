# Agent operating prompt (NovelGuard)

Phases: **0 Intake → 1 Grill-me → 2 Lock → 3 Autonomous loop → 4 Final gate → 5 PR/merge**.

Always-on behavior and which `@.cursor/rules/*.mdc` to attach: **`00-core.mdc`** rules index (only place that lists rule paths).

---

## Canonical — full mission (Phase 1 + instructions for Phase 2)

```text
@AGENTS.md @.cursor/rules/00-core.mdc @.cursor/rules/11-grill-me-hardening.mdc

Full development mission. Grill-me once — do not code yet.

Challenge scope, risks, affected modules, verification gates, stop conditions, numbered task sequence, merge target (commit / PR / merge).

After I approve with "Approved. Scope is locked.", attach @.cursor/rules/21-autonomous-mission-execution.mdc:
- complete all tasks in order
- do not ask "continue?" between tasks
- repair failures from current work; rerun smallest verification
- continue through implementation, verification, commits (if in plan), merge/PR prep

Stop only for true blockers in 00-core (destructive op, secrets, spec contradiction, missing credential, merge conflict, same failure 3x).

MCP if needed: @57-mcp-context7 / @58-mcp-supabase-db / @59-ui-playwright-verification (see 00-core index).
```

---

## Phase 1 — Development mission start (grill-me)

```text
@AGENTS.md @.cursor/rules/11-grill-me-hardening.mdc

Full development mission. Grill-me once — do not code yet.

Challenge:
- scope / out of scope
- affected modules and layer
- risks and destructive operations
- verification gates
- stop conditions
- numbered implementation sequence
- merge target (commit / PR / merge)

After your proposal I will lock scope in a follow-up message.
```

---

## Phase 2 — Scope lock (after you approve)

```text
Approved. Scope is locked.

@.cursor/rules/21-autonomous-mission-execution.mdc

Proceed autonomously until all tasks, verification, commits (if in scope), and PR/merge preparation are complete.

Do not ask between tasks.
Stop only for true blockers in 00-core.

MCP if needed: @.cursor/rules/57-mcp-context7.mdc / @58-mcp-supabase-db.mdc / @59-ui-playwright-verification.mdc
```

Do **not** reply with only "continue" — that can be read as permission for a single task.

---

## Small task (skip grill-me)

```text
@AGENTS.md

Small task: <one sentence scope>.
Skip grill-me, specs, plans, Superpowers, persona.
After edit: <single verification command>.
```

---

## Batch without formal grill-me (scope locked in same message)

```text
@AGENTS.md @.cursor/rules/21-autonomous-mission-execution.mdc

Scope locked in this message: <paste scope>.

Tasks 1–N: <list>

Do not ask between tasks. One line per completed task. Final summary at end.

MCP if needed: @57-mcp-context7 / @58-mcp-supabase-db / @59-ui-playwright-verification
```

---

## UI-only

```text
@AGENTS.md @.cursor/rules/59-ui-playwright-verification.mdc

<scope>
```

---

## Backend / DB

```text
@AGENTS.md @.cursor/rules/58-mcp-supabase-db.mdc

<scope>
Local SQLite: src/infrastructure/sqlite_library_index.py is authoritative.
```
