# NovelGuard

로컬 우선 소설 라이브러리 도구 — 폴더 스캔, exact/near/relation 중복 검출, 검토·이동 적용, 품질 이슈 분석, finalize(적용·검증)까지 한 데스크톱 앱에서 처리합니다.

**안전:** 파괴적 파일 이동·삭제는 dry-run 미리보기와 사용자 승인 후에만 실행됩니다.

## 스택

| Layer | Path |
|-------|------|
| UI | `web/` — React + TypeScript + Tailwind v4 ([DESIGN.md](DESIGN.md)) |
| App / bridge | `src/app/` — pywebview `BridgeApi`, contract validation |
| Application | `src/application/` — `LibrarySession`, scan/apply/finalize jobs |
| Domain / infra | `src/domain/`, `src/infrastructure/` |

레이어·IA 정본: [docs/architecture/main-ux-contract.md](docs/architecture/main-ux-contract.md)  
실행·검증 명령: [docs/entry_points.md](docs/entry_points.md)

## 주요 기능 (main)

- **Scan** — `.txt` / `.md` 폴더 스캔, SQLite 인덱스, 스트리밍 해시
- **Resolve & Organize** — 가상화 그리드, keeper/이동 결정, move preview + stale guard, bulk auto-approve job
- **Quality** — 빈 파일·인코딩 등 detect-only 이슈, repair 서브플로우
- **Finalize** — `startFinalizeJob` / `getFinalizeJob` / `cancelFinalize` 비동기 bridge job (UI 폴링·취소)
- **Settings / Logs** — 별도 라우트

브라우저 dev는 `mockBridge`; 데스크톱은 `LibrarySession` 실동작.

## 실행

**Desktop (Windows):**

```bash
pip install -e ".[gui]"
cd web && npm install && npm run build
run.bat
# or: novelguard-webview
```

**Browser dev (mock bridge):**

```bash
cd web && npm install && npm run dev
```

`VITE_USE_MOCK_BRIDGE=true` — [docs/entry_points.md](docs/entry_points.md)

## 검증

```bash
pip install -e ".[dev]"
cd web && npm install

# Python gate (pytest, ruff, mypy, black, web lint + vitest, packaging smokes)
python scripts/verify_phase_completion.py

# Web (touch web/ 시)
npm run lint
npm run test:contracts
npm run build
```

Bridge 계약: `pytest tests/test_bridge_contract.py -v` + `npm run test:contracts`

에이전트·PR 규칙: [AGENTS.md](AGENTS.md)
