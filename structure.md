# NovelGuard Project Structure Index

> Local-first novel library scanner: scan → parse → duplicate/relation detect → review → dry-run preview → apply cleanup.  
> Indexed: **2026-06-03** — regenerate when layers or bridge contracts change materially.

Canonical guides: [AGENTS.md](AGENTS.md) · [DESIGN.md](DESIGN.md) · [docs/entry_points.md](docs/entry_points.md) · [docs/superpowers/README.md](docs/superpowers/README.md)

---

## Top-level layout

```
NovelGuard/
├── src/                    # Python: domain → application → infrastructure → app
├── web/                    # React + TypeScript + Tailwind v4 UI
├── tests/                  # Python contract / scaffold tests
├── scripts/                # verify gate, packaging, hooks, automation CLI
├── automation/             # Hermes queue + Cursor CLI worker (in-repo)
├── docs/                   # Current docs + superpowers specs/plans/roadmaps
├── persona/                # Role cards (opt-in for large tasks)
├── protocols/              # Development protocol
├── packaging/              # Windows packaging + fixture library
├── .cursor/rules/          # Cursor agent rules
├── AGENTS.md               # Cross-agent entrypoint
├── DESIGN.md               # UI tokens and UX
├── pyproject.toml          # Python deps and tool config
└── package.json            # Root npm proxies to web/
```

**Excluded from this index (generated / vendor):** `.venv/`, `node_modules/`, `web/build/`, `.mypy_cache/`, `.pytest_cache/`, `web/test-results/`

---

## Architecture (dependency direction)

| Layer | Path | Role |
|-------|------|------|
| **domain** | `src/domain/` | Pure rules, models, duplicate/relation/quality policies — no I/O |
| **application** | `src/application/` | Use cases, DTO mapping, query builders, **ports** |
| **infrastructure** | `src/infrastructure/` | SQLite index, FS scan/apply/repair, settings JSON |
| **app** | `src/app/` | `BridgeApi`, pywebview host, selection guards, facades |
| **web** | `web/src/` | React UI; talks to Python only via bridge contract |
| **tests** | `tests/` | Bridge parity with `web/src/contracts/` |

```
web (UI) ──bridge──► app/bridge_api.py ──► LibrarySession + use cases ──► ports ◄── infrastructure
```

---

## Entry points

| What | Path / command |
|------|----------------|
| Python scaffold | `src/main.py` (`python src/main.py`) |
| Desktop host | `src/app/webview_main.py` · CLI `novelguard-webview` |
| Bridge surface (Python) | `src/app/bridge_api.py` → `BridgeApi` |
| Bridge surface (TS) | `web/src/bridge/NovelGuardBridge.ts` |
| Web dev | `cd web && npm run dev` (mock: `VITE_USE_MOCK_BRIDGE=true`) |
| Full verify gate | `python scripts/verify_phase_completion.py` |
| E2E smoke | `cd web && npm run test:e2e` → `web/e2e/smoke.spec.ts` |

---

## Python — `src/`

### `src/main.py`

Minimal CLI scaffold entry (desktop uses `webview_main`).

### `src/domain/` — business rules (no I/O)

| Module | Purpose |
|--------|---------|
| `models.py` | `FileRecord`, `DuplicateGroup`, `make_file_id` |
| `duplicate_exact.py` | Exact duplicate grouping by content hash |
| `duplicate_near.py` | Near-duplicate detection (Jaccard fingerprints, union-find) |
| `filename_relation.py` | Filename relation / chapter-sequence grouping |
| `quality.py` | `QualityIssue`, issue IDs |
| `apply_models.py` | Preview/apply operation models |
| `apply_path_policy.py` | Move paths under library root, validation |
| `repair_models.py` | Quality repair operation models |
| `settings_keys.py` | Canonical app setting key constants |

### `src/application/` — use cases and orchestration

| Module | Purpose |
|--------|---------|
| `library_session.py` | **Central orchestrator** for scan, snapshot, queries, apply hooks |
| `dto_mapper.py` | Snapshot and DTO assembly for bridge |
| `scan_settings.py` | Scan option parsing and labels |
| `app_settings.py` | Typed app settings get/set |
| `settings_store.py` | Settings store protocol usage |
| `file_query.py` / `file_row_query.py` | File row paging and filters |
| `file_review_projection.py` | Review projection over file rows |
| `file_row_page_memory.py` | In-memory page cache for file rows |
| `review_query.py` / `review_rows_builder.py` | Resolve grid query + row build |
| `review_decisions.py` / `review_state_merge.py` | Persisted review decisions merge |
| `review_snapshot_counts.py` | Counts for snapshot work section |
| `review_errors.py` | Review-layer error types |
| `duplicate_group_detail.py` | Duplicate group detail DTO |
| `near_duplicate_detect.py` / `near_group_detail.py` | Near-dup pipeline + detail |
| `near_review_rows_builder.py` / `near_batch_id.py` / `near_text_reader.py` | Near-dup rows and batch IDs |
| `relation_membership.py` / `relation_group_detail.py` | Relation groups |
| `relation_review_rows_builder.py` / `relation_batch_id.py` | Relation review rows |
| `quality_analyzer.py` / `quality_query.py` / `quality_rows_builder.py` | Quality scan and grid |
| `quality_issue_detail.py` | Single issue detail |
| `encoding_detect.py` | Encoding detection for quality |
| `plan_fingerprint.py` / `repair_plan_fingerprint.py` / `issue_selection_fingerprint.py` | Stale-preview guards |
| `finalize_runner.py` / `finalize_summary.py` / `finalize_blockers.py` | Finalize verification pipeline |
| `finalize_report.py` / `finalize_audit_tail.py` | Finalize reports and audit tail |
| `audit_log.py` / `log_buffer.py` / `log_query.py` / `logs_artifacts.py` | Logging and log UI support |

#### `src/application/ports/` — interfaces for infrastructure

| Port | File |
|------|------|
| Library index | `library_index.py` |
| Review state persistence | `review_state.py` |
| Filesystem apply (moves) | `filesystem_apply.py` |
| Filesystem repair (quality) | `filesystem_repair.py` |
| Finalize cleanup | `finalize_cleanup.py` |

### `src/infrastructure/` — adapters

| Module | Purpose |
|--------|---------|
| `sqlite_library_index.py` | Primary SQLite library index |
| `sqlite_file_rows_page.py` | Paginated file rows from SQLite |
| `memory_library_index.py` | In-memory index (tests / light paths) |
| `filesystem_scanner.py` | Directory scan |
| `content_hasher.py` | File hashing |
| `local_filesystem_apply.py` | Apply move operations |
| `local_filesystem_repair.py` | Apply quality repairs |
| `finalize_cleanup.py` | Finalize cleanup adapter |
| `json_settings_store.py` | JSON settings persistence |

### `src/app/` — composition and bridge

| Module | Purpose |
|--------|---------|
| `bridge_api.py` | **`BridgeApi`** — pywebview-exposed methods (snake_case) |
| `bridge_contract.py` | Contract constants / shapes shared with tests |
| `bridge_parity.py` | Parity helpers for contract tests |
| `webview_main.py` | pywebview window + static `web/build` |
| `session_factory.py` | Construct `LibrarySession` + dependencies |
| `runtime_paths.py` | App data / library paths |
| `selection_resolve.py` / `selection_guards.py` / `selection_fingerprint.py` | Apply selection validation |
| `build_preview_plan.py` / `move_preview_facade.py` / `preview_apply_guard.py` | Move preview pipeline |
| `build_quality_repair_plan.py` / `quality_repair_facade.py` / `quality_repair_guard.py` | Quality repair preview/apply |
| `apply_resolved_actions.py` / `apply_quality_repair.py` | Apply entrypoints |
| `version.py` / `_build_stamp.py` | Version metadata |

#### `BridgeApi` methods (sync with `NovelGuardBridge`)

`get_snapshot`, `set_work_mode`, `select_folder`, `start_scan`, `cancel_run`,  
`query_review_rows`, `query_quality_rows`, `query_file_rows`,  
`get_duplicate_group_detail`, `get_quality_issue_detail`,  
`get_quality_repair_preview`, `apply_quality_repair`, `discard_quality_repair_preview`,  
`get_move_preview`, `apply_resolved_actions`, `discard_move_preview`,  
`update_review_decisions`,  
`get_app_info`, `get_app_setting`, `set_app_setting`,  
`query_log_entries`, `get_logs_artifacts`,  
`get_finalize_summary`, `run_finalize_verification`, `get_finalize_report`, `cancel_finalize`

---

## Web — `web/src/`

Stack: React 19, TypeScript, Vite, Tailwind v4 (`web/src/styles/globals.css` ← `DESIGN.md`).

### App shell and routing

| Path | Purpose |
|------|---------|
| `main.tsx` | React root |
| `app/App.tsx` | Routes: **work** \| **settings** \| **logs**; global dialogs |
| `app/providers/SnapshotProvider.tsx` | Bridge + snapshot context |
| `app/providers/snapshotHooks.ts` | `useBridge`, `useSnapshot`, refresh helpers |
| `app/providers/snapshotContexts.ts` | Context definitions |

**Note:** `App.tsx` imports `features/logs/LogsRoute` — that folder is not present in the tree yet (logs route may be WIP).

### Bridge layer — `web/src/bridge/`

| File | Purpose |
|------|---------|
| `NovelGuardBridge.ts` | TypeScript bridge interface (camelCase) |
| `pywebviewBridge.ts` | Production adapter → `window.pywebview.api` |
| `mockBridge.ts` | Dev/mock implementation |
| `bridgeFactory.ts` | Select mock vs pywebview vs test |
| `callBridge.ts` | Typed invoke + error mapping |
| `bridgeErrors.ts` / `parseBridgeRejection.ts` | Error types |
| `bridgeHealth.ts` | Connection health |
| `waitForPywebviewApi.ts` | Wait for host API |
| `selectionFingerprint.ts` / `issueSelectionFingerprint.ts` | Client fingerprints for stale guards |
| `snapshotInvalidationSchedule.ts` | Mock invalidation events |
| `mockData.ts`, `mockFileRows.ts`, `mockReviewState.ts`, `mockDuplicateGroupDetail.ts`, `mockQualityIssueDetail.ts` | Mock datasets |
| `testBridge.ts` | E2E/test hook bridge |
| `bridgeParity.test.ts` | Parity with Python contract |

### Contracts — `web/src/contracts/`

Shared fixtures and contract tests aligned with `tests/test_bridge_contract.py`:

`snapshotContract.ts`, `reviewPageContract.ts`, `qualityPageContract.ts`, `fileRowsPageContract.ts`, `movePreviewContract.ts`, `bridgeParity.ts`, `fixtures.ts`, `*.test.ts`

### Types — `web/src/types/`

`snapshot.ts`, `review.ts`, `reviewDecisions.ts`, `quality.ts`, `qualityRepair.ts`, `selection.ts`, `movePreview.ts`, `finalize.ts`, `fileRows.ts`, `logs.ts`, `settings.ts`, `appInfo.ts`, `snapshotInvalidation.ts`

### Layout components — `web/src/components/`

| Area | Files |
|------|-------|
| **layout** | `AppShell.tsx`, `AppHeader.tsx`, `AppSidebar.tsx`, `GlobalCommandBar.tsx`, `ShellFileDock.tsx`, `shellFileDockColumns.ts`, `shellFileDockStorage.ts` |
| **grid** | `VirtualizedDataGrid.tsx`, `ColumnChooser.tsx`, `gridColumnWidths.ts`, `gridColumnMeta.ts`, `virtualWindow.ts` |
| **ui** | `StatChip.tsx` |

### Features — `web/src/features/`

| Area | Key files |
|------|-----------|
| **work** | `WorkRoute.tsx`, `WorkModeTabs.tsx`, `WorkModePanel.tsx` |
| | `ScanWorkspace.tsx` — scan mode |
| | `ResolveAndOrganizeWorkspace.tsx` — resolve mode (master-detail) |
| | `resolve/` — `VirtualizedReviewGrid.tsx`, `DetailPanel.tsx`, `FacetPanel.tsx`, `BatchActionBar.tsx`, `reviewGridColumns.tsx`, `reviewGridLayout.ts` |
| | `QualityWorkspace.tsx`, `quality/` — quality grid + columns/layout/persistence |
| | `FinalizeWorkspace.tsx`, `FinalizeSubflowDialog.tsx` |
| | `ApplySubflowDialog.tsx`, `RepairSubflowDialog.tsx`, `PreflightPipelineDialog.tsx` |
| **settings** | `SettingsRoute.tsx` |
| **diagnostics** | `AppInfoDiagnostics.tsx` |
| **placeholder** | `PlaceholderRoute.tsx` |

**Work modes** (`WorkMode` in snapshot): `scan` · `resolve` · `quality` (finalize flows via resolve + subflow dialogs).

### Perf — `web/src/perf/`

`gridDataPath.test.ts`, `gridDataPath.bench.ts`

### E2E — `web/e2e/`

`smoke.spec.ts` — Playwright smoke (mock bridge failure paths, apply/finalize dialogs)

### Web config (repo root of UI)

| File | Purpose |
|------|---------|
| `web/package.json` | Scripts: `dev`, `build`, `lint`, `test:contracts`, `test:e2e` |
| `web/vite.config.ts` | Vite + dev server (port 5173) |
| `web/playwright.config.ts` | E2E webServer |
| `web/.env.development.example` | Mock bridge env template |

---

## Tests — `tests/`

| File | Purpose |
|------|---------|
| `test_bridge_contract.py` | Python side of bridge contract parity |
| `test_scaffold.py` | Scaffold sanity |
| `fixtures/bridge_contract_fixtures.py` | Shared contract fixtures |

Web contract tests: `cd web && npm run test:contracts`

---

## Scripts — `scripts/`

| Script | Purpose |
|--------|---------|
| `verify_phase_completion.py` | Full gate: pytest → ruff → mypy → black → npm lint |
| `guard_new_tests.py` | Policy guard for new test files |
| `package_windows.py` / `verify_packaging.py` | Windows packaging |
| `perf_file_rows_query.py` | File-rows query perf probe |
| `install_git_hooks.py` / `hooks/pre-commit` | Git hooks |
| `automation_worker.py` / `automation_enqueue.py` | Job worker and enqueue (see `automation/`) |

---

## Automation — `automation/`

| Path | Purpose |
|------|---------|
| `README.md` | Queue + worker quick start |
| `config.example.yaml` | Repo path, Cursor CLI, verify commands |
| `runners/job_worker.py` | Branch → Cursor → verify → result |
| `schemas/job-payload.schema.json` | Hermes / dispatcher JSON contract |
| `prompts/*.md` | implement / review / test_fix templates |

---

## Documentation — `docs/`

| Path | Purpose |
|------|---------|
| `README.md` | Docs index |
| `entry_points.md` | Run, verify, contract, e2e commands |
| `agent-testing-policy.md` | Agent test governance |
| `release/` | Packaging, smoke template, known limitations |
| `superpowers/README.md` | Specs / plans / roadmaps index |
| `superpowers/specs/` | Design specs (`NNN-YYYY-MM-DD-...-design.md`) |
| `superpowers/plans/` | Implementation plans (`...-prNN-...md`) |
| `superpowers/roadmap/` | Program roadmaps (000–003) |
| `superpowers/agent-workflow.md` | Superpowers routing (large tasks, optional) |
| `agent-automation.md` | Hermes + runner topology |

Historical read-only docs may live under `documents/` (empty or archived in this checkout).

---

## Agent / process collateral

| Path | Purpose |
|------|---------|
| `.cursor/rules/` | `00-automation-core`, runner safety, project layers, verify gates, web Tailwind, MCP index, PR finish |
| `automation/` | SQLite job queue, Cursor CLI runner, prompt templates |
| `persona/` | simon (coord), dominic (domain), yuri (app), ada (infra), gina-gui (web), tess (tests), rex (verify) |
| `protocols/` | `development_protocol.md` |

---

## Packaging — `packaging/`

`README.md`, `fixtures/library/` — sample texts for packaging smoke.

---

## CI

`.github/workflows/ci.yml` — repository CI workflow.

---

## Core user flow (code map)

1. **Scan** — UI `ScanWorkspace` → `start_scan` → `library_session` + `filesystem_scanner` → SQLite index  
2. **Exact dupes** — `domain/duplicate_exact` → review rows  
3. **Near dupes** — `near_duplicate_detect` + `duplicate_near`  
4. **Relations** — `filename_relation` + relation row builders  
5. **Resolve review** — `ResolveAndOrganizeWorkspace` ↔ `query_review_rows`, `update_review_decisions`, group detail  
6. **Quality** — `quality_analyzer` ↔ `QualityWorkspace`  
7. **Preview apply** — `get_move_preview` / guards → `ApplySubflowDialog` → `apply_resolved_actions`  
8. **Repair** — `get_quality_repair_preview` → `RepairSubflowDialog` → `apply_quality_repair`  
9. **Finalize** — `FinalizeWorkspace` / `FinalizeSubflowDialog` ↔ finalize runner + report  

---

## Quick file counts (source only)

| Area | ~Files |
|------|--------|
| `src/**/*.py` | 89 |
| `web/src/**/*.{ts,tsx}` | 105+ |
| `tests/` | 5 |
| `docs/superpowers/` | 60+ markdown |

---

*To refresh this index after large refactors: rescan `src/`, `web/src/`, and `BridgeApi` / `NovelGuardBridge` method lists.*
