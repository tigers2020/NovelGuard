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

## Web UI (production build)

```bash
cd web
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
