# Known Limitations — Windows packaging

Release-engineering scope for the Windows desktop package. Not a full product limitation list.

## Platform and distribution

- **Windows-first package only.** macOS and Linux packages are deferred.
- **PyInstaller onedir only.** Onefile bundles are deferred.
- **No installer** (MSI, NSIS, Inno Setup, etc.).
- **No code signing** or notarization.
- **No auto-update** channel.
- **No Microsoft Store** distribution.

## Runtime

- **Microsoft Edge WebView2 Runtime** is required on the operator machine.
- The packaged app must run inside **pywebview** (`NovelGuard.exe`). Opening `web/build/index.html` directly in a browser is **unsupported** and triggers production bridge fail-closed (`PRODUCTION_BRIDGE_UNAVAILABLE`).
- **`mockBridge` is intentionally blocked** in production builds (`VITE_USE_MOCK_BRIDGE` is a dev/e2e path only).

## Data and paths

- **Legacy `~/.novelguard` data is not automatically migrated** to `%LOCALAPPDATA%/NovelGuard/` / `%APPDATA%/NovelGuard/`.
- Per-library state lives under `%LOCALAPPDATA%/NovelGuard/state/libraries/<libraryId>/`; user outputs under `<libraryRoot>/SAVE/`.

## UI / release gate (PR-33..43)

- **Work surface is 3-mode** (Scan / Resolve / Quality). `finalize` is not a top-level work mode; use **FinalizeSubflowDialog** from apply/resolve/quality CTAs.
- **Dev mock bridge** (`VITE_USE_MOCK_BRIDGE`) is not available in packaged builds; Playwright E2E uses mock in Vite dev only.
- **Packaged UI smoke** is manual per [packaging-smoke-checklist.md](packaging-smoke-checklist.md); automated checks verify `data-testid` anchors in source and (strict) in `web/build` after package.

## Verification and smoke

- **Package smoke uses fixture libraries only** (`packaging/fixtures/library/`). Do not run destructive finalize/cleanup tests against personal libraries.
- **Headless packaged E2E** (drive `NovelGuard.exe` from Playwright) is deferred; mock-bridge E2E covers full pipeline in dev ([PR-43](../superpowers/roadmap/003-2026-06-02-platform-release-gate-roadmap.md)).
- **Stale local `web/build` or `dist/NovelGuard`** may warn on `smoke_packaged_ui.py` until rebuilt with `package_windows.py`.

## CI vs local

- `python scripts/verify_packaging.py` is CI-safe (static checks; optional artifact checks when `dist/NovelGuard` exists).
- `python scripts/package_windows.py` is a **local** full build (npm + PyInstaller); not required on every CI run.

## Related docs

- [Windows packaging runbook](packaging-windows.md)
- [Smoke record template](smoke-record-template.md)
- Spec: `docs/superpowers/specs/012-2026-06-02-packaging-distribution-design.md`
