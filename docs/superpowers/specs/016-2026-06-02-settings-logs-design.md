---
title: PR-28 Settings / Logs v1
status: approved
approved: 2026-06-02
date: 2026-06-02
authors: PR-28 brainstorming 2026-06-02 (pre-design + codebase baseline)
parent_spec: docs/superpowers/specs/000-2026-06-01-novelguard-ui-overhaul-design.md
related_specs:
  - docs/superpowers/specs/012-2026-06-02-packaging-distribution-design.md
  - docs/superpowers/specs/011-2026-06-02-finalize-cleanup-pipeline-design.md
  - docs/superpowers/specs/014-2026-06-02-snapshot-invalidation-design.md
roadmap: docs/superpowers/roadmap/002-2026-06-02-pr26-pr30-platform-polish-roadmap.md
pr_label: PR-28
plan: docs/superpowers/plans/022-2026-06-02-pr28-settings-logs.md
prerequisite: PR-23 finalize artifacts; PR-24 runtime paths (`runtime_paths`); PR-26 invalidation (no extra snapshot pollers on Settings/Logs)
---

# 016 — Settings / Logs v1

## Status

**Approved** (2026-06-02) — `/grill-me` complete; blockers resolved. Implementation per [plan 022](../plans/022-2026-06-02-pr28-settings-logs.md).

**Brainstorming outcome (adopted):** Logs live stream = **minimal `queryLogEntries`** from in-process bounded ring buffer. Settings = **effective scan controls only** on Settings route; reserved contract keys without UI. **`openLogsDirectory` deferred.**

---

## Scope sentence

PR-28 replaces `PlaceholderRoute` for **Settings** and **Logs** with minimal v1 surfaces in **one PR** (roadmap Option A). Settings exposes only **effective** scan-default controls (three fields) and retains **AppInfoDiagnostics**. Logs shows a **live log** via `queryLogEntries` only, plus a read-only **artifact metadata** list via `getLogsArtifacts` (no file tail, no artifact body reads). No expert settings tree, no log DB, no shell open, no second snapshot polling loop.

---

## Locked decisions (brainstorming — 2026-06-02)

### LOCK-28 — PR scope (verbatim; roadmap + grill-me 2026-06-02)

```text
PR-28 implements minimal Settings v1 and Logs v1 only.

PR-28 visible Settings v1 exposes only effective scan settings:
- scan.extensionFilter
- scan.includeSubdirs (read-only control — walk is always recursive today)
- scan.includeHidden

scan.incrementalScan and scan.includeSymlinks are reserved contract keys only.
They may be accepted by getAppSetting / setAppSetting for forward compatibility,
but must not be presented as effective user-facing controls until the scanner consumes them.

Duplicate, relation, similarity, conflict policy, performance, theme, density, and expert settings are out of scope unless explicitly listed in this spec.

Existing PR-20 key include_relation remains on the bridge; PR-28 does not add relation/duplicate policy UI on Settings.

Logs v1 live display uses queryLogEntries only.
getLogsArtifacts returns persisted artifact metadata only and must not become a file-tail transport.

The Logs tab must render live log entries only through queryLogEntries.
It must not tail filesystem log files, parse release log files, or read a separate frontend-only log cache.

openLogsDirectory is deferred from PR-28.
PR-28 may expose artifact paths as metadata, but must not add shell/path-opening behavior.

Full log pagination, search UI, structured detail drawer, DB-backed log history, and virtualized log table are deferred.
```

### LOCK-28-LOGS — Runtime logging (grill G3)

```text
Runtime logging
└── SessionLogBuffer (application)
    ├── bounded ring buffer; deterministic sort order (plan 022: oldest-first)
    ├── queryLogEntries({ level?, limit? })
    └── optional file mirror under logs_dir() for support/debug only — never read by Logs UI

Logs tab
└── queryLogEntries only

Artifacts panel
└── getLogsArtifacts only (metadata list; no tail, no open, no body read)
```

