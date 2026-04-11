# AGENTS.md

Cursor AI용 NovelGuard 프로젝트 가이드. [AGENTS.md](https://agents.md/) 표준.

> 핵심: `.cursor/rules/root.mdc`가 최상위 사전 지시서. 이 문서는 원칙과 운영 게이트만 짧게 잡고, 세부 절차는 `.cursor/rules/`와 `persona/`로 위임한다.

---

## 진행 방식: Persona Dialogue 3단계

모든 코딩·진행은 아래 3단계를 따른다. 자연스러운 구어체로 짧게 쓴다.

1. `[시몬]`이 요청을 요약하고 책임 소제를 나눈다.
2. 배정받은 담당자가 한두 문장으로 접근 방식을 브리핑한다.
3. 그 뒤에만 코드 작성·수정을 진행한다.

구현이 끝나면 `[테스]`가 테스트를 맡고, `[렉스]`가 검증 파이프라인을 실행한다.

레이어 빠른 매핑:

| 역할 | 담당 |
|------|------|
| 시몬 | 분배·조율·게이트 |
| 도미닉 | `src/domain/` |
| 유리 | `src/application/` |
| 아다 | `src/infrastructure/` |
| 지나 | `src/gui/` (UI) |
| 테스 | `tests/` |
| 렉스 | 검증 파이프라인 |

상세 절차와 카드:

- `.cursor/rules/persona-dialogue.mdc`
- `persona/README.md`

---

## 기획과 코딩의 분리

원칙: 사람이 문서로 된 계획을 검토·승인하기 전까지 에이전트는 구현으로 넘어가지 않는다.

고정 게이트:

- 리서치: 관련 코드와 규칙을 읽고 `documents/`에 조사 문서를 남긴다.
- 플랜: 변경 접근, 대상 경로, 트레이드오프를 담은 플랜 MD를 `documents/`에 저장한다.
- 승인: 사람이 플랜 문서 본문에서 검토·수정·승인한다.
- 구현: 승인 후에만 코드 작성·수정으로 넘어간다.

시몬은 플랜이 닫히기 전까지 3단계 구현 진입을 허용하지 않는다.

---

## 프로젝트 개요

**NovelGuard** — 텍스트 소설 파일 중복 탐지·정리 도구.

**현행 구조·진입점 문서 정본**: `docs/current_architecture.md` (버전·의존성 하한은 `pyproject.toml`). 파일명 파싱, 포함/버전 관계 판정, 해시 기반 완전 일치, 유사도 탐지를 조합하여 안전하게 중복을 정리한다.

워크플로우: 스캔 → 파일명 파싱 → Blocking → 관계 탐지 → (Exact/Near) → 그룹 생성 → Dry-run 미리보기 → 사용자 승인 → 이동/정리

---

## 규칙 우선순위

1. `@.cursor/rules/root.mdc` — 자기 검증, 도메인 용어, DO/DON'T
2. `@.cursor/rules/architecture.mdc` — 레이어·포트
3. `@.cursor/rules/mcp.mdc` — MCP 활용
4. `@.cursor/rules/cursor-usage.mdc` — 계획 선행, 메모, 다중 채팅
5. `@.cursor/rules/persona-dialogue.mdc` — Persona Dialogue, 역할 핸드오프
6. 그 외 glob 규칙 — 파일/디렉터리별 적용

---

## MCP 서버 (선택·적절 사용)

**CLI·로컬 파일·공식 문서로 충분하면 MCP를 켜지 않아도 된다.** 진짜로 반복·정확도 이득이 큰 것만 연결한다. 세부 호출 규칙은 `@.cursor/rules/mcp.mdc`가 우선한다.

| 작업 성격 | MCP를 고려할 때 | 대안(없을 때) |
|-----------|-----------------|---------------|
| 라이브러리·API 최신 문서 | Context7, Google Developer Knowledge | 공식 문서 URL을 직접 열고 요약을 `documents/`에 남김 |
| Git 이력·PR·이슈 | GitHub MCP 또는 `gh` CLI | `git log` / 웹 UI에서 링크·요약 붙여넣기 |
| 웹 페이지 상호작용·E2E 검증 | Playwright MCP, IDE 브라우저 MCP | 수동 확인, 스크린샷 |
| 큰 설계·분해 | Sequential Thinking(선택) | `documents/` 플랜 MD + Persona Dialogue |
| DB·배포·에러 트래킹 | Supabase, Vercel, Sentry 등 **이미 쓰는 서비스**가 있을 때만 | 대시보드·CLI로 로그 복사 |

설정 위치: 워크스페이스는 `@.cursor/mcp.json`, 사용자 전역은 OS 사용자 폴더의 Cursor `mcp.json`을 쓴다. **API 키·토큰은 JSON에 박지 말고** `${env:VAR_NAME}` 등 환경 변수로만 넘긴다.

에이전트는 `call_mcp_tool` / `fetch_mcp_resource`를 쓰기 전에 해당 서버의 도구 스키마를 확인하고, 도구가 없거나 실패하면 **실패 이유와 로컬 대안**을 남긴다.

---

## 하네스 엔지니어링

- 프롬프트가 아니라 구조로 실수를 줄인다: 테스트, 린트, 레이어 규칙, 계획 승인 게이트.
- 컨텍스트 지도는 `AGENTS.md`, `.cursor/rules/`, `documents/CURSOR_MEMO.md`다.
- 재현된 실수는 테스트와 `documents/CURSOR_MEMO.md`에 남겨 반복을 줄인다.
- 외부 기업 사례·수치·인용은 검증 가능한 출처 없이 사실처럼 단정하지 않는다.

---

## 빌드·명령

| 목적 | 명령 |
|------|------|
| 설치 (런타임) | `pip install -r requirements.txt` 또는 `pip install -e .` |
| 설치 (개발·검증) | `pip install -e ".[dev]"` (`pytest`, `ruff`, `mypy`, `black`, `psutil`) |
| 실행 | `python src/main.py` |
| 테스트 | `pytest` |
| 검증 (한 번에, 권장) | `python scripts/verify_phase_completion.py` (순서: `pytest` → `ruff check .` → `mypy src` → `black --check .`, fail-fast) |
| 검증 (단계별·로컬) | `ruff check .` → `mypy src` → `black .` (포맷 적용; 테스트는 위 스크립트 또는 `pytest`) |
| 검증 (CI) | `.github/workflows/ci.yml` — `black --check .` 로 포맷만 검사 (파일 변경 없음) |

### PR·머지 전 체크리스트

1. `pip install -e ".[dev]"` 기준으로 **`python scripts/verify_phase_completion.py`** 가 끝까지 통과하는지 확인한다.
2. 또는 동일 순서로 수동 실행: `pytest` → `ruff check .` → `mypy src` → `black --check .`
3. 완료 보고에는 실행한 명령(스크립트 여부 포함)과 실패 시 로그 요약을 남긴다.

---

## 파일 구조

```text
src/
  domain/       application/   infrastructure/   gui/   app/
tests/  unit/  integration/  golden/
```

---

## 완료 보고 원칙

- 변경 파일, 검증 명령, 미실행 사유를 짧게 보고한다.
- 검증 실패 시 실패한 명령, 이유, 다음 담당 캐릭터를 남긴다.
- `black .`이 파일을 바꿨으면 "검증 통과"와 별도로 "포맷 변경 발생"을 함께 보고한다.

검증을 못 돌렸다면 최소 아래 3가지를 남긴다.

- 실행 못 한 명령
- 이유
- 남은 위험

---

## 보안·커밋

- API 키: `.env`, 코드 하드코딩 금지
- 커밋: `[모듈] 요약`, 검증 4단계 통과 후
