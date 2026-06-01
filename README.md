# NovelGuard

프로젝트를 **전면 초기화**한 상태입니다. 도메인·GUI·프론트엔드 코드는 제거되었고, 처음부터 다시 구현할 수 있는 최소 스캐폴드만 남아 있습니다.

## 유지된 것

- Git 저장소(히스토리는 그대로; 이번 초기화는 새 커밋으로 반영)
- [AGENTS.md](AGENTS.md) — 에이전트·검증 게이트
- `.cursor/rules/`, `persona/`, `protocols/` — 개발 절차
- `.venv`, `.env`(로컬, gitignore) — 로컬 환경

## 현재 구조

```
NovelGuard/
├── web/                 # React + Tailwind UI (v1)
├── src/app/             # pywebview host + bridge stub
├── run.bat              # desktop launcher (Windows)
└── docs/superpowers/    # approved spec + plan
```

## 실행

**Desktop (Windows):** `run.bat` or `novelguard-webview` after `pip install -e ".[gui]"` and `cd web && npm run build`

**Browser dev:** `cd web && npm run dev` (mock bridge)

**Python scaffold:** `python src/main.py`

## 검증

```bash
pip install -e ".[dev]"
python scripts/verify_phase_completion.py
```

## 잠긴 폴더

초기화 시 다른 프로세스가 파일을 잡고 있으면 `_delete_*` 이름으로 남을 수 있습니다. IDE·앱을 종료한 뒤 해당 폴더를 수동으로 삭제하세요.

## 다음 단계

1. `docs/superpowers/specs/`에 새 설계 작성 → 승인
2. `docs/superpowers/plans/`에 구현 플랜 작성 → 승인
3. `src/` 백엔드 레이어 + `web/` React UI ([DESIGN.md](DESIGN.md)) 재구축

정본 정책: [AGENTS.md](AGENTS.md)
