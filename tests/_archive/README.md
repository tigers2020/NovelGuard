# Archived tests (레거시 하네스)

이 디렉터리는 **기본 `pytest` 수집에서 제외**된다 (`pyproject.toml`의 `testpaths`에 포함되지 않으며, `norecursedirs`에 `_archive`가 있어 `pytest tests`로 넓게 호출해도 재귀하지 않음).

| 경로 | 내용 |
|------|------|
| `integration/` | 골든 시나리오 — 삭제된 `infra.*` / `usecases.*` / `domain.models.*` 등에 의존. **현재 구조로 포팅되지 않았으며, 수동 실행 시 collection/import 단계에서 실패할 수 있다.** |
| `performance/` | 벤치마크 스크립트·JSON — 동일하게 구 아키텍처 import에 묶여 있음. **2026-04-11 Remediation Phase 4 기준으로 CI·`scripts/verify_phase_completion.py`에서는 호출하지 않는다.** 향후 포팅 시 스크립트·JSON·[docs/archive/performance/](../../docs/archive/performance/) 서술을 함께 갱신한다. |

수동으로 열어볼 때는 실패가 정상이다. 포팅 작업 중이라면 파일을 직접 실행하기 전에 의존성을 현행 `src/`에 맞출 것.

```text
# 기대: 레거시 의존으로 실패할 수 있음
python -m pytest tests/_archive/integration/test_golden_scenarios.py -v
```

정본 경계 설명은 [tests/README.md](../README.md)를 본다.
