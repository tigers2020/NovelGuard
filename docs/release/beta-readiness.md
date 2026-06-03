# Beta readiness — platform release gate

Checklist for a **local beta** of NovelGuard after roadmap PR-33..44. Not a public store release.

## Gates (automated)

| Check | Command |
|-------|---------|
| Full phase gate | `python scripts/verify_phase_completion.py` |
| Web E2E (mock) | `cd web && npm run test:e2e` |
| Packaging static | `python scripts/verify_packaging.py` |

## Sample library flows (manual)

Use `packaging/fixtures/library/` or a disposable copy. **Do not** beta-test destructive flows on production libraries.

1. **Scan** — select folder → start scan → summary visible.
2. **Resolve** — review grid; facet **이동 계획**; approve/exclude selection.
3. **Move** — 이동 계획 미리보기 → 확인 → 적용 (fixture only).
4. **Finalize** — 최종 검증 dialog; read blockers/warnings; run only when queue clear.
5. **Quality** — open issues list; repair subflow if needed (fixture).
6. **Logs / Settings** — live logs, artifacts, app info (`buildType` dev vs packaged).
7. **Packaged build** (optional) — [packaging-smoke-checklist.md](packaging-smoke-checklist.md).

## Copy / UX (PR-45)

- Work destructive paths use Korean step labels in apply/finalize dialogs.
- Technical tokens (`libraryRevision`, bridge error codes) stay in logs/diagnostics, not primary buttons.
- Known English in grid column headers may remain where tied to contract field names — track in backlog.

## Out of scope for beta

- Installer, auto-update, code signing, multi-user sync, cloud backup.
- Headless packaged E2E (exe drive).

## Sign-off

| Role | Name | Date | Notes |
|------|------|------|-------|
| Engineering | | | Phase gate green |
| QA / operator | | | Fixture smoke record filed |

Template: [smoke-record-template.md](smoke-record-template.md)
