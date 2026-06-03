# NovelGuard Windows packaging (PR-24)

## Prerequisites

- Python 3.12+ on the **same interpreter** used for PyInstaller
- `pip install -e ".[gui]"` (pulls in `pywebview` — required or the frozen exe exits at startup)
- `pip install pyinstaller`
- Node.js/npm — `cd web && npm install && npm run build` → `web/build/index.html`

## Canonical build (Task 7)

From repository root (same Python as PyInstaller; GUI extras installed):

```bash
pip install -e ".[gui]"
pip install pyinstaller
python scripts/package_windows.py
```

Preflight fails fast if `pywebview` or PyInstaller is missing on that interpreter.

## Manual onedir build (Task 6 smoke)

From repository root:

```bash
cd web && npm run build && cd ..
pyinstaller packaging/NovelGuard.spec --noconfirm --clean
```

Expected output:

```text
dist/NovelGuard/NovelGuard.exe
dist/NovelGuard/_internal/...
dist/NovelGuard/_internal/web/build/index.html   # via _MEIPASS at runtime
```

Canonical automated build: `python scripts/package_windows.py` (Task 7).

Bundled frontend path must match `runtime_paths.frontend_asset_root()` when frozen (`bundle_root() / "web" / "build"`).

## Post-build smoke (PR-44)

`package_windows.py` runs `smoke_packaged_ui` (strict bundle markers). Manual checklist: `docs/release/packaging-smoke-checklist.md`.