### Design locks (brainstorming)

| # | Topic | Lock |
|---|--------|------|
| **L1** | Logs live stream | **`queryLogEntries`** — limit-only; no cursor; no text search |
| **L2** | Logs artifacts | **`getLogsArtifacts`** — artifact **metadata list** only (kinds: audit_tail file, finalize_report, packaging_log); no tail/body/open |
| **L3** | Settings transport | Extend **`getAppSetting` / `setAppSetting`** with typed values for scan keys; persist under PR-24 **`config_dir()`** |
| **L4** | Diagnostics | **Retain** `AppInfoDiagnostics` (`getAppInfo`) on Settings |
| **L5** | Work scan chips | After PR-28, Work scan summary reads **persisted** defaults (snapshot `scanOptions` labels may mirror settings; no duplicate editors on Work) |
| **L6** | `start_scan` | Must pass persisted scan options into session scan path (today `options` ignored) for fields marked **consume** below |
| **L7** | Bridge parity | `queryLogEntries`, `getLogsArtifacts` on RPC parity list + mockBridge behavior tests |
| **L8** | PR-26 | Settings/Logs routes **must not** add `getSnapshot()` polling |

### Grill-me (2026-06-02 — approved)

| # | Topic | Lock | Status |
|---|--------|------|--------|
| **G1** | `incrementalScan` in v1 UI? | **Excluded** — reserved contract key only; not visible/effective until scanner consumes it | **Approved** |
| **G2** | `includeSymlinks` in v1 UI? | **Excluded** — reserved contract key only; not visible until scanner supports symlinks safely | **Approved** |
| **G3** | Log source of truth | **`queryLogEntries`** from in-process **bounded ring buffer**; optional `logs_dir()` mirror for support only | **Approved** |
| **G4** | `openLogsDirectory` | **Defer** — no shell/path-open in PR-28; paths as metadata only | **Approved** |
| **G5** | `getLogsArtifacts` vs `getFinalizeSummary().auditTail` | **Keep `getLogsArtifacts`** — metadata list only; finalize summary tail stays finalize-workspace scoped | **Approved** |
| **G6** | `resetAppSettings` | **Defer** — no reset RPC in v1 | **Approved** |

---

## 1. Problem

### 1.1 Baseline (verified in repo — 2026-06-02)

**Baseline mismatch (do not use as implementation truth):** Pre-design notes referencing legacy **`InMemoryLogSink`**, **`LogsTab`**, **`QSettings`**, or `app/settings/constants.py` describe a **prior GUI inventory**, not the current tree. PR-28 builds on **pywebview + React** only (table below).

| Area | Today |
|------|--------|
| Routes | `web/src/app/App.tsx` → `PlaceholderRoute` for `settings` and `logs` |
| Settings UI | Placeholder copy + **`AppInfoDiagnostics`** only (`PlaceholderRoute.tsx`) |
| Settings bridge | `getAppSetting` / `setAppSetting` — **bool only**; domain key `include_relation` (`AppSettings` in-memory, not persisted to `config_dir`) |
| Scan | `start_scan(options)` accepts dict but **`options` ignored** in `LibrarySession.start_scan`; scanner supports `extensions` + hidden skip in `filesystem_scanner` |
| Work UI | `ScanWorkspace` shows `library.scanOptions` string chips from snapshot (mock labels) |
| Runtime logs path | `runtime_paths.logs_dir()` → `%LOCALAPPDATA%/NovelGuard/logs/` (PR-24 LOCK-G1) — **no bridge read** |
| Apply audit | Per-library `apply-audit.jsonl`; `read_audit_tail` used by **Finalize** summary only — not duplicated as tail content on Logs |
| Finalize outputs | `<libraryRoot>/SAVE/finalize/` per `library_runtime_paths` |

### 1.2 User-visible gap

