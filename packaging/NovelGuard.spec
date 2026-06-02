# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller onedir spec for NovelGuard desktop (PR-24). Build: see packaging/README.md."""

from pathlib import Path

ROOT = Path(SPECPATH).parent
WEB_BUILD = ROOT / "web" / "build"
ENTRYPOINT = ROOT / "src" / "app" / "webview_main.py"

if not (WEB_BUILD / "index.html").is_file():
    raise FileNotFoundError(
        f"Frontend build not found: {WEB_BUILD / 'index.html'}. "
        "Run `npm run build` in web/ before packaging."
    )

datas = [
    (str(WEB_BUILD), "web/build"),
]

hiddenimports: list[str] = [
    "webview",  # delayed import in webview_main; PyInstaller warn-NovelGuard.txt
]

excludes = [
    "pytest",
    "unittest",
]

a = Analysis(
    [str(ENTRYPOINT)],
    pathex=[str(ROOT / "src")],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="NovelGuard",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="NovelGuard",
)
