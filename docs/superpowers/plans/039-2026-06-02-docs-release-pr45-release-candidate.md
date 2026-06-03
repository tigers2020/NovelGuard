# PR-45 — Release candidate

**Status:** Done (2026-06-03)  
**Roadmap:** [003 platform release gate](../roadmap/003-2026-06-02-platform-release-gate-roadmap.md)

## Goal

Beta readiness documentation and Korean copy on destructive Work paths (apply/finalize).

## Tasks

- [x] `docs/release/beta-readiness.md` — beta gate + sample flows
- [x] Apply/finalize dialog copy (Korean steps; destructive hint)
- [x] Resolve facet + batch tooltip Korean
- [x] E2E selector update (`이동 계획`)
- [x] CHANGELOG Unreleased — platform gate summary
- [x] Roadmap PR-45 → Done

## Verification

```bash
python scripts/verify_phase_completion.py
cd web && npm run test:e2e
```
