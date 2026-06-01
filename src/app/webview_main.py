"""Desktop host: pywebview + built React assets."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
WEB_DIST = REPO_ROOT / "web" / "dist" / "index.html"


def main() -> int:
    try:
        import webview  # type: ignore[import-not-found]
    except ImportError:
        print(
            "Install pywebview: pip install 'novelguard[gui]' or pip install pywebview",
            file=sys.stderr,
        )
        return 1

    if not WEB_DIST.is_file():
        print(f"Build web UI first: cd web && npm run build\nMissing: {WEB_DIST}", file=sys.stderr)
        return 1

    from app.bridge_api import BridgeApi

    api = BridgeApi()
    webview.create_window(
        "NovelGuard",
        WEB_DIST.as_uri(),
        js_api=api,
        width=1280,
        height=800,
    )
    webview.start()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