- Settings/Logs routes still say “v1 shell parity” while Work/FileDock/Quality are product-ready.
- No persisted scan defaults; scan behavior does not follow user intent.
- No unified runtime log surface for support; file logs under `logs_dir()` are invisible to UI.
- Finalize/audit artifacts are only visible indirectly via Finalize workspace.

### 1.3 Risk (why LOCK-28 is grill-heavy)

Combining settings persistence, scan wiring, log buffer, and artifact listing in one PR without hard locks invites a “settings platform” or hybrid log sources (memory vs file vs audit JSONL). This spec enforces **one live log API** and **scan-only** settings scope.

---

## 2. Goals

1. **Settings route:** scan-default controls + existing app info diagnostics; values survive restart via `config_dir()`.
2. **Logs route:** live log from `queryLogEntries`; artifact metadata list from `getLogsArtifacts`; placeholder copy removed.
3. **Bridge:** minimal new surface; mock/Python parity for new methods; extended setting value types documented.
4. **Safety:** no destructive actions on Logs; no new pipeline policy; no extra snapshot pollers.

---

## 3. Non-goals

- Expert settings / full rule editor (000 P2)
- Theme, density, duplicate/relation/similarity/conflict/performance settings UI
- `include_relation` UI (bridge may remain for Work/Resolve consumers)
- Log level/source **filter UI** (API `level` param allowed; no multi-control filter bar)
- `queryLogEntries` cursor, full-text search, job filter, virtualized table, log DB
- Tailing `%LOCALAPPDATA%/NovelGuard/logs/*.log` in the web UI
- `openLogsDirectory` and any shell/path-open (G4)
- Visible UI for `scan.incrementalScan` / `scan.includeSymlinks` (G1/G2)
- `resetAppSettings` RPC (G6)
- Remote log shipping, log-triggered repair
- Split PR-28a/28b (roadmap Option B only via changelog)

---

## 4. Settings v1

### 4.1 UI (`SettingsRoute` replaces placeholder)

Sections:

1. **Scan defaults** — controls for **visible** keys only (§4.2); no disabled “coming soon” toggles for reserved keys.
2. **App info** — move/reuse `AppInfoDiagnostics` unchanged (`data-testid="app-info-diagnostics"`).

Layout: DESIGN.md tokens; single scroll column; no nested settings navigation tree.

### 4.2 Setting keys (domain + bridge)

**Visible on Settings route (effective in PR-28):**

| Key | Type | Default | Scanner consume |
|-----|------|---------|-----------------|
| `scan.extensionFilter` | `string` | `".txt,.md"` | **Yes** — `set[str]` for `scan_folder(extensions=…)` |
| `scan.includeSubdirs` | `boolean` | `true` | **N/A** — read-only control; walk always recursive today |
| `scan.includeHidden` | `boolean` | `false` | **Yes** — when true, do not skip dot dirs/files |

**Reserved contract keys (bridge only; no Settings UI; no scanner effect in PR-28):**

| Key | Type | Default | Notes |
|-----|------|---------|--------|
| `scan.incrementalScan` | `boolean` | `false` | G1 — forward-compatible read/write; must not affect scan |
| `scan.includeSymlinks` | `boolean` | `false` | G2 — forward-compatible read/write; must not affect scan |

**`include_relation`:** unchanged bool key; **no** Settings UI in PR-28.

### 4.3 Bridge contract (Settings)

Extend existing methods (breaking TS shape — coordinated in plan):

```typescript
type AppSettingKey =
  | "include_relation"
  | "scan.extensionFilter"
  | "scan.includeSubdirs"
  | "scan.includeHidden"
  | "scan.incrementalScan"
  | "scan.includeSymlinks";

type AppSettingValue = string | boolean;

type AppSettingResponse = {
  key: AppSettingKey;
  value: AppSettingValue;
  source: "default" | "persisted";
};

getAppSetting(key: AppSettingKey): Promise<AppSettingResponse>;
setAppSetting(key: AppSettingKey, value: AppSettingValue): Promise<AppSettingResponse>;
```

**Persistence:** JSON (or equivalent) under `config_dir()` / `settings.json` — plan 022 locks format and atomic write. In-memory `AppSettings` loads at session/bridge startup.

**Validation:**

- `scan.extensionFilter` — comma-separated extensions; normalize to lowercase; leading dot required per segment; reject empty result set with bridge `rejected` + `INVALID_SETTING_VALUE`.
- Booleans — strict JSON bool on wire.

### 4.4 Work integration

- On successful load, snapshot `library.scanOptions` (or Settings link) reflects human-readable summary of persisted scan defaults — **display only** on Work; editing only on Settings route.
- `startScan()` bridge call passes no per-run overrides in v1 (session reads persisted settings).

---

## 5. Logs v1

### 5.1 UI (`LogsRoute` replaces placeholder)

Two sections (single page):

1. **Live log** — formatted list (table or stacked rows); data **only** from `queryLogEntries`.
2. **Artifacts** — read-only metadata list from `getLogsArtifacts` (paths/labels only; no open, no tail).

Controls (minimal):

- **Refresh** — re-fetch `queryLogEntries` (and artifacts).
- **Clear display** — optional UI-only clear of rendered rows **without** implying server log deletion (if offered, label: “화면 지우기”; does not mutate buffer).
- **Level** — optional single `<select>` bound to `query.level` (not a full filter UI — one control acceptable; grill may defer UI and fix `level` undefined).

No export-to-file requirement in v1 (defer).

### 5.2 `queryLogEntries` (live stream — sole source of truth)

```typescript
type LogLevel = "DEBUG" | "INFO" | "WARNING" | "ERROR";

type LogEntry = {
  timestamp: string; // ISO-8601 UTC with Z
  level: LogLevel;
  message: string;
  logger?: string;
  context?: Record<string, unknown>;
};

type LogEntriesQuery = {
  level?: LogLevel; // minimum severity inclusive — locked in plan 022
  limit?: number;
};

type LogEntriesPage = {
  entries: LogEntry[];
  pageInfo: {
    limit: number;
    hasMore: false;
  };
};

queryLogEntries(query: LogEntriesQuery): Promise<LogEntriesPage>;
```

**v1 limits (LOCK):**

| Rule | Value |
|------|--------|
| Default `limit` | `200` |
| Max `limit` | `500` |
| Cursor | **none** — `hasMore` always `false` |
| Search | **none** |
| DB | **none** |

**Backend (G3 — approved):**

- Application **`SessionLogBuffer`**: bounded ring buffer of `LogEntry`, fed by `logging.Handler` on NovelGuard loggers.
- **`queryLogEntries`** reads buffer only — deterministic **oldest-first** within returned window (plan may not change).
- Optional mirror to `logs_dir()/session-<id>.log` for support — **never** read by Logs UI.
- **Prohibited:** tailing filesystem logs; parsing release log files in UI; React-only log cache not backed by bridge buffer.

### 5.3 API roles (no overlap)

| API | Role |
|-----|------|
| `queryLogEntries` | **Live** app log for current session (ring buffer) |
| `getLogsArtifacts` | **Persisted** support/verification artifact **metadata** on disk |
| `getFinalizeSummary().auditTail` | **Finalize workspace** summary aggregates — unchanged; Logs must not re-fetch this shape for a “tail” panel |

`getLogsArtifacts` **does not replace** `queryLogEntries`. It must not return log line bodies or tail JSONL content.

### 5.4 `getLogsArtifacts` (metadata only)

```typescript
type LogsArtifactKind =
  | "audit_tail"
  | "finalize_report"
  | "packaging_log"
  | "unknown";

type LogsArtifact = {
  id: string;
  kind: LogsArtifactKind;
  label: string;
  path: string; // absolute or library-relative — plan 022 locks display rules
  createdAt?: string;
  sizeBytes?: number;
};

type LogsArtifactsResponse = {
  artifacts: LogsArtifact[];
};

getLogsArtifacts(): Promise<LogsArtifactsResponse>;
```

