# Superpowers workflow (NovelGuard)

1. **Roadmap** (optional orientation) — `roadmap/NNN-YYYY-MM-DD-<area>-<topic>-roadmap.md` — program waves, done vs next; see [roadmap/README.md](./roadmap/README.md)
2. **Spec** — `specs/NNN-YYYY-MM-DD-<kind>-<layer>-<area>-<topic>-design.md` → human approval
3. **Plan** — `plans/NNN-YYYY-MM-DD-<kind>-<layer>-<area>-prNN-<topic>.md` → human approval

**Naming:** directory-local `NNN`; `prNN` plan-only; `risk` in frontmatter (`safe` \| `destructive` \| `breaking`). Full rules: [AGENTS.md § Spec & plan file naming](../../AGENTS.md#spec--plan-file-naming). Pre-format files are grandfathered.
4. **Implement** — `executing-plans` or `subagent-driven-development`; run all plan tasks continuously until final review ([AGENTS.md](../../AGENTS.md) — Plan execution continuity)

**Current program status:** [Master roadmap](./roadmap/000-2026-06-01-novelguard-master-roadmap.md) — PR-0..24 **Done** (packaging merged); PR-25 **Done** on `main` — [spec 013](./specs/013-2026-06-02-shell-filedock-design.md) → [plan 019](./plans/019-2026-06-02-pr25-shell-filedock.md). **Next:** program wave after PR-25 (see master roadmap).

Historical specs and plans from before the full reset were removed with the codebase.
