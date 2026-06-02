---
title: PR-24 Packaging / Distribution
status: approved
date: 2026-06-02
authors: PR-24 spec gate + codebase baseline
parent_spec: docs/superpowers/specs/011-2026-06-02-finalize-cleanup-pipeline-design.md
related_specs:
  - docs/superpowers/specs/002-2026-06-01-novelguard-greenfield-library-session-design.md
  - docs/superpowers/specs/000-2026-06-01-novelguard-ui-overhaul-design.md
roadmap: docs/superpowers/roadmap/001-2026-06-02-pr20-pr25-development-roadmap.md
pr_label: PR-24
plan: docs/superpowers/plans/018-2026-06-02-pr24-packaging-distribution.md
prerequisite: PR-23 merged (plan 017 implemented)
---

# PR-24 — Packaging / Distribution

## Status

**Approved** (2026-06-02) — grill-me **G1–G5** + **LOCK-G1** + **LOCK-G2** locked below. Implementation per [plan 018](../plans/018-2026-06-02-pr24-packaging-distribution.md).

## Scope sentence

PR-24 turns the current NovelGuard **pywebview + React/Vite + Python** desktop app into a **Windows-first distributable** that runs **without** the Vite dev server. Target artifact: **PyInstaller onedir** (`dist/NovelGuard/NovelGuard.exe`) or an interim `run.bat` that documents remaining runtime deps. **Release engineering only** — no scan, duplicate, relation, quality, finalize, or shell IA changes.

---

## Locked decisions (grill-me — 2026-06-02)

| # | Topic | Lock | Status |
|---|--------|------|--------|
| G1 | Runtime paths | **Option C** — see **LOCK-G1**; per-library state under `%LOCALAPPDATA%/NovelGuard/state/libraries/<libraryId>/`; user-visible outputs under `<library>/SAVE/` | **Approved 2026-06-02** |
| G2 | Production bridge | **Fail-closed** — see **LOCK-G2**; `VITE_USE_MOCK_BRIDGE=true` for explicit dev mock | **Approved 2026-06-02** |
| G3 | onedir vs onefile | **onedir only** for PR-24 acceptance | **Approved 2026-06-02** |
| G4 | Smoke level | Manual smoke record + automated static/package checks | **Approved 2026-06-02** |
| G5 | Canonical command | `python scripts/package_windows.py` | **Approved 2026-06-02** |

### LOCK-G1 — Runtime paths (Option C)

PR-24 adopts **Option C** runtime paths:

- **Logs** (machine-local runtime artifacts): `%LOCALAPPDATA%/NovelGuard/logs/`
- **Config** (user preference): `%APPDATA%/NovelGuard/`
- **App-owned mutable state root**: `%LOCALAPPDATA%/NovelGuard/state/`
- **Per-library internal state**: `%LOCALAPPDATA%/NovelGuard/state/libraries/<libraryId>/`
  - `library.db`
  - authoritative `apply-audit.jsonl`
- **User-visible finalize/repair outputs**: `<libraryRoot>/SAVE/` (e.g. finalize JSON, repair backup staging per existing feature layout)
- **User-readable reports** (recommended export/summary copies): `<libraryRoot>/SAVE/reports/`
- **Bundled frontend assets**: frozen app dir — **read-only; no writes**

`libraryId` is a stable app-derived identifier for the selected library root (plan 018 locks algorithm — e.g. SHA-256 of normalized absolute path).

**Migration:** PR-24 wires **new** paths via `runtime_paths`. **No** automatic migration of legacy `~/.novelguard/` or `~/.novelguard/SAVE` contents unless explicitly added to plan 018.

**Rationale:** SAVE is user-inspectable output; `library.db` and authoritative audit are app metadata and must not live beside user files in a way that confuses cleanup or library move/delete.

### LOCK-G2 — Production bridge fail-closed

In **production** builds (`import.meta.env.PROD`):

- `mockBridge` **MUST NOT** be selected automatically.
- Missing `window.pywebview.api` **MUST** surface fatal error: `PRODUCTION_BRIDGE_UNAVAILABLE`.
- UI **MUST NOT** render fake scan/review/apply/finalize data.
- Browser-opened production build is **unsupported** — show fatal bridge screen (not a general web app).
- Development mock requires **explicit opt-in**: `VITE_USE_MOCK_BRIDGE=true` (and no pywebview api).

