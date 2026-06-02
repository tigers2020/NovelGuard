"""Desktop host: pywebview + built React assets."""

from __future__ import annotations

import importlib
import sys
from typing import Any

from app.runtime_paths import frontend_asset_root


def _load_webview() -> Any:
    """Optional GUI dependency (pywebview); resolved at runtime."""
    return importlib.import_module("webview")


def main() -> int:
    try:
        webview = _load_webview()
    except ImportError:
        print(
            "Install pywebview: pip install 'novelguard[gui]' or pip install pywebview",
            file=sys.stderr,
        )
        return 1

    index_path = frontend_asset_root() / "index.html"
    if not index_path.is_file():
        print(
            f"Frontend build not found: {index_path}\n"
            "Run `npm run build` in web/ (output: web/build/).",
            file=sys.stderr,
        )
        return 1

    from app.session_factory import create_bridge_api, create_library_session

    api = create_bridge_api(create_library_session())
    # Use file path (not file:// URI alone) so relative ./assets/* from Vite build resolve.
    webview.create_window(
        "NovelGuard",
        str(index_path),
        js_api=api,
        width=1280,
        height=800,
        min_size=(1100, 640),
    )
    webview.start()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
