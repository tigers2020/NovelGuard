# PR-24 Package Smoke Record

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

## Smoke Checklist

- [ ] Launch `dist/NovelGuard/NovelGuard.exe`
- [ ] Main window visible
- [ ] Settings → app info shows `buildType=packaged` (and commit/time if stamped)
- [ ] Production bridge active — not mock; no `PRODUCTION_BRIDGE_UNAVAILABLE`
- [ ] Select fixture library folder: `packaging/fixtures/library/`
- [ ] Run scan (completes or shows expected empty/partial state)
- [ ] Open resolve/review workspace
- [ ] Non-destructive navigation works (tabs, back, list scroll)
- [ ] Close app cleanly
- [ ] Logs written under `%LOCALAPPDATA%/NovelGuard/logs/`
- [ ] No writes inside `dist/NovelGuard/_internal/` (read-only bundle)

## Destructive ops (optional; fixture only)

If testing finalize/cleanup/move: use **only** `packaging/fixtures/library/`. Do not run destructive flows against real libraries.

- [ ] (Optional) Dry-run preview only on fixture paths
- [ ] (Optional) Confirm outputs land under `<fixture-library>/SAVE/` when applicable

## Result

PASS / FAIL:

Notes:
