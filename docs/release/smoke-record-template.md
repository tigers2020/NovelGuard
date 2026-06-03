# Package smoke record (PR-24 + PR-44 UI gate)

Date:
Operator:
Machine:
Windows version:
Python used for packaging:
Node/npm:
Package commit:
Package command: `python scripts/package_windows.py`

## Preconditions

- [ ] Built with `python scripts/package_windows.py` on the same Python that has `pip install -e ".[gui]"` and PyInstaller
- [ ] `dist/NovelGuard/NovelGuard.exe` exists
- [ ] `dist/NovelGuard/build-manifest.json` exists
- [ ] No Vite dev server running on port 5173
- [ ] Smoke uses **fixture library only** — `packaging/fixtures/library/` (never a personal library)

## Automated preflight (PR-44)

- [ ] `python scripts/verify_packaging.py` PASS
- [ ] `python scripts/smoke_packaged_ui.py --require-build` PASS (after package build)

## Smoke Checklist

- [ ] Launch `dist/NovelGuard/NovelGuard.exe`
- [ ] Main window visible
- [ ] Settings → app info shows `buildType=packaged` (and commit/time if stamped)
- [ ] Production bridge active — not mock; no `PRODUCTION_BRIDGE_UNAVAILABLE`
- [ ] Select fixture library folder: `packaging/fixtures/library/`
- [ ] **Scan section (PR-35):** scan completes; summary visible
- [ ] **3-mode tabs (PR-34):** Scan / Resolve / Quality switch without layout break
- [ ] **FileDock (PR-38):** expand dock; cross-link to scan or resolve
- [ ] **Resolve grid (PR-36):** rows load; scroll OK
- [ ] **Finalize dialog (PR-37/41):** open from apply flow or resolve CTA; summary loads
- [ ] **Logs / Settings (PR-40):** routes open; log search returns hits on fixture run
- [ ] Close app cleanly
- [ ] Logs written under `%LOCALAPPDATA%/NovelGuard/logs/`
- [ ] No writes inside `dist/NovelGuard/_internal/` (read-only bundle)

Full matrix: [packaging-smoke-checklist.md](packaging-smoke-checklist.md)

## Destructive ops (optional; fixture only)

If testing finalize/cleanup/move: use **only** `packaging/fixtures/library/`. Do not run destructive flows against real libraries.

- [ ] (Optional) Dry-run preview only on fixture paths
- [ ] (Optional) Confirm outputs land under `<fixture-library>/SAVE/` when applicable

## Result

PASS / FAIL:

Notes:
