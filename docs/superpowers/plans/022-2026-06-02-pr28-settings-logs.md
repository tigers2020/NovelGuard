# PR-28: Settings / Logs v1 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace Settings/Logs placeholders with minimal v1 routes: persisted **effective** scan defaults (3 visible controls), `queryLogEntries` live log from in-process ring buffer, and `getLogsArtifacts` metadata-only listing — no file tail, no shell open.

**Architecture:** Extend `AppSettings` + JSON file under `config_dir()` (PR-24); wire `LibrarySession.start_scan` → `filesystem_scanner` with extension/hidden flags; add `SessionLogBuffer` + `logging.Handler` in application layer; bridge returns dict DTOs for settings/logs; React `SettingsRoute` / `LogsRoute` call bridge only (PR-26: no new snapshot pollers).

**Tech Stack:** Python 3.12 (`src/application`, `src/infrastructure`, `src/app/bridge_api.py`); React 19 + Tailwind v4 (`web/`); pytest + Vitest + Playwright smoke.

**Spec:** [016-2026-06-02-settings-logs-design.md](../specs/016-2026-06-02-settings-logs-design.md) (**approved** 2026-06-02 — LOCK-28, G1–G6)

**Plan status:** **Approved** (2026-06-02)

**Prerequisite:** Spec 016 approved; PR-24 `runtime_paths`; PR-23 finalize SAVE layout; PR-26 invalidation on `SnapshotProvider`

**Parent:** [002 PR-26..30 roadmap](../roadmap/002-2026-06-02-pr26-pr30-platform-polish-roadmap.md)

**Test policy:** Extend **`tests/test_bridge_contract.py`**, **`web/src/bridge/bridgeParity.test.ts`**, **`web/e2e/smoke.spec.ts`** — **no new test files** without `TEST_ALLOWED`.

**Scope freeze (LOCK-28):** No `openLogsDirectory`; no `resetAppSettings`; no incremental/symlinks Settings UI; no log DB/cursor/search/virtualized table; no artifact body/tail/open; no second `getSnapshot()` loop on Settings/Logs; no expert settings / theme / duplicate policy UI.

---

## Plan-locked constants

| Constant | Value |
|----------|--------|
| Settings file | `config_dir() / "settings.json"` |
| Visible setting keys | `scan.extensionFilter`, `scan.includeSubdirs`, `scan.includeHidden` |
| Reserved keys (bridge only) | `scan.incrementalScan`, `scan.includeSymlinks` |
| Default `scan.extensionFilter` | `".txt,.md"` |
| Invalid setting reason | `INVALID_SETTING_VALUE` |
| Log buffer capacity | `2000` entries (ring) |
| `queryLogEntries` default `limit` | `200` |
| `queryLogEntries` max `limit` | `500` |
| Log sort order | **oldest-first** within returned window |
| Finalize artifacts max | `5` newest under `finalize_save_root` |
| Artifact path display | **absolute** `str(path)` on wire (UI may truncate visually) |

### LOCK-P28-1 — `queryLogEntries.level` semantics

**Minimum severity inclusive** (not exact match).

```text
Severity rank: DEBUG=10, INFO=20, WARNING=30, ERROR=40
When query.level is set, return entries with entry.level rank >= query.level rank.
When query.level is omitted, return all levels.
Invalid level string → bridge rejected INVALID_LOG_LEVEL (add to contract).
```

Python and mockBridge **must** share the same filter function (export from TS `logLevelRank` + Python mirror in `application/log_query.py`).

### LOCK-P28-2 — Settings wire shape

`get_app_setting` / `set_app_setting` return **dict** (not bare bool):

```python
{"key": "scan.includeHidden", "value": False, "source": "persisted"}
```

`include_relation` remains bool-valued in `value`. Tests that asserted `api.get_app_setting("include_relation") is False` become `["value"] is False`.

### LOCK-P28-4 — Log handler attachment

Attach `SessionLogHandler` once to the **process root logger**, not only to `logging.getLogger("novelguard")`.

The handler must filter accepted records to NovelGuard-owned logger prefixes:

- `app`
- `application`
- `domain`
- `infrastructure`

Plan implementation may include `novelguard` as an additional accepted prefix, but attaching **only** to `novelguard` is **forbidden** because current module loggers may not be children of that name.

Tests must include at least one probe from `logging.getLogger("application.contract_probe")`, not only `logging.getLogger("novelguard")`.

---

## File map

| File | Action |
|------|--------|
| `src/domain/settings_keys.py` | **Modify** — scan key constants + defaults |
| `src/application/app_settings.py` | **Modify** — typed values, reserved keys, defaults |
| `src/application/settings_store.py` | **Create** — load/save/validate settings JSON |
| `src/application/log_buffer.py` | **Create** — `SessionLogBuffer`, `SessionLogHandler` + root attach with prefix filter (LOCK-P28-4) |
| `src/application/log_query.py` | **Create** — `query_log_entries`, level rank filter |
| `src/application/logs_artifacts.py` | **Create** — metadata listing (audit, finalize, packaging) |
| `src/application/scan_settings.py` | **Create** — parse extension filter → `set[str]` |
| `src/infrastructure/json_settings_store.py` | **Create** — atomic write to `config_dir/settings.json` |
| `src/infrastructure/filesystem_scanner.py` | **Modify** — `include_hidden: bool` parameter |
| `src/application/library_session.py` | **Modify** — persist settings, consume on scan, log buffer, bridge methods |
| `src/application/dto_mapper.py` | **Modify** — `scanOptions` labels from persisted settings |
| `src/app/session_factory.py` | **Modify** — pass `include_hidden` + extensions into scan |
| `src/app/bridge_api.py` | **Modify** — `query_log_entries`, `get_logs_artifacts`, settings dict responses |
| `src/app/bridge_contract.py` | **Modify** — validate new page shapes |
| `src/app/bridge_parity.py` | **Modify** — register RPC names |
| `tests/test_bridge_contract.py` | **Extend** — settings dict, log limit, level filter, scan hidden, artifacts |
| `web/src/types/settings.ts` | **Modify** — `AppSettingKey`, `AppSettingResponse` |
| `web/src/types/logs.ts` | **Create** — log + artifact types |
| `web/src/bridge/NovelGuardBridge.ts` | **Modify** — new methods + settings return type |
| `web/src/bridge/pywebviewBridge.ts` | **Modify** — wire RPC |
| `web/src/bridge/mockBridge.ts` | **Modify** — settings persist mock, log buffer, artifacts fixture |
| `web/src/contracts/bridgeParity.ts` | **Modify** — `query_log_entries`, `get_logs_artifacts` |
| `web/src/bridge/bridgeParity.test.ts` | **Extend** — parity + level filter |
| `web/src/features/settings/SettingsRoute.tsx` | **Create** |
| `web/src/features/logs/LogsRoute.tsx` | **Create** |
| `web/src/app/App.tsx` | **Modify** — route to new components |
| `web/e2e/smoke.spec.ts` | **Extend** — Settings + Logs navigation |
| `docs/superpowers/specs/016-2026-06-02-settings-logs-design.md` | **Modify** — plan link when done |
| `docs/superpowers/roadmap/002-2026-06-02-pr26-pr30-platform-polish-roadmap.md` | **Modify** — PR-28 status rows |

---

## LOCK-P28-3 — Green commits

Every task commit must leave touched tests green:

- Python: `pytest tests/test_bridge_contract.py -q` (or narrowed `-k` for touched tests)
- Web: `cd web && npm run test -- src/bridge/bridgeParity.test.ts`
- Before PR close: `python scripts/verify_phase_completion.py`

---

### Task 0: Plan approval gate

**Gate passed 2026-06-02 — Tasks 1–12 may proceed.**

- [x] Reviewer confirms plan matches spec 016 LOCK-28 and LOCK-P28-1..4
- [x] Update this file: `Plan status: **Approved** (2026-06-02)`
- [x] Roadmap PR-28 row → plan approved

---

### Task 1: Domain keys + settings defaults

**Files:**
- Modify: `src/domain/settings_keys.py`
- Modify: `src/application/app_settings.py`

- [x] **Step 1:** Add constants:

```python
SETTINGS_KEY_SCAN_EXTENSION_FILTER = "scan.extensionFilter"
SETTINGS_KEY_SCAN_INCLUDE_SUBDIRS = "scan.includeSubdirs"
SETTINGS_KEY_SCAN_INCLUDE_HIDDEN = "scan.includeHidden"
SETTINGS_KEY_SCAN_INCREMENTAL = "scan.incrementalScan"
SETTINGS_KEY_SCAN_INCLUDE_SYMLINKS = "scan.includeSymlinks"

VISIBLE_SCAN_KEYS = frozenset({...})
RESERVED_SCAN_KEYS = frozenset({incremental, symlinks})
ALL_SETTING_KEYS = frozenset({include_relation, ...scan keys})
```

- [x] **Step 2:** Extend `AppSettings` with `get_value(key) -> tuple[value, source]` and `set_value(key, value)` supporting `str | bool`; reserved keys writable but documented no-op for scan in session.

- [x] **Step 3:** Run `pytest tests/test_bridge_contract.py -k include_relation -q` — still green after later bridge shape change in Task 4.

---

### Task 2: JSON settings persistence

**Files:**
- Create: `src/infrastructure/json_settings_store.py`
- Create: `src/application/settings_store.py`

- [ ] **Step 1:** `JsonSettingsStore(path: Path)` — load dict on init; `save()` writes temp file + `os.replace` atomic rename.

- [ ] **Step 2:** `SettingsStore` port wraps infra; merges persisted values over defaults; returns `source: "persisted" | "default"`.

- [ ] **Step 3:** Wire store path `config_dir() / "settings.json"` via `runtime_paths.config_dir()` in `session_factory` or `BridgeApi` construction (ensure dir exists).

---

### Task 3: Scan settings parser + scanner `include_hidden`

**Files:**
- Create: `src/application/scan_settings.py`
- Modify: `src/infrastructure/filesystem_scanner.py`
- Test: `tests/test_bridge_contract.py`

- [ ] **Step 1:** `parse_extension_filter(raw: str) -> set[str]` — split comma, strip, lower, require leading `.`, min one extension or raise `SettingsValidationError`.

- [ ] **Step 2:** Add `include_hidden: bool = False` to `scan_folder`:

```python
if not include_hidden:
    dirnames[:] = [d for d in dirnames if not d.startswith(".")]
    # skip dot files (existing)
else:
    # do not filter dot dirs/files by name prefix
```

- [ ] **Step 3:** Extend `test_scan_folder_finds_txt_and_md` or add `test_scan_folder_include_hidden_finds_dotfile` in **`tests/test_bridge_contract.py`** (existing file).

- [ ] **Step 4 (recommended):** `parse_extension_filter` rejects empty/whitespace-only, bare `txt` (no dot), lone `.`, and `*.txt` patterns.

Run: `pytest tests/test_bridge_contract.py -k scan_folder -q`

---

### Task 4: LibrarySession — settings dict API + scan consume

**Files:**
- Modify: `src/application/library_session.py`
- Modify: `src/app/session_factory.py`
- Modify: `src/application/dto_mapper.py`
- Modify: `src/app/bridge_api.py`
- Test: `tests/test_bridge_contract.py`

- [ ] **Step 1:** Replace bool-only `get_app_setting` / `set_app_setting` with dict responses per LOCK-P28-2; map `SettingsValidationError` → `BridgeCallError` / rejection `INVALID_SETTING_VALUE`.

- [ ] **Step 2:** In `start_scan`, read `scan.extensionFilter` + `scan.includeHidden`; call `_scan_folder(..., extensions=parsed, include_hidden=...)`. Reserved keys **must not** alter scan.

- [ ] **Step 3:** `build_snapshot` / `dto_mapper` — build `scanOptions` human labels from persisted values (e.g. `".txt, .md"`, `"숨김 파일 포함"` when hidden true); remove hardcoded mock-only list in Python path.

- [ ] **Step 4:** Update contract tests:

```python
payload = api.get_app_setting("include_relation")
assert payload["value"] is False
api.set_app_setting("scan.includeHidden", True)
# hidden dotfile appears after start_scan + idle
```

Run: `pytest tests/test_bridge_contract.py -k "include_relation or app_setting or scan" -q`

---

### Task 5: SessionLogBuffer + `query_log_entries`

**Files:**
- Create: `src/application/log_buffer.py`
- Create: `src/application/log_query.py`
- Modify: `src/application/library_session.py`
- Modify: `src/app/bridge_api.py`
- Modify: `src/app/session_factory.py` (attach handler at bridge boot)
- Test: `tests/test_bridge_contract.py`

- [ ] **Step 1:** `SessionLogBuffer(maxlen=2000)` thread-safe deque; `append(entry_dict)`; `query(level, limit) -> list` oldest-first, apply LOCK-P28-1 filter, clamp limit 1..500 default 200.

- [ ] **Step 2:** `SessionLogHandler(logging.Handler)` formats records to `LogEntry` dict (`timestamp` ISO Z, `level`, `message`, `logger`).

- [ ] **Step 3:** Attach handler once to the **process root logger** with a NovelGuard-prefix filter (`app`, `application`, `domain`, `infrastructure`, optionally `novelguard`). Do **not** attach only to `logging.getLogger("novelguard")`. Single handler per process (LOCK-P28-4).

- [ ] **Step 4:** `BridgeApi.query_log_entries(query: dict) -> dict` with `pageInfo.hasMore is False`.

- [ ] **Step 5:** Tests (LOCK-P28-4 probe):

```python
logging.getLogger("application.contract_probe").info("contract probe")
page = api.query_log_entries({"limit": 10})
assert any("contract probe" in e["message"] for e in page["entries"])

logging.getLogger("application.contract_probe").info("info level msg")
logging.getLogger("application.contract_probe").warning("warn level msg")
page_warn = api.query_log_entries({"level": "WARNING", "limit": 50})
assert any(e["message"] == "warn level msg" for e in page_warn["entries"])
assert not any(e["message"] == "info level msg" for e in page_warn["entries"])
```

---

### Task 6: `get_logs_artifacts` metadata

**Files:**
- Create: `src/application/logs_artifacts.py`
- Modify: `src/application/library_session.py`
- Modify: `src/app/bridge_api.py`
- Test: `tests/test_bridge_contract.py`

- [ ] **Step 1:** `list_logs_artifacts(session) -> {"artifacts": [...]}`:

  - `audit_tail`: if `audit_log_path.is_file()` → id stable hash, `path` absolute, `sizeBytes`, `createdAt` from mtime.
  - `finalize_report`: glob `finalize_save_root/<session_id>/finalize_*.json`, newest 5.
  - `packaging_log`: optional single `logs_dir()/novelguard.log` if exists.
  - No file reads beyond stat/listdir.

- [ ] **Step 2:** Empty library → `{"artifacts": []}`.

- [ ] **Step 3:** Contract test with tmp library + touch audit file → one `audit_tail` artifact.

---

### Task 7: Bridge contract + parity lists

**Files:**
- Modify: `src/app/bridge_contract.py`
- Modify: `src/app/bridge_parity.py`
- Modify: `web/src/contracts/bridgeParity.ts`

- [ ] **Step 1:** Validators `validate_log_entries_page`, `validate_logs_artifacts_response`, `validate_app_setting_response`.

- [ ] **Step 2:** Append `"query_log_entries"`, `"get_logs_artifacts"` to `PYWEBVIEW_API_METHODS` and `bridgeParity.ts` `PYWEBVIEW_RPC_METHODS`.

- [ ] **Step 3:** Run `pytest tests/test_bridge_contract.py -k "parity or log_entries or logs_artifacts" -q`

---

### Task 8: TypeScript bridge + mock parity

**Files:**
- Create: `web/src/types/logs.ts`
- Modify: `web/src/types/settings.ts`
- Modify: `web/src/bridge/NovelGuardBridge.ts`
- Modify: `web/src/bridge/pywebviewBridge.ts`
- Modify: `web/src/bridge/mockBridge.ts`
- Modify: `web/src/bridge/bridgeParity.test.ts`

- [ ] **Step 1:** Add types per spec §4.3 / §5.2 / §5.4.

- [ ] **Step 2:** `pywebviewBridge` — `call(api, "query_log_entries", query)`, `get_logs_artifacts`.

- [ ] **Step 3:** `mockBridge`:

  - In-memory settings map seeded from defaults; `getAppSetting` returns `{ key, value, source }`.
  - Ring buffer array for logs; push on `startScan` / pipeline simulation; `queryLogEntries` uses shared `filterByMinLevel` (LOCK-P28-1).
  - `getLogsArtifacts` returns fixture list when `state.folderPath` set.

- [ ] **Step 4:** `bridgeParity.test.ts` — level filter: INFO query excludes DEBUG-only entries in mock.

Run: `cd web && npm run test -- src/bridge/bridgeParity.test.ts`

---

### Task 9: `SettingsRoute` UI

**Files:**
- Create: `web/src/features/settings/SettingsRoute.tsx`
- Modify: `web/src/app/App.tsx`

- [ ] **Step 1:** Form: extension filter text input; include subdirs checkbox **disabled** with helper text (e.g. “현재는 항상 하위 폴더를 포함합니다”); include hidden toggle.

- [ ] **Step 2:** Load on mount via `getAppSetting` for three visible keys; `setAppSetting` on change with inline error on rejection.

- [ ] **Step 3:** Embed `<AppInfoDiagnostics />` below scan section.

- [ ] **Step 4:** `data-testid`: `settings-route`, `settings-scan-extension`, `settings-scan-hidden`, `settings-scan-subdirs`.

- [ ] **Step 5:** `App.tsx` — `route === "settings"` → `<SettingsRoute />`.

---

### Task 10: `LogsRoute` UI

**Files:**
- Create: `web/src/features/logs/LogsRoute.tsx`
- Modify: `web/src/app/App.tsx`

- [ ] **Step 1:** Live section: `useEffect` fetch `queryLogEntries({ limit: 200 })`; render stacked rows (`timestamp`, `level`, `message`).

- [ ] **Step 2:** Optional refresh button; optional “화면 지우기” clears local React state only (does not call bridge).

- [ ] **Step 3:** Optional single level `<select>` → passes `level` to query (uses LOCK-P28-1).

- [ ] **Step 4:** Artifacts section: `getLogsArtifacts()` → list `label` + monospace `path` (truncate CSS); **no** click/open handlers.

- [ ] **Step 5:** **No** `getSnapshot()` polling — refresh logs on mount + manual refresh only (PR-26 L8).

- [ ] **Step 6:** `data-testid`: `logs-route`, `logs-live-list`, `logs-artifacts-list`.

- [ ] **Step 7:** `App.tsx` — `route === "logs"` → `<LogsRoute />`.

---

### Task 11: E2E smoke

**Files:**
- Modify: `web/e2e/smoke.spec.ts`

- [ ] **Step 1:**

```typescript
test("Settings route loads diagnostics", async ({ page }) => {
  await page.getByRole("button", { name: /설정|Settings/i }).click();
  await expect(page.getByTestId("settings-route")).toBeVisible();
  await expect(page.getByTestId("app-info-diagnostics")).toBeVisible();
});

test("Logs route loads live and artifacts sections", async ({ page }) => {
  await page.getByRole("button", { name: /로그|Logs/i }).click();
  await expect(page.getByTestId("logs-route")).toBeVisible();
  await expect(page.getByTestId("logs-live-list")).toBeVisible();
  await expect(page.getByTestId("logs-artifacts-list")).toBeVisible();
});
```

Run: `cd web && npm run test:e2e` (or project e2e script from `package.json`).

---

### Task 12: Docs + verification closeout

**Files:**
- Modify: `docs/superpowers/specs/016-2026-06-02-settings-logs-design.md`
- Modify: `docs/superpowers/roadmap/002-2026-06-02-pr26-pr30-platform-polish-roadmap.md`
- Modify: this plan → `Plan status: **Complete**`

- [ ] **Step 1:** Run `python scripts/verify_phase_completion.py` — record pass/fail in PR notes.

- [ ] **Step 2:** Roadmap PR-28 → **Done** when merged.

---

## Acceptance mapping (spec §8)

| Criterion | Task |
|-----------|------|
| Settings 3 controls, restart persist | 2, 4, 9 |
| Scanner honors extension + hidden | 3, 4 |
| Reserved keys no scan effect | 1, 4 |
| Logs live via `queryLogEntries` only | 5, 10 |
| Artifacts metadata only | 6, 10 |
| No extra snapshot poller | 10 |
| E2E Settings/Logs | 11 |
| Bridge parity | 7, 8 |

---

## Risks / notes

- **Breaking change:** `get_app_setting` return shape — update all Python/TS call sites in one PR slice (Task 4 + 8).
- **File mirror:** optional; defer if timeboxed — buffer alone satisfies spec.
- **Sidebar labels:** match existing `AppSidebar` i18n pattern (Korean labels in smoke regex above).

---

## Changelog

| Date | Change |
|------|--------|
| 2026-06-02 | Initial plan 022 from approved spec 016; LOCK-P28-1 minimum severity inclusive |
| 2026-06-02 | Plan approved; LOCK-P28-4 root logger attach + `application.contract_probe` test |