Minimum bridge resolution (conceptual):

```ts
export function resolveBridge() {
  const api = window.pywebview?.api;
  if (api) return createPywebviewBridge(api);
  if (import.meta.env.PROD) {
    throw new BridgeUnavailableError("PRODUCTION_BRIDGE_UNAVAILABLE");
  }
  if (import.meta.env.VITE_USE_MOCK_BRIDGE === "true") return mockBridge;
  throw new BridgeUnavailableError("DEV_BRIDGE_UNAVAILABLE");
}
```

**Tests (extend existing web test module — no new test files without `TEST_ALLOWED`):**

| Case | Expected |
|------|----------|
| PROD + no pywebview | `PRODUCTION_BRIDGE_UNAVAILABLE` |
| DEV + no flag + no pywebview | mock **not** auto-selected |
| DEV + `VITE_USE_MOCK_BRIDGE=true` | mock allowed |

---

## Codebase baseline (2026-06-02)

| Area | Current state | PR-24 action |
|------|---------------|--------------|
| Desktop entry | [`src/app/webview_main.py`](../../../src/app/webview_main.py) loads `web/dist/index.html` | Route via `runtime_paths.frontend_asset_root()` |
| Vite outDir | `web/vite.config.ts` → `dist` | **Migrate** to `web/build/` (avoid PyInstaller `dist/` collision; [pywebview freezing guide](https://pywebview.flowrl.com/guide/freezing.html)) |
| Dev launcher | [`run.bat`](../../../run.bat) — `npm run build` + `python src/app/webview_main.py` | Keep as **dev** path; canonical package command = `python scripts/package_windows.py` |
| Writable paths | `Path.home() / ".novelguard"` in [`session_factory.py`](../../../src/app/session_factory.py) | Consolidate in `runtime_paths.py`; grill-me locks packaged layout |
| Bridge selection | [`SnapshotProvider.tsx`](../../../web/src/app/providers/SnapshotProvider.tsx) — no pywebview → **silent `mockBridge`** | **PROD fail-closed** (`PRODUCTION_BRIDGE_UNAVAILABLE`) |
| pywebview adapter | [`pywebviewBridge.ts`](../../../web/src/bridge/pywebviewBridge.ts) — no mock fallback | Preserve; extend PROD guards |
| FileDock / shell | WorkTab internal dock; AppShell FileSummaryStrip per [000 UI overhaul](000-2026-06-01-novelguard-ui-overhaul-design.md) | **No change** (PR-25) |

---

## 1. Purpose

Ship a user-runnable Windows desktop package:

1. **`NovelGuard.exe`** (PyInstaller onedir) with bundled frontend static assets, **or**
2. Documented **`run.bat`** interim only if exe path slips — must state Python/Node requirements explicitly.

Packaged runtime:

- Loads **bundled** HTML/JS/CSS (not `npm run dev`, not localhost Vite).
- Python remains authority for FS, `LibrarySession`, bridge methods, destructive-operation guards.
- Frontend calls **only** `window.pywebview.api` (via `createPywebviewBridge`).

---

## 2. Non-goals / scope freeze

PR-24 **MUST NOT**:

- Add or change scan, duplicate, relation, quality, finalize, or cleanup **behavior**
- Change review UX or Work shell IA (tabs, AppShell, WorkTab FileDock placement)
- Implement PR-25 shell FileDock
- Auto-update, Store distribution, macOS/Linux packages
- Installer authoring (beyond placeholder docs), code signing, telemetry, crash reporting service

PR-24 **MAY** add only: build scripts, PyInstaller spec, `runtime_paths`, version metadata, production bridge guards, packaging verification helpers, release docs.

**LOCK-1:** PR-24 is release engineering only.

**LOCK-9:** PR-25 Shell FileDock is explicitly out of scope.

---

## 3. Packaging architecture

### 3.1 Frontend

```text
clean outputs
→ frontend production build (Vite)
→ bundle static assets into Python package (PyInstaller datas)
→ pywebview loads local index.html from bundled path
```

**Forbidden in packaged runtime:**

- Vite dev server
- `npm run dev`
- localhost frontend server
- silent `mockBridge` fallback

**Frontend build output (locked for PR-24):**

```text
web/build/
```

Rationale: PyInstaller default output also uses `dist/`; separate names avoid collisions ([pywebview freezing](https://pywebview.flowrl.com/guide/freezing.html), [PyInstaller spec `datas`](https://pyinstaller.org/en/stable/spec-files.html)).

**Migration:** Change `vite.config.ts` `build.outDir` from `dist` → `build`; update `webview_main`, `.gitignore`, docs, and package script references in the **same PR**.

### 3.2 Python desktop runtime

Unchanged role: filesystem, session state, bridge API, apply/finalize safety. Frontend is static UI over pywebview `js_api`.

Entrypoint for packaging: `src/app/webview_main.py` (or thin wrapper re-exported in spec).

### 3.3 Packaging tool

**Primary:** PyInstaller **onedir** on Windows.

**Acceptance target:**

```text
dist/NovelGuard/NovelGuard.exe
dist/NovelGuard/_internal/...
(bundled web assets under predictable subpath — exact tree locked in plan 018)
```

**LOCK-7:** First package target is **onedir only**; onefile deferred.

Onefile may be documented as future work; not PR-24 acceptance.

---

## 4. Runtime path policy

### 4.1 Single resolver

Add **`src/app/runtime_paths.py`** — the **only** module that resolves dev vs frozen paths.

```python
def is_frozen() -> bool: ...
def app_root() -> Path: ...
def frontend_asset_root() -> Path: ...
def state_root() -> Path: ...
def library_state_dir(library_id: str) -> Path: ...
def library_db_path(library_id: str) -> Path: ...
def apply_audit_path(library_id: str) -> Path: ...
def logs_dir() -> Path: ...
def config_dir() -> Path: ...
def save_dir_for_library(library_root: Path) -> Path: ...
def reports_dir_for_library(library_root: Path) -> Path: ...
def library_id_for_root(library_root: Path) -> str: ...
```

**LOCK-6:** No scattered packaging path logic in bridge, session, or feature modules.

`session_factory`, `bridge_api`, finalize/repair report writers, and `webview_main` **must** call `runtime_paths` after PR-24.

### 4.2 Path categories (LOCK-G1 approved)

| Category | Dev (interim) | Target (LOCK-G1) | Writable |
|----------|---------------|------------------|----------|
| Frontend assets | `web/build/index.html` | Bundled read-only dir | No |
| `library.db` | `~/.novelguard/library.db` | `%LOCALAPPDATA%/NovelGuard/state/libraries/<libraryId>/library.db` | Yes |
| `apply-audit.jsonl` | `~/.novelguard/apply-audit.jsonl` | `.../libraries/<libraryId>/apply-audit.jsonl` | Yes |
| Finalize / repair outputs | `~/.novelguard/SAVE/...` | `<libraryRoot>/SAVE/...` | Yes |
| User reports (export) | — | `<libraryRoot>/SAVE/reports/` | Yes |
| Logs | stderr / ad hoc | `%LOCALAPPDATA%/NovelGuard/logs/` | Yes |
| Config | — | `%APPDATA%/NovelGuard/` | Yes |

Dev mode may keep reading legacy `~/.novelguard/` until session wiring switches — plan 018 sequences resolver first, then call-site migration.

### 4.3 Hard rule

**LOCK-5:** Packaged runtime **MUST NOT** write into the frozen application directory (`_internal/`, exe dir assets).

```text
bundled app dir     = read-only assets + binaries
LOCALAPPDATA/...    = logs + per-library internal state (DB, audit)
APPDATA/...         = config
<library>/SAVE/     = user-visible outputs + reports
```

---

## 5. Production bridge contract

### 5.1 `mockBridge` block

| Mode | Bridge |
|------|--------|
| **PROD** | pywebview **required** — **LOCK-G2** |
| **DEV** + pywebview | pywebview |
| **DEV** + `VITE_USE_MOCK_BRIDGE=true` | mockBridge (explicit opt-in only) |
| **DEV** otherwise | fatal `DEV_BRIDGE_UNAVAILABLE` (no silent mock) |

**LOCK-4 / LOCK-G2:** Production mock fallback forbidden.

**Required PROD failure** when `window.pywebview?.api` missing:

```text
PRODUCTION_BRIDGE_UNAVAILABLE
```

Fatal UI (existing `bridge-unavailable` pattern extended) — **no** fake scan/review/apply/finalize data.

**Forbidden in PROD:**

```text
silent mockBridge in SnapshotProvider.resolveBridge()
apply/finalize through mock data
```

### 5.2 Build-time guard

Minimum lock (extend existing [`bridgeParity.test.ts`](../../../web/src/bridge/bridgeParity.test.ts)):

```text
import.meta.env.PROD === true AND no pywebview api
→ bridge factory throws / returns error path with PRODUCTION_BRIDGE_UNAVAILABLE
```

Additional checks allowed: static import boundary (pywebviewBridge must not import mockBridge — **already tested**), `verify_packaging.py` grep, Vitest factory unit test.

### 5.3 Runtime guard

On PROD startup:

```text
window.pywebview.api exists
required bridge methods exist (parity set)
mockBridge not active (BridgeKind !== "mock" in packaged exe)
```

Python side: packaged entry must pass `js_api` to `webview.create_window` (already true in `webview_main`).

---

## 6. Version metadata

Expose diagnostics-only metadata (no feature gating by version).

```json
{
  "appName": "NovelGuard",
  "version": "0.24.0",
  "buildType": "dev|production|packaged",
  "gitCommit": "...",
  "builtAt": "...",
  "frontendBuild": "web/build",
  "pythonRuntime": "3.12.x"
}
```

Suggested sources:

```text
src/app/version.py          # generated or maintained at build time
web/src/app/version.json    # copied/generated during package script
```

Expose via bridge method (e.g. `get_app_info`) and/or snapshot `app.version` field — **plan 018** picks one surface; spec requires **some** user-visible version in About/diagnostics.

---

## 7. Build pipeline

**Canonical command (LOCK-10):**

```bash
python scripts/package_windows.py
```

Optional wrapper: `scripts/package_windows.bat` → calls Python script.

**Pipeline steps:**

```text
1. clean prior frontend + PyInstaller outputs (not whole repo)
2. verify Node deps / run web install if missing (documented)
3. web: production build → web/build/
4. verify index.html + assets exist
5. PyInstaller using packaging/NovelGuard.spec
6. verify bundled frontend inside dist/NovelGuard/
7. optional: launch smoke (non-interactive or documented manual)
8. write build manifest (paths, version, git commit)
```

**Dev path (unchanged intent):** `run.bat` remains convenient for developers; **not** the canonical clean-checkout package command.

---

## 8. PyInstaller spec policy

Committed spec:

```text
packaging/NovelGuard.spec
```

Must include:

- Entry: `webview_main` (or designated `__main__`)
- `datas=` — `web/build/**` → bundled web subtree
- Hidden imports only as needed (pywebview, stdlib hooks)
- Exclude: tests, `.vite/`, `node_modules/`, dev fixtures, source maps (unless explicitly accepted)
- No dev-server, no `mockBridge` assets as runtime fallback

Example layout (exact paths in plan 018):

```text
dist/NovelGuard/NovelGuard.exe
dist/NovelGuard/_internal/...
dist/NovelGuard/web/build/...   # or equivalent — resolver is sole reader
```

---

## 9. Smoke test

### 9.1 Required smoke (manual minimum)

```text
launch packaged app (exe or documented run.bat)
main window visible
production bridge active (not mock)
select folder → scan
open resolve/review — non-destructive navigation
close app
logs written under logs_dir() (not frozen app dir)
```

### 9.2 Destructive operations

Use **fixture library only** in smoke docs/scripts. No developer real library paths.

### 9.3 Fresh machine

Document:

```text
Windows VM or clean host
no Vite dev server
no repo-relative path assumptions at runtime
no npm at runtime for exe path
Python not required on PATH when using NovelGuard.exe
```

If `run.bat` ships as interim, document **exact** prerequisites (Python venv, Node for build-only vs runtime).

**LOCK-8 (G4):** PR-24 minimum = **manual smoke record** + automated static/package checks; full E2E against exe is optional stretch.

---

## 10. Verification integration

Top-level gate unchanged:

```bash
python scripts/verify_phase_completion.py
```

Add packaging helper (recommended):

```text
scripts/verify_packaging.py
```

Checks (extend gate or subprocess):

| Check | Required |
|-------|----------|
| `packaging/NovelGuard.spec` exists | Yes |
| `scripts/package_windows.py` exists | Yes |
| `runtime_paths` unit tests (extend existing test module) | Yes |
| PROD `mockBridge` block test | Yes |
| Version metadata files present | Yes |
| Frontend `web/build` policy documented / vite outDir | Yes |
| Package smoke record template in `docs/release/` | Yes |
| Full exe build on every CI run | Optional (document local vs CI) |

---

## 11. Documentation outputs

| Path | Purpose |
|------|---------|
| This spec | Design gate |
| `docs/superpowers/plans/018-2026-06-02-pr24-packaging-distribution.md` | Tasks (after approval) |
| `docs/release/packaging-windows.md` | Operator runbook |
| `docs/release/known-limitations.md` | Shipped constraints |
| `CHANGELOG.md` | Release notes entry |

**Known limitations (minimum):**

- Windows-first only
- No auto-update, installer, or code signing
- onedir only (not onefile)
- Smoke uses fixture library
- PROD requires pywebview bridge; mock intentionally blocked
- SAVE/log path policy per approved G1

---

## 12. Acceptance criteria

**Automated:**

```bash
python scripts/verify_phase_completion.py
```

passes including packaging checks.

**Clean checkout package:**

```bash
python scripts/package_windows.py
```

produces launchable `dist/NovelGuard/NovelGuard.exe` (or documented equivalent).

**Manual smoke** confirms:

- [ ] Packaged app launches without dev server
- [ ] Folder select + scan work
- [ ] Resolve/review navigation works (non-destructive)
- [ ] PROD blocks `mockBridge` fallback
- [ ] Writable paths outside frozen app dir
- [ ] Version metadata visible

---

## 13. Grill-me resolution log

All items **approved 2026-06-02** — see **Locked decisions** at top (**LOCK-G1**, **LOCK-G2**, G3–G5).

---

## 14. Decision locks (approved)

| Lock | Statement |
|------|-----------|
| LOCK-1 | Release engineering only; no product feature changes |
| LOCK-2 | Windows-first package target |
| LOCK-3 | Frontend dev server forbidden in packaged runtime |
| LOCK-4 | Production `mockBridge` fallback forbidden (see LOCK-G2) |
| LOCK-5 | No writes inside frozen app directory |
| LOCK-6 | Single `runtime_paths` module |
| LOCK-7 | PyInstaller **onedir** first (G3) |
| LOCK-8 | `verify_phase_completion.py` remains top-level gate |
| LOCK-9 | PR-25 Shell FileDock out of scope |
| LOCK-10 | `python scripts/package_windows.py` is canonical package command (G5) |
| LOCK-11 | Vite `outDir` → `web/build/` (avoid PyInstaller `dist/` collision) |
| **LOCK-G1** | Option C runtime paths — see § Locked decisions |
| **LOCK-G2** | Production bridge fail-closed + explicit dev mock flag |

---

## 15. Risk register

| Risk | Impact | Mitigation |
|------|--------|------------|
| PROD still uses `mockBridge` when opened in browser | Fake destructive ops appear possible in UI | `import.meta.env.PROD` guard in `resolveBridge`; test + smoke |
| Packaged app reads repo `web/dist` or `~/.novelguard` | Fresh machine failure | `runtime_paths` + grill-me G1 |
| PyInstaller misses pywebview/WebView2 edge deps | Launch failure on clean VM | Document WebView2 runtime; smoke on clean VM |
| `dist/` name collision | Wrong assets bundled | LOCK-11 `web/build/` |

---

## 16. References

- [pywebview — Freezing](https://pywebview.flowrl.com/guide/freezing.html)
- [PyInstaller documentation](https://pyinstaller.org/)
- [PyInstaller spec files — `datas`](https://pyinstaller.org/en/stable/spec-files.html)
- Roadmap: [001 PR-20..25 § PR-24](../roadmap/001-2026-06-02-pr20-pr25-development-roadmap.md#pr-24--packaging--distribution)
- Prior finalize SAVE policy: [011 finalize spec](011-2026-06-02-finalize-cleanup-pipeline-design.md) (migrate paths via resolver, not behavior change)

---

## Changelog

| Date | Change |
|------|--------|
| 2026-06-02 | Initial spec 012 draft from PR-24 release engineering brief + codebase baseline |
| 2026-06-02 | Grill-me G1–G5 approved; LOCK-G1 (Option C paths), LOCK-G2 (PROD fail-closed); status → **approved** |
