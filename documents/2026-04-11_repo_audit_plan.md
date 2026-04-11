# 플랜: 2026-04-11 저장소 전수 감사 리포트 작성

> 상태: 완료

## 배경

사용자 요청은 "최신 표준 코드 포맷 점검과 프로젝트 전반의 정밀 검토"를 코드 수정 없이 수행하고, 전수 감사 결과를 한국어 MD 리포트로 남기는 것이다. 이번 작업의 목표는 실행 가능한 기준선, 레이어 규칙 대비 이탈, 문서/테스트/자산 드리프트를 한 문서 체계로 닫는 데 있다.

## 변경 범위

| 레이어 | 파일/모듈 | 변경 내용 |
|--------|-----------|-----------|
| domain | `src/domain/`, `tests/domain/` | 타입 안정성, 레거시 테스트 잔존, 규칙/값 객체 상태 감사 |
| application | `src/application/`, `tests/application/` | port 계약, use case 흐름, DTO 일관성 감사 |
| infrastructure | `src/infrastructure/`, `tests/infrastructure/`, `tests/integration/` | 구현체 안정성, DB/FS adapter 상태, 현행 통합 테스트 감사 |
| gui | `src/gui/`, `tests/gui/` | Qt 결합도, view-model 상태, dead/stub 영역 감사 |
| tests | `tests/` 전체 | legacy/current split, fixture/snapshot 유효성, collection 경로 감사 |
| docs | `README.md`, `docs/`, `persona/`, `protocols/`, 루트 문서 | 실행 문서, 운영 문서, 리팩토링 히스토리의 현실 일치 여부 감사 |
| deliverables | `documents/2026-04-11_repo_audit_{research,plan,report}.md` | 감사 결과 문서 작성 |

## 접근 방식

1. 기준선 명령을 비파괴 방식으로 재실행해 현재 상태를 숫자로 고정한다.
2. `.cursor/rules/architecture.mdc`를 기준으로 `src/`를 레이어별로 대조한다.
3. 루트/문서/설정/스크립트와 `tests/`를 별도로 훑어 stale entrypoint, 중복 문서, 레거시 import, 죽은 자산을 식별한다.
4. 모든 tracked 파일을 `finding recorded`, `checked/no issue`, `grouped asset bucket` 중 하나로 분류해 전수 커버리지를 닫는다.

주요 트레이드오프:

- 코드 수정 대신 문서화에 집중해 현재 상태를 정확히 보존한다.
- fixture/snapshot은 개별 설명보다 묶음 설명을 택하되, 부록에는 파일 단위로 전부 남긴다.
- 프로젝트 템플릿의 `black .` 실행 항목은 이번 감사 성격상 `black --check .`로 대체한다.

## 영향 분석

- 기존 테스트 영향: 코드 변경이 없으므로 런타임 동작은 변하지 않는다. 대신 `pytest` 전체 기준선이 collection 단계에서 `21`건 실패한다는 사실을 문서화한다.
- DTO/port 계약 변경: 없음. 다만 `IJobRunner`와 GUI 결합 불일치를 주요 개선 항목으로 보고한다.
- DB migration 필요 여부: 없음.
- UI 변경 여부: 없음. `small_file_tab`, `undo_tab`, `_stubs` 등 미완성 UI 상태를 감사 결과로 기록한다.

## 검증 계획

- [x] `git status --short`
- [x] `git -c core.quotepath=false ls-files`
- [x] `git -c core.quotepath=false ls-files --others --exclude-standard`
- [x] `python -m pytest`
- [x] `python -m ruff check .`
- [x] `python -m mypy src`
- [x] `python -m black --check .`
- [x] 현행 구조 대상 subset 재검증 (`78 passed`)

## 감사 루브릭

- 심각도:
  - `P0`: 전체 검증 파이프라인 또는 핵심 운영 문서가 현재 구조를 허위로 설명하는 수준
  - `P1`: 아키텍처 규칙 위반, 정적 품질 악화, 표준 정의 충돌
  - `P2`: 죽은 코드, 미연결 스텁, 디버그 출력, stale benchmark/harness
  - `P3`: 유지보수 혼선은 크지만 즉시 장애로 이어지지 않는 문서/설정 찌꺼기
- 카테고리:
  - `format/lint`
  - `typing`
  - `test integrity`
  - `architecture`
  - `docs/config drift`
  - `duplicate/dead code`
  - `fixtures/assets hygiene`

## 승인

- 승인자: 사용자
- 승인일: 2026-04-11
