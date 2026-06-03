# PR-44 — Packaging smoke (post UI overhaul)

**Status:** Done (2026-06-03)  
**Roadmap:** [003 platform release gate](../roadmap/003-2026-06-02-platform-release-gate-roadmap.md)  
**Extends:** [spec 012](../specs/012-2026-06-02-packaging-distribution-design.md) · [plan 018](018-2026-06-02-pr24-packaging-distribution.md)

## Goal

Windows onedir smoke checklist and automated UI marker gates after PR-33..43 shell/work changes.

## Tasks

- [x] `scripts/smoke_packaged_ui.py` — source + optional bundle `data-testid` anchors
- [x] Wire into `verify_packaging.py` (CI) and `package_windows.py` (strict post-build)
- [x] `docs/release/packaging-smoke-checklist.md` — manual matrix
- [x] Update `smoke-record-template.md`, `known-limitations.md`, `packaging-windows.md`
- [x] Roadmap 003 PR-44 → Done

## Verification

```bash
python scripts/verify_packaging.py
python scripts/smoke_packaged_ui.py
# After full package:
python scripts/package_windows.py
```

Manual: [packaging-smoke-checklist.md](../../release/packaging-smoke-checklist.md).
