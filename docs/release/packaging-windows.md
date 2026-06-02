# Windows Packaging Runbook

PR-24 release engineering — Windows-first PyInstaller **onedir** desktop package.

## Scope

- PyInstaller onedir under `dist/NovelGuard/`
- Bundled frontend: `web/build` → `_internal/web/build/`
- **Out of scope:** installer (MSI/NSIS), code signing, auto-update, macOS/Linux packages

## Build prerequisites

| Requirement | Notes |
|-------------|--------|
| Windows 10/11 | Target platform |
| Python 3.12+ | Same interpreter for packaging and PyInstaller |
| Node.js + npm | `web/` production build only at package time |
| GUI extras | `pip install -e ".[gui]"` (includes `pywebview`) |
| PyInstaller | `pip install pyinstaller` |
| Microsoft Edge WebView2 Runtime | Required at **runtime** on operator machines (not npm) |

Preflight: `python scripts/package_windows.py` fails fast if `webview` or PyInstaller is missing on the packaging Python.

## Build command

From repository root:

```bash
pip install -e ".[gui]"
pip install pyinstaller
cd web && npm install && cd ..
python scripts/package_windows.py
```

## Output

```text
dist/NovelGuard/NovelGuard.exe
dist/NovelGuard/_internal/web/build/index.html
dist/NovelGuard/_internal/app/_build_stamp.py   # when built via package script
dist/NovelGuard/build-manifest.json
```

Do not commit `dist/`, `build/`, or `src/app/_build_stamp.py`.

## Runtime path policy

| Data | Location |
|------|----------|
| Logs | `%LOCALAPPDATA%/NovelGuard/logs/` |
| Config | `%APPDATA%/NovelGuard/` |
| Per-library DB + audit | `%LOCALAPPDATA%/NovelGuard/state/libraries/<libraryId>/` |
| User-visible outputs (finalize, reports) | `<libraryRoot>/SAVE/` |

`libraryId` = SHA-256 of normalized library root (casefold on Windows). No automatic migration from legacy `~/.novelguard/`.

## Verification (CI-safe)

Static packaging gate (no exe build):

```bash
python scripts/verify_packaging.py
```

Full phase gate (includes pytest, ruff, mypy, black, npm lint, packaging verify):

```bash
python scripts/verify_phase_completion.py
```

## Smoke

1. Use fixture library: `packaging/fixtures/library/`
2. Fill in `docs/release/smoke-record-template.md`
3. **Destructive** finalize/cleanup/move tests: fixture library **only**

## Fresh-machine runtime prerequisites

- WebView2 Runtime installed
- **No** Node/npm required to run the packaged exe
- Do not open `web/build/index.html` in a browser for production smoke — use `NovelGuard.exe` (production bridge fail-closed)

## Troubleshooting

| Symptom | Action |
|---------|--------|
| Package script: missing `webview` | `pip install -e ".[gui]"` on the **same** Python as `python scripts/package_windows.py` |
| Package script: missing PyInstaller | `pip install pyinstaller` |
| Package script: missing npm | Install Node.js; ensure `npm` on PATH |
| Exe exits immediately | Check packaging Python had GUI extras; rebuild with `package_windows.py` |
| Blank window / WebView2 error | Install [Microsoft Edge WebView2 Runtime](https://developer.microsoft.com/microsoft-edge/webview2/) |
| `PRODUCTION_BRIDGE_UNAVAILABLE` | Launch `NovelGuard.exe`, not static `index.html` in a browser |
| Cannot delete `dist/NovelGuard` | Close running `NovelGuard.exe`; package script may rename locked dir to `NovelGuard.bak.*` |

## Related docs

- [Known limitations](known-limitations.md)
- [Smoke record template](smoke-record-template.md)
- [CHANGELOG.md](../../CHANGELOG.md) — PR-24 release notes (Unreleased)
- Spec: `docs/superpowers/specs/012-2026-06-02-packaging-distribution-design.md`
- Plan: `docs/superpowers/plans/018-2026-06-02-pr24-packaging-distribution.md`
- Manual PyInstaller smoke: `packaging/README.md`