**v1 listing rules:**

- **`audit_tail`:** one entry for current library `apply-audit.jsonl` when library bound and file exists (metadata only — **no** `read_audit_tail` payload on wire).
- **`finalize_report`:** up to **5** newest report files under `finalize_save_root` (PR-23 layout).
- **`packaging_log`:** optional entry when a known packaging log exists under `logs_dir()` — metadata only.
- **No** open file, open folder, or read body in PR-28 (G4).
- No library selected: `{ artifacts: [] }` — no throw.

**MockBridge:** return stable fixture artifacts when library context exists; empty list otherwise.

---

## 6. Bridge surface summary (PR-28 delta)

| Method | Change |
|--------|--------|
| `getAppSetting` / `setAppSetting` | Extended keys + `AppSettingResponse` |
| `queryLogEntries` | **New** |
| `getLogsArtifacts` | **New** |
| `openLogsDirectory` | **Out of scope** (G4) |
| `resetAppSettings` | **Out of scope** (G6) |

All other bridge methods unchanged. Register new methods in `bridge_parity.py`, `bridgeParity.ts`, `pywebviewBridge`, `mockBridge`, contract tests.

---

## 7. Layering

| Layer | Responsibility |
|-------|----------------|
| `domain/settings_keys.py` | Key constants + defaults |
| `application/` | `SettingsStore` port (load/save config_dir); `SessionLogBuffer` + query; `get_logs_artifacts` use case |
| `infrastructure/` | JSON settings file; log handler; filesystem listing for finalize reports |
| `app/bridge_api.py` | Wire RPC |
| `web/` | `SettingsRoute`, `LogsRoute`; remove placeholder routes for these tabs |

**Invariant:** domain has no filesystem or logging I/O.

---

## 8. Acceptance criteria

1. Navigate **Settings** — **three** visible scan controls only; no incremental/symlinks toggles; restart restores from `config_dir()`.
2. **includeHidden** / **extensionFilter** change scanner behavior on next `start_scan`; reserved keys do **not** change scan behavior if set via bridge.
3. Navigate **Logs** — live list from `queryLogEntries` only after pipeline actions; no placeholder copy; no file tail.
4. **Artifacts** list metadata entries when library/files exist; no tail content, no shell open.
5. No regression: PR-26 invalidation-only refresh; Work/FileDock/Quality grids unchanged.
6. E2E smoke: sidebar → Settings + Logs without bridge fatal error.
7. mockBridge + Python parity tests for new/changed setting types and log query limits.

---

## 9. Test plan (plan 022 — no new files without approval)

- Extend existing bridge parity / contract tests for `queryLogEntries` limit clamp and invalid setting rejection.
- Scanner unit test: `includeHidden` + extension filter honored (existing test module if present).
- E2E: navigate Settings/Logs (existing smoke pattern).

---

## 10. References

- Roadmap LOCK-28: [002 PR-26..30](../roadmap/002-2026-06-02-pr26-pr30-platform-polish-roadmap.md#pr-28--settings--logs-product-surfaces)
- Runtime paths: `src/app/runtime_paths.py`
- Placeholder: `web/src/features/PlaceholderRoute.tsx`
- PR-24 config/logs dirs: [012 packaging](012-2026-06-02-packaging-distribution-design.md)

---

## Changelog

| Date | Change |
|------|--------|
| 2026-06-02 | Initial proposed spec from PR-28 brainstorm (Option B logs, scan subset settings, baseline correction) |
| 2026-06-02 | Grill-me: visible vs reserved scan keys; logs/artifacts boundary; `getLogsArtifacts` metadata DTO; G1–G6 approved |
| 2026-06-02 | Human spec approval; plan 022 authorized |
