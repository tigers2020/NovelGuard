# PR-24: Packaging / Distribution — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Ship Windows-first **PyInstaller onedir** package with bundled `web/build` assets, centralized `runtime_paths`, production bridge fail-closed, version metadata, and packaging verification — **no product feature or shell IA changes**.

**Architecture:** `runtime_paths` (dev vs frozen) → session/bridge path call sites → Vite `web/build` → PyInstaller `packaging/NovelGuard.spec` → `scripts/package_windows.py` → `verify_packaging.py` hooked from `verify_phase_completion.py`.

**Tech Stack:** Python 3.12, pywebview, PyInstaller, React/Vite, pytest + Vitest (extend existing files only).

**Spec:** [012-2026-06-02-packaging-distribution-design.md](../specs/012-2026-06-02-packaging-distribution-design.md) (**approved** 2026-06-02 — LOCK-G1, LOCK-G2, G3–G5)

**Plan status:** **Approved** (2026-06-02) — ready for implementation

**Prerequisite:** PR-23 merged (plan 017 implemented, PR #14)

**Parent:** [001 PR-20..25 roadmap](../roadmap/001-2026-06-02-pr20-pr25-development-roadmap.md)

**Test policy:** Extend `tests/test_bridge_contract.py`, `web/src/bridge/bridgeParity.test.ts` — **no new test files** without `TEST_ALLOWED`.

**Scope freeze:** No legacy `~/.novelguard` auto-migration unless user opens new spec cycle. No AppShell / WorkTab / FileDock IA changes (PR-25).

---

## Plan-locked constants (spec 012 approved)

| Constant | Value |
|----------|--------|
| Frontend outDir | `web/build/` (LOCK-11) |
| Package output | `dist/NovelGuard/NovelGuard.exe` (onedir, LOCK-7) |
| Canonical package cmd | `python scripts/package_windows.py` (LOCK-10) |
| Logs | `%LOCALAPPDATA%/NovelGuard/logs/` |
| Config | `%APPDATA%/NovelGuard/` |
| State root | `%LOCALAPPDATA%/NovelGuard/state/` |
| Per-library state | `%LOCALAPPDATA%/NovelGuard/state/libraries/<libraryId>/` |
| `library.db` | `.../libraries/<libraryId>/library.db` |
| `apply-audit.jsonl` | `.../libraries/<libraryId>/apply-audit.jsonl` |
| User SAVE root | `<libraryRoot>/SAVE/` |
| User reports | `<libraryRoot>/SAVE/reports/` |
| `libraryId` | Stable hash of normalized library root absolute path (SHA-256 hex, plan task 1) |
| Dev mock flag | `VITE_USE_MOCK_BRIDGE=true` (LOCK-G2) |
| PROD bridge error | `PRODUCTION_BRIDGE_UNAVAILABLE` |
| Dev bridge error (no api, no flag) | `DEV_BRIDGE_UNAVAILABLE` |

---

## File map

| File | Action |
|------|--------|
| `src/app/runtime_paths.py` | **Create** |
| `src/app/version.py` | **Create** |
| `src/app/webview_main.py` | **Modify** — `runtime_paths.frontend_asset_root()` |
| `src/app/session_factory.py` | **Modify** — DB, audit, SAVE paths via resolver |
| `src/app/bridge_api.py` | **Modify** — audit/finalize paths via resolver |
| `src/application/finalize_report.py` | **Modify** — SAVE root if hardcoded |
| `src/application/library_session.py` | **Modify** — pass library root for SAVE |
| `web/vite.config.ts` | **Modify** — `outDir: "build"` |
| `web/src/app/providers/SnapshotProvider.tsx` | **Modify** — LOCK-G2 bridge resolution |
| `web/src/bridge/bridgeFactory.ts` (or inline in provider) | **Create** — optional extract from provider |
| `web/src/bridge/bridgeErrors.ts` | **Create** — error types/codes |
| `web/src/bridge/bridgeParity.test.ts` | **Modify** — PROD/DEV/mock flag cases |
| `web/.env.development` | **Modify** — document `VITE_USE_MOCK_BRIDGE` |
| `packaging/NovelGuard.spec` | **Create** |
| `scripts/package_windows.py` | **Create** |
| `scripts/package_windows.bat` | **Create** (optional wrapper) |
| `scripts/verify_packaging.py` | **Create** |
| `scripts/verify_phase_completion.py` | **Modify** — invoke packaging checks |
| `run.bat` | **Modify** — `web/build` paths |
| `.gitignore` | **Modify** — `web/build/`, `dist/NovelGuard/` |
| `pyproject.toml` | **Modify** — optional `[project.scripts]` / dev dep note for PyInstaller |
| `docs/release/packaging-windows.md` | **Create** |
| `docs/release/known-limitations.md` | **Create** |
| `docs/release/smoke-record-template.md` | **Create** |
| `CHANGELOG.md` | **Modify** |
| `tests/test_runtime_paths.py` | **Extend existing** — prefer `tests/test_bridge_contract.py` or add to smallest existing `tests/test_*.py` under app if one exists |

**Grep before edit:** `web/dist`, `.novelguard`, `SAVE/finalize`, `apply-audit` — migrate all call sites.

---

## Task 0: Plan gate

- [x] Spec 012 **approved** (G1–G5, LOCK-G1, LOCK-G2 — 2026-06-02)
- [x] Plan 018 **approved** (2026-06-02)
- [ ] PR-23 on branch baseline (plan 017 implemented)
- [ ] Human confirms **no** legacy path migration in this slice (default: **no migration**)

---

## Task 1: Runtime path resolver

**Files:** `src/app/runtime_paths.py`, tests in existing module

- [x] `is_frozen()` — `getattr(sys, "frozen", False)` or equivalent
- [x] `app_root()` — repo root (dev) vs exe parent (frozen)
- [x] `frontend_asset_root()` — `web/build` (dev) vs bundled subtree (frozen)
- [x] `state_root()`, `logs_dir()`, `config_dir()`
- [x] `library_id_for_root(library_root: Path) -> str` — SHA-256 of normalized absolute path
- [x] `library_state_dir(library_id)`, `library_db_path(library_id)`, `apply_audit_path(library_id)`
- [x] `save_dir_for_library(library_root)`, `reports_dir_for_library(library_root)`
- [x] Unit tests in `tests/test_scaffold.py` — dev path, env overrides, libraryId, SAVE/reports
- [x] **No** call-site migration in Task 1 (session_factory / bridge_api untouched)

---

## Task 2: Wire Python call sites to resolver

**Files:** `session_factory.py`, `bridge_api.py`, finalize/repair writers

- [x] Replace `Path.home() / ".novelguard"` with resolver functions when `library_root` / `library_id` known
- [x] Session open: derive `library_id` from selected folder (`bind_library_runtime` on `select_folder`)
- [x] Finalize report path: `<libraryRoot>/SAVE/finalize/<sessionId>/` (align spec 011 behavior, new root)
- [x] Repair backup: `<libraryRoot>/SAVE/repair_backup/` (or subpath per existing layout)
- [x] Dev mode: **new paths only** — no legacy `~/.novelguard` reads; no auto-migrate
- [x] Tests in `test_scaffold.py` + `test_cancel_scan_discards_partial` factory wiring fix

---

## Task 3: Frontend outDir `web/build/`

**Files:** `web/vite.config.ts`, `webview_main.py`, `run.bat`, `.gitignore`, docs

- [x] `build.outDir: "build"` in Vite config
- [x] Update `webview_main` → `runtime_paths.frontend_asset_root()`
- [x] Update `run.bat` post-build check for `web\build\index.html`
- [x] `.gitignore`: `web/build/`, `web/dist/`
- [x] Vite `web/build/` output verified (`npx vite build`); **`npm run build` closed in Task 4** (tsc)

---

## Task 4: Production bridge fail-closed (LOCK-G2)

**Files:** `SnapshotProvider.tsx`, bridge factory module, `bridgeParity.test.ts`, `.env.development`

- [x] `resolveBridge()` in `bridgeFactory.ts`
- [x] PROD + no api → `PRODUCTION_BRIDGE_UNAVAILABLE` fatal UI (`bridge-unavailable` testid)
- [x] DEV + no api + no flag → `DEV_BRIDGE_UNAVAILABLE` (no silent mock)
- [x] DEV + `VITE_USE_MOCK_BRIDGE=true` → mockBridge (`.env.e2e` + `dev:e2e --mode e2e`)
- [x] Vitest: three cases in `bridgeParity.test.ts`
- [x] `.env.development.example` documents mock flag
- [x] E2E: `dev:e2e` uses `--mode e2e` for mock bridge
- [x] Fix pre-existing TS errors so `npm run build` passes (Task 3 acceptance close)

---

## Task 5: Version metadata

**Files:** `src/app/version.py`, generated/copied `web` artifact, bridge or snapshot field

- [x] `src/app/version.py` — `get_app_info()`, `apply_build_stamp()` for Task 7
- [x] Bridge `get_app_info()` + `validate_app_info`
- [x] Frontend `AppInfo` type, parity, mock/pywebview adapters
- [x] Settings placeholder: `AppInfoDiagnostics` read-only row
- [x] Contract test `test_get_app_info_returns_required_keys`

---

## Task 6: PyInstaller spec (onedir)

**Files:** `packaging/NovelGuard.spec`, `packaging/README.md`

- [x] Entry: `src/app/webview_main.py`; `ROOT = Path(SPECPATH).parent`
- [x] `datas`: `web/build` → `web/build` (frozen: `_internal/web/build/index.html`)
- [x] Hiddenimports: empty until smoke demands (tkinter not excluded — folder picker)
- [x] Excludes: `pytest`, `unittest` only
- [x] Smoke: `pyinstaller packaging/NovelGuard.spec --noconfirm --clean` → `dist/NovelGuard/NovelGuard.exe`
- [ ] WebView2 note → `known-limitations.md` (Task 10)

---

## Task 7: `scripts/package_windows.py`

- [x] Preflight: Python path/version, `PyInstaller`, `webview`, `npm`
- [x] Clean `web/build`, `build/`, `dist/NovelGuard`, `src/app/_build_stamp.py`
- [x] `npm ci` / `npm install` + `npm run build` → `web/build/index.html`
- [x] `apply_build_stamp` → generated `src/app/_build_stamp.py` (gitignored)
- [x] PyInstaller + `--hidden-import app._build_stamp`
- [x] Verify exe + bundled `web/build/index.html`
- [x] `dist/NovelGuard/build-manifest.json`
- [x] Windows locked-dir rename fallback for `dist/NovelGuard`
- [ ] Optional `package_windows.bat` → delegates to Python script

---

## Task 8: Packaging verification helper

**Files:** `scripts/verify_packaging.py`, `scripts/verify_phase_completion.py`

- [x] Static checks: spec 012, plan 018, spec/script/runtime/version/vite/bridge guards
- [x] `web/build` in runtime paths; no `web/dist` in runtime-critical files
- [x] Optional artifact checks when `dist/NovelGuard` exists (exe, manifest, bundled index)
- [x] `verify_phase_completion.py` step 6/6 → `verify_packaging.py` (no PyInstaller run)
- [x] Full exe build **not** required on CI — use `python scripts/package_windows.py` locally

---

## Task 9: Smoke fixture + smoke record

**Files:** `docs/release/smoke-record-template.md`, `docs/release/packaging-windows.md`

- [ ] Document fixture library path (repo `tests/fixtures/` or dedicated `packaging/fixtures/library/`)
- [ ] Manual checklist: launch exe → folder select → scan → resolve navigation → logs path
- [ ] Destructive ops: fixture only
- [ ] Fresh-machine prerequisites (WebView2, no npm at runtime)
- [ ] Filled smoke record template committed as example or left blank for operator

---

## Task 10: Release docs + changelog

- [ ] `docs/release/packaging-windows.md` — build, run, troubleshoot
- [ ] `docs/release/known-limitations.md` — Windows-only, no installer/signing/auto-update, onedir, mock block, no legacy migration
- [ ] `CHANGELOG.md` — PR-24 entry

---

## Task 11: Final verification

- [ ] `python scripts/verify_phase_completion.py` — all steps pass
- [ ] `python scripts/package_windows.py` — produces exe on dev machine
- [ ] Manual smoke record completed (Task 9)
- [ ] Scope freeze acknowledged — no FileDock, no feature creep

---

## Contract / regression matrix

| Scenario | Expected |
|----------|----------|
| Dev + pywebview | Real bridge |
| Dev + browser + `VITE_USE_MOCK_BRIDGE=true` | mockBridge |
| Dev + browser + no flag | `DEV_BRIDGE_UNAVAILABLE` |
| PROD build + no pywebview | `PRODUCTION_BRIDGE_UNAVAILABLE` |
| Frozen app writes log | Under `%LOCALAPPDATA%/NovelGuard/logs/` |
| Frozen app writes DB | Under `state/libraries/<libraryId>/` |
| Finalize report | Under `<library>/SAVE/finalize/...` |
| `npm run test` / bridge parity | Pass |
| `pytest` | Pass |

---

## Changelog

| Date | Change |
|------|--------|
| 2026-06-02 | Initial plan 018 from approved spec 012 (grill-me G1–G5) |
