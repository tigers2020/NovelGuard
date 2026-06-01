# Entry points

## Python scaffold

```bash
python src/main.py
```

## Web UI (development)

```bash
cd web
npm install
npm run dev
```

Open http://localhost:5173 — uses `mockBridge` in the browser.

## Web UI (lint / build)

From repo root (proxies to `web/`):

```bash
npm run lint
npm run build
```

Or from `web/` directly:

```bash
cd web
npm run lint
npm run build
```

Output: `web/dist/`

## Desktop (pywebview smoke)

Requires built `web/dist/` and optional dependency:

```bash
pip install -e ".[gui]"
novelguard-webview
# or: python src/app/webview_main.py  (with PYTHONPATH=src)
```

React loads `createPywebviewBridge()` when `window.pywebview.api` is present; methods are snake_case on the Python `BridgeApi` class (`src/app/bridge_api.py`).

## Verification

```bash
pip install -e ".[dev]"
cd web && npm install
python scripts/verify_phase_completion.py
```

Runs `pytest` → `ruff` → `mypy` → `black --check` → `npm run lint` (fail-fast). For web-only checks without the Python gate:

```bash
npm run lint
cd web && npm run build
```

## Contract tests (PR-10)

```bash
cd web && npm run test:contracts
pytest tests/test_bridge_contract.py -v
```

## E2E smoke (PR-11)

```bash
cd web
npx playwright install chromium
npm run test:e2e
```

Uses Vite dev server (`playwright.config.ts` `webServer`). Injects `__NOVELGUARD_TEST_BRIDGE_FAIL__` for failure-path smoke tests.

## Grid perf (PR-12)

```bash
cd web
npm run test:perf
npm run bench:grid
```

`test:perf` gates DOM virtualization bounds and filter+paginate latency. Resolve grid uses TanStack Table + Virtual; optional columns via **열 선택** chooser.

## Preview token / stale apply (PR-13)

Spec: `docs/superpowers/specs/01-2026-06-01-pr13-preview-token-stale-apply-design.md`

Bridge methods (TS camelCase / Python snake_case):

- `getMovePreview` / `get_move_preview` — returns `previewToken`, `libraryRevision`, `selectionFingerprint`, `rows`, `summary`
- `applyResolvedActions` / `apply_resolved_actions` — requires `{ selection, previewToken }`; no filesystem mutation in PR-13
- `discardMovePreview` / `discard_move_preview` — idempotent cleanup when Apply dialog closes

**Note:** “token” here is a preview–apply correlation id, not `DESIGN.md` color/spacing design tokens.

`AppSnapshot.work.resolve.libraryRevision` is required for library stale detection in the UI.

E2E hook (mock only): `window.__NOVELGUARD_TEST_BUMP_REVISION__()` bumps revision for stale-banner smoke.
