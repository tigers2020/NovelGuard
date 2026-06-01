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
python scripts/verify_phase_completion.py
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

## Deferred: TanStack Table (PR-12)

v1 review/quality grids use **TanStack Virtual** + CSS grid columns only. **TanStack Table** (sorting, column resize, header APIs) is deferred to **PR-12** per `docs/superpowers/plans/2026-06-01-novelguard-ui-overhaul.md` and `docs/superpowers/plans/2026-06-01-novelguard-ui-e2e-smoke.md` non-goals.
