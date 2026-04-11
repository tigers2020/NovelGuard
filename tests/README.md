# 테스트 레이아웃과 기본 스위트 (Phase 0 기준선)

## 기본 `pytest`에 포함되는 경로

`pyproject.toml`의 `testpaths`가 아래만 수집한다. 이 묶음이 CI·로컬의 **현행 기준선**이다.

- `tests/app/settings/`
- `tests/application/`
- `tests/gui/`
- `tests/infrastructure/`
- `tests/integration/` — 골든 러너는 `_archive`로 이동됨; 남은 파일만 수집
- `tests/unit/` — 도메인·애플리케이션 단위 테스트(현행 `src` 구조 정렬)

## 기본 수집에서 제외되는 레거시 (체크리스트)

2026-04-11 감사(P0-1) 기준. 포팅 우선순위는 이후 페이즈에서 결정한다.

| 구분 | 경로 | 비고 |
|------|------|------|
| 앱 레거시 | `tests/app/test_bootstrap.py`, `tests/app/test_workflows.py` | `app.bootstrap` / `app.workflows` 등 미존재 모듈 |
| 공통 레거시 | `tests/common/test_exception_mapper.py` | `common.*` 패키지 미존재 |
| 도메인 레거시 | `tests/domain/` 전체 | 현 `src/domain` 패키지 트리와 불일치 |
| 인프라 레거시 | `tests/infra/` 전체 | `infra.*` 미존재 |
| 골든·러너 | `tests/_archive/integration/` | `test_golden_scenarios.py`, `run_golden_tests.py` |
| 퍼포먼스 | `tests/_archive/performance/` | `benchmark_*.py`, `benchmark_baseline.json` |

`tests/_archive/`는 `norecursedirs`에 `_archive` basename을 두어, `pytest tests`처럼 넓게 호출해도 재귀하지 않도록 했다.

## 스냅샷·픽스처

- `tests/snapshots/` — 과거 스캔 결과 JSON 등을 두기 위한 자리였으나, **현재 저장소에는 파일이 없거나 비어 있을 수 있다.** [`tests/integration/test_snapshot_normalizer.py`](integration/test_snapshot_normalizer.py)는 디스크의 JSON을 읽지 않고, `snapshot_normalizer` 헬퍼의 순서·경로·타임스탬프 정규화만 검증한다.
- `tests/fixtures/` — 고정 데이터셋 디렉터리. **기본 `pytest` 스위트에서 `tests.fixtures` / `FIXTURES_DIR`를 import하는 테스트는 없다** (수동·향후 통합·아카이브 하네스용으로 보관). 상세는 [fixtures/README.md](fixtures/README.md).

## 기준선 개수 참고

2026-04-11 감사에서는 특정 8개 파일만 모아 **78 passed**를 기록했다. Phase 0 이후 기본 `testpaths`에는 동일 파일 외에 `tests/application`의 나머지 스테이지·파이프라인 테스트와 `tests/unit/` 전체가 포함되므로, 로컬에서 `python -m pytest`는 **약 144 passed** 규모가 된다(환경에 따라 소폭 차이 가능).

## 관련 문서

- 해결 계획 Phase 0: `documents/2026-04-11_repo_audit_remediation_plan.md`
- 감사 리포트 P0-1: `documents/2026-04-11_repo_audit_report.md`
