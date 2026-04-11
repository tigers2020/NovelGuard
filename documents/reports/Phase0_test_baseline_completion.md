# 개발 완료 보고서: Phase 0 테스트 기준선 복구

> **범위**: 2026-04-11 저장소 감사 후속 — [Phase 0 기준선 복구](../../../documents/2026-04-11_repo_audit_remediation_plan.md)  
> **완료일**: 2026-04-11  
> **상태**: 완료

---

## 1. 목표 달성 요약

| 목표 | 결과 |
|------|------|
| 기본 `pytest`가 레거시 import로 collection 단계에서 중단되지 않을 것 | 달성: `python -m pytest` collection error 없이 완주 |
| 현행 구조 테스트만 기본 수집 | `pyproject.toml`의 `testpaths` 화이트리스트 + `tests/conftest.py`의 `collect_ignore` |
| 골든·퍼포먼스 하네스 비활성(아카이브) | `tests/_archive/integration/`, `tests/_archive/performance/`로 이동, 기본 수집 제외 |
| 현행 vs 레거시 경계 문서화 | `tests/README.md`, `tests/fixtures/README.md`, `tests/_archive/README.md` |

---

## 2. 배경 (감사 P0-1)

- `testpaths = ["tests"]` 일 때 삭제된 패키지 트리(`app.bootstrap`, `common.*`, `infra.*`, `usecases.*`, `domain.models.*` 등)를 참조하는 테스트가 수집 단계에서 다수 오류를 냄.
- 감사 시점에는 특정 8개 파일 subset으로 **78 passed**가 확인되었으나, 전체 스위트는 사용 불가 상태였음.

---

## 3. 변경 사항

### 3.1 설정

- **`pyproject.toml`**
  - `testpaths`: `tests/app/settings`, `tests/application`, `tests/gui`, `tests/infrastructure`, `tests/integration`, `tests/unit`
  - `norecursedirs`: `_archive` 포함(넓은 경로 호출 시 아카이브 재귀 방지)

### 3.2 수집 안전망

- **`tests/conftest.py`**
  - `collect_ignore`: `_archive`, 레거시 `app`·`common`·`domain`·`infra` 트리
  - 목적: `pytest tests`처럼 `testpaths`를 우회하는 호출에서도 collection error 방지

### 3.3 아카이브 이동

| 이전 | 이후 |
|------|------|
| `tests/integration/test_golden_scenarios.py` | `tests/_archive/integration/test_golden_scenarios.py` |
| `tests/integration/run_golden_tests.py` | `tests/_archive/integration/run_golden_tests.py` |
| `tests/performance/*` | `tests/_archive/performance/*` |

- 골든 시나리오 파일 내 `PROJECT_ROOT` 계산을 새 경로 기준(`Path(__file__).resolve().parents[3]`)으로 수정.

### 3.4 스크립트

- **`scripts/verify_phase_completion.py`**: 골든·벤치 경로를 `tests/_archive/...`로 갱신.

### 3.5 문서

- **`tests/README.md`**: 기본 스위트 디렉터리, 제외 레거시 체크리스트, 78(감사 subset) vs 142(현재 기본 스위트) 설명.
- **`tests/fixtures/README.md`**: 현행 소비자·아카이브 하네스 상태 반영.
- **`tests/_archive/README.md`**: 아카이브 목적·수동 실행 안내.

---

## 4. 검증

실행 환경 예: Windows, Python 3.13.x, pytest 9.x.

| 명령 | 기대 |
|------|------|
| `python -m pytest` | collection 오류 없음, **142 passed** (애플리케이션·유닛 전체 포함 시; 환경에 따라 건수 소폭 차이 가능) |
| `python -m pytest tests` | 동일하게 레거시 제외 후 통과 |
| `python -m pytest tests --collect-only` | collection error 없음 |
| 해결 계획서 subset (5파일 스모크) | 통과 (감사 문서의 회귀용 한 줄) |

감사 문서의 **8파일·78 passed**는 “당시 고의 subset”이며, Phase 0 이후 기본 스위트는 `tests/unit` 및 나머지 `tests/application` 테스트를 포함해 건수가 늘어난 것이 의도된 결과임 — 상세는 `tests/README.md`의 “기준선 개수 참고” 절.

---

## 5. 범위 외 (후속 페이즈)

- `black` / `ruff` / `mypy` 전 저장소 정합 (Phase 3 등).
- `README.md`, `docs/*` 엔트리포인트 정본화 (Phase 1).
- `IJobRunner`·GUI 계약 정리 (Phase 2).
- 레거시 테스트 포팅, 벤치마크·골든 재구현 (Phase 4 및 별도 백로그).

---

## 6. 운영 참고

- Phase 1에서 `.gitignore`의 `tests/` 등 소스 트리 무시 블록이 정리됨. 다만 **`testpaths`에 넣은 디렉터리(특히 `tests/unit/`)는 Git에 추적**되어야 클론 후 `pytest` 건수가 설계와 일치한다. 미추적이면 “로컬에서만 144 passed”와 “저장소 기준”이 어긋난다. 미추적이었던 `tests/unit/`은 저장소에 포함하는 것으로 재현성을 맞춘다 — [tests/README.md](../../tests/README.md) “Git 추적” 절.

---

## 7. 참고 문서

- `documents/2026-04-11_repo_audit_remediation_plan.md` — Phase 0 정의
- `documents/2026-04-11_repo_audit_report.md` — P0-1, Validation Baseline
- `tests/README.md` — 정본(테스트 레이아웃)
