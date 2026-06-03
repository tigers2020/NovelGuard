# Changelog

All notable changes to this project are documented in this file.

Format loosely follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added

- **Platform release gate (PR-33..45):** 3-mode Work shell, unified scan section, resolve master-detail, FileDock global, app shell polish, Logs/Settings v2, finalize cleanup preview, bridge regression tests, E2E full pipeline smoke, packaging UI marker gate (`scripts/smoke_packaged_ui.py`), beta readiness doc.
- Windows-first PyInstaller **onedir** packaging for NovelGuard (`scripts/package_windows.py`, `packaging/NovelGuard.spec`).
- Bundled `web/build` frontend assets for the packaged desktop runtime.
- Production bridge **fail-closed** behavior to block `mockBridge` in production builds (`PRODUCTION_BRIDGE_UNAVAILABLE` / `DEV_BRIDGE_UNAVAILABLE`).
- Centralized **runtime path resolver** for logs, config, per-library state, and library-scoped `SAVE/` outputs (`src/app/runtime_paths.py`).
- App version diagnostics via `get_app_info()` (Settings read-only row).
- Packaging static verification (`scripts/verify_packaging.py`) and release docs under `docs/release/`.
- Smoke fixture library at `packaging/fixtures/library/`.

### Changed

- Work UI copy: Korean labels on resolve facets, apply subflow steps, and destructive-path hints (PR-45).
- Vite production output directory from `web/dist` to `web/build` (avoids PyInstaller `dist/` collision).

### Known limitations

- Windows onedir only; no installer, signing, auto-update, Store distribution, macOS, or Linux package.
- WebView2 Runtime required; legacy `~/.novelguard` not auto-migrated.
- See [docs/release/known-limitations.md](docs/release/known-limitations.md).
