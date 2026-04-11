# Archived tests (레거시 하네스)

이 디렉터리는 **기본 `pytest` 수집에서 제외**된다 (`pyproject.toml`의 `testpaths`에 포함되지 않음).

| 경로 | 내용 |
|------|------|
| `integration/` | 골든 시나리오 — 삭제된 `infra.*` / `usecases.*` / `domain.models.*` 등에 의존. 현행 구조로 포팅 전까지 보관. |
| `performance/` | 벤치마크 스크립트·JSON — 동일 이유로 깨진 import. Phase 4에서 갱신 또는 폐기 결정. |

수동 실행이 필요하면(예: 포팅 작업 중) 해당 파일을 직접 지정해 실행한다.

```text
python -m pytest tests/_archive/integration/test_golden_scenarios.py -v
```

정본 경계 설명은 [tests/README.md](../README.md)를 본다.
