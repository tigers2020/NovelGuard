# persona

Persona Dialogue: 요청을 `[시몬]`이 나누고, 레이어 담당이 한두 문장 브리핑한 뒤 구현한다. 검증은 `[테스]`·`[렉스]`(pytest → ruff → mypy → black) 순.

| 역할 | 주 담당 경로 |
|------|----------------|
| 시몬 | 분배·게이트·`app/` |
| 도미닉 | `src/domain/` |
| 유리 | `src/application/` |
| 아다 | `src/infrastructure/` |
| 지나 | `src/gui/` (UI) |
| 테스 | `tests/` |
| 렉스 | 검증 파이프라인 |

전체 표와 3단계 규칙은 [AGENTS.md](../AGENTS.md)를 본다. UI 화면 세부 카드는 [gina-gui.md](gina-gui.md).
