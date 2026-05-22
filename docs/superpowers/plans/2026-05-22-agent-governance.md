# Agent Governance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reorganize NovelGuard AI governance: slim AGENTS.md, numbered Cursor rules with two always-on files, and `docs/superpowers/` as the only home for new specs/plans.

**Architecture:** Migrate content from five legacy `.mdc` files into eight numbered rules; delete duplicates; update cross-links in `persona/`, `documents/`, and `docs/README.md`.

**Tech Stack:** Markdown, Cursor `.mdc` rules (YAML frontmatter), no application code changes.

**Spec:** [../specs/2026-05-22-agent-governance-design.md](../specs/2026-05-22-agent-governance-design.md)

---

### Task 1: Superpowers tree and spec

**Files:**
- Create: `docs/superpowers/README.md`, `docs/superpowers/specs/2026-05-22-agent-governance-design.md`, `docs/superpowers/plans/2026-05-22-agent-governance.md`

- [x] Spec and plan written (this file).

### Task 2: Slim AGENTS.md

**Files:**
- Modify: `AGENTS.md`

- [ ] Replace body with constitution: priority, Superpowers table, Persona one-liner, invariants, doc map, verification, security.
- [ ] Remove MCP table, full build table, detailed Persona table, "root.mdc is top" line.
- [ ] Point planning to `docs/superpowers/` not `documents/` for new work.

### Task 3: New Cursor rules

**Files:**
- Create: `.cursor/rules/00-project-core.mdc` through `90-branch-pr-finish.mdc` (use `55-mcp.mdc` not `50-mcp`)
- Delete: `root.mdc`, `persona-dialogue.mdc`, `architecture.mdc`, `cursor-usage.mdc`, `mcp.mdc`

- [ ] Create all eight numbered rules per spec.
- [ ] Delete five legacy rules.

### Task 4: Cross-links and archive notice

**Files:**
- Create: `documents/README.md`
- Modify: `docs/README.md`, `persona/README.md`, `documents/PLAN_TEMPLATE.md`, `documents/CURSOR_MEMO.md`

- [ ] `documents/README.md`: historical only; link to superpowers.
- [ ] `docs/README.md`: link superpowers tree.
- [ ] PLAN_TEMPLATE header: new plans under `docs/superpowers/plans/`.
- [ ] CURSOR_MEMO: 2026-05-22 governance row.

### Task 5: Verification

- [ ] Run: `python scripts/verify_phase_completion.py`
- [ ] Manual: confirm only `00` and `10` have `alwaysApply: true`.

---

**Plan complete.** Inline execution in current session (user approved).
