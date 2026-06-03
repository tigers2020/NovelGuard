# Packaging smoke checklist (PR-44)

Post–UI-overhaul (`PR-33`..`PR-43`) manual smoke for the **Windows onedir** package. Use **fixture library only** for any destructive path.

## Automated gates (no exe launch)

| Command | When |
|---------|------|
| `python scripts/verify_packaging.py` | CI / every phase gate |
| `python scripts/smoke_packaged_ui.py` | Same (source markers; optional warnings for stale `web/build` / `dist/`) |
| `python scripts/smoke_packaged_ui.py --require-build` | After `npm run build` or `package_windows.py` (strict bundle markers) |

`python scripts/package_windows.py` runs strict UI marker checks after PyInstaller.

## Build

```bash
pip install -e ".[gui]"
pip install pyinstaller
cd web && npm install && cd ..
python scripts/package_windows.py
```

Record output paths and `build-manifest.json` in [smoke-record-template.md](smoke-record-template.md).

## Manual launch matrix

| # | Area | Steps | Pass criteria |
|---|------|--------|----------------|
| 1 | Launch | `dist/NovelGuard/NovelGuard.exe` | Window opens; no `PRODUCTION_BRIDGE_UNAVAILABLE` |
| 2 | App info | Settings → 앱 정보 | `buildType=packaged`; version visible |
| 3 | Scan (PR-35) | Work → Scan; select `packaging/fixtures/library/`; **스캔 시작** | `scan-section` completes; summary visible |
| 4 | 3-mode shell (PR-34) | Tabs: Scan / Resolve / Quality | Single active panel; no hub scroll regression |
| 5 | FileDock (PR-38) | Expand dock; sort; **스캔으로** / **검토로** links | Dock `data-state` expanded; cross-links switch mode |
| 6 | Resolve (PR-36) | Resolve grid loads; scroll; optional row select | Grid rows visible; no white screen |
| 7 | Move apply (PR-37) | Move plan preview → apply on fixture (non-destructive preview OK) | Apply dialog completes or shows expected block |
| 8 | Finalize (PR-37/41) | **최종 검증** dialog; summary; optional cleanup preview | Dialog opens; blockers/warnings readable; run only on fixture if clearing blockers |
| 9 | Logs (PR-40) | Logs route; search; artifact row | Live list + artifacts; search filters |
| 10 | Settings (PR-40) | Section nav (scan / app) | Sections switch without error |
| 11 | Shutdown | Close app | Clean exit; logs under `%LOCALAPPDATA%/NovelGuard/logs/` |
| 12 | Bundle integrity | Inspect `dist/NovelGuard/_internal/web/build/` | No writes during run; `index.html` present |

## Destructive (fixture only)

- Move apply, finalize cleanup, or repair: **`packaging/fixtures/library/`** only.
- Outputs under `<fixture>/SAVE/` when applicable.

## Failures → doc updates

| Symptom | Update |
|---------|--------|
| Missing UI after package | Rebuild frontend; run `smoke_packaged_ui.py --require-build` |
| WebView2 missing | [packaging-windows.md](packaging-windows.md) troubleshooting |
| Bridge unavailable in exe | Do not smoke via browser `index.html` |
| New platform blocker | [known-limitations.md](known-limitations.md) + roadmap 003 changelog |

## Related

- [smoke-record-template.md](smoke-record-template.md)
- [packaging-windows.md](packaging-windows.md)
- Spec 012 · Plan 018 · Plan [038](../superpowers/plans/038-2026-06-02-infra-release-pr44-packaging-smoke.md)
