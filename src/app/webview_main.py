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
    from app.session_factory import create_library_session

    api = BridgeApi(create_library_session())
    # Use file path (not file:// URI alone) so relative ./assets/* from Vite build resolve.
    webview.create_window(
        "NovelGuard",
        str(WEB_DIST),
        js_api=api,
        width=1280,
        height=800,
        min_size=(1100, 640),
    )
    webview.start()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
