# 플랜: 2026-04-11 저장소 감사 후속 해결 계획

> 상태: Phase 0–5 이행 완료 (2026-04-11)

## 배경

2026-04-11 전수 감사 결과, NovelGuard는 "현행 구조는 일부 자리 잡았지만 레거시 문서·테스트·운영 기준선이 정리되지 않은 전환 중 상태"로 확인됐다. 이번 계획서는 감사 리포트의 P0-P3 Findings를 실제 정비 작업으로 전환하기 위한 해결 방법, 진행 방식, 페이즈별 개발 순서를 정의한다.

## 변경 범위

| 레이어 | 파일/모듈 | 변경 내용 |
|--------|-----------|-----------|
| domain | `src/domain/`, `tests/domain/` | 타입 안정성 복구, 레거시 테스트 포팅 또는 격리 |
| application | `src/application/`, `tests/application/` | port 계약 재정의, use case 기준선 정비 |
| infrastructure | `src/infrastructure/`, `tests/infrastructure/`, `tests/integration/`, `tests/performance/` | adapter 정합성, benchmark/golden harness 재정비 |
| gui | `src/gui/`, `tests/gui/` | `QtJobManager` 결합 해소, placeholder/stub 정리, lint/type 부채 상환 |
| tests | `tests/` 전체 | 기본 수집 경로 재설계, 현행 기준선/레거시 기준선 분리 |
| docs | `README.md`, `docs/`, `persona/`, `protocols/`, 루트 문서 | 현행 구조 정본화, archive 분리, 운영 문서 중복 제거 |

## 접근 방식

핵심 전략은 "기준선 복구 → 문서 정본화 → 계약/구조 정리 → 품질 부채 상환 → 죽은 자산 정리" 순서다. 먼저 깨진 테스트와 허위 문서를 방치한 상태에서 타입/포맷만 손보면 다시 드리프트가 생기므로, P0 단계에서 검증선과 구조 문서를 먼저 바로잡는다.

주요 트레이드오프:

- 한 번에 전부 고치지 않고 페이즈별로 기준선을 다시 세운다.
- 대규모 포맷 변경은 기능/구조 변경과 분리한다.
- 레거시 자산은 무조건 보존하지 않고, 유지 가치가 있으면 포팅하고 없으면 archive 또는 제거한다.

## 영향 분석

- 기존 테스트 영향: 기본 `pytest` 수집 경로가 바뀔 수 있다. 레거시 테스트는 별도 marker/디렉터리로 분리될 가능성이 높다.
- DTO/port 계약 변경: `IJobRunner`와 GUI 사이 계약은 변경 가능성이 높다. 이 단계는 application/gui 경계에 직접 영향을 준다.
- DB migration 필요 여부: 현재 계획상 없음. 다만 `sqlite_index_repository.py` 정리 과정에서 저장 포맷 영향 여부는 별도 점검이 필요하다.
- UI 변경 여부: placeholder 탭, `_stubs`, signal 연결 방식 정리 과정에서 일부 화면/동작 방식이 바뀔 수 있다.

## 해결 방법

### 1. 기준선 복구

- 기본 `pytest`가 현행 구조만 검증하도록 수집 대상을 재정의한다.
- 레거시 테스트는 `legacy` 성격으로 격리하거나, 유지 가치가 있는 것만 현행 구조로 포팅한다.
- `black --check`, `ruff`, `mypy`, `pytest`를 CI/로컬 공통 기준선으로 다시 선언한다.

### 2. 문서 정본화

- 실행 진입점, 레이어 구조, 개발 표준은 한 문서 집합만 정본으로 둔다.
- `docs/refactoring*`, `docs/refactoring_plan_v1.4/*`, 완료 보고서류는 "현재 설계 문서"가 아니라 "역사 기록"으로 분리한다.
- `README.md`, `pyproject.toml`, `requirements.txt` 사이 버전/의존성 정의를 하나로 맞춘다.

### 3. 계약과 경계 복구

- `IJobRunner`가 실제 필요한 이벤트와 명령을 담도록 재설계하거나, GUI 전용 adapter를 별도로 둔다.
- GUI는 `hasattr(...)`와 구현 전용 신호/메서드 대신 명시적 protocol만 바라보게 만든다.
- `app` 레이어가 조립 책임을 다시 가져가도록 wiring 성격의 호출을 걷어낸다.

### 4. 정적 품질 부채 상환

- domain 핵심 타입 오류와 GUI/infra hotspot을 우선순위 순으로 쪼개서 수리한다.
- 포맷 변경은 별도 phase 또는 별도 PR로 분리한다.
- 각 단계마다 subset test + static check를 다시 고정해 회귀 범위를 줄인다.

### 5. 죽은 코드와 자산 정리

- `_stubs`, `sample.html`, stale benchmark JSON, 깨진 harness는 유지/삭제/포팅 결정을 내린다.
- fixture/스냅샷은 "현재 어떤 테스트가 소비하는가"를 기준으로 재설명한다.
- `print(...)` 기반 디버그 출력은 `LogSink` 또는 공용 로깅 경로로 통합한다.

## 진행 방식

1. 각 페이즈는 문서 기준선, 코드 기준선, 검증 기준선을 함께 닫는다.
2. 페이즈 시작 전:
   - 대상 경로 확정
   - 위험 요소 확인
   - 필요한 경우 리서치/세부 플랜 문서 추가
3. 페이즈 진행 중:
   - 작은 단위로 변경
   - 통과 가능한 subset 검증 먼저 고정
   - 변경 이유와 남은 리스크 기록
4. 페이즈 종료 시:
   - 문서/코드/검증 결과가 서로 모순 없는지 확인
   - 다음 페이즈가 기대하는 기준선을 명시

## 페이즈별 개발 계획

## Phase 0. 기준선 복구

### 목표

- 기본 검증 체계를 다시 신뢰 가능한 상태로 만든다.
- 전체 `pytest`가 레거시 import 때문에 즉시 깨지는 상태를 끝낸다.

### 대상

- `tests/app/`
- `tests/common/`
- `tests/domain/`
- `tests/infra/`
- `tests/integration/test_golden_scenarios.py`
- `tests/integration/run_golden_tests.py`
- `tests/performance/`
- `tests/fixtures/README.md`
- `pyproject.toml`

### 작업 항목

1. 현재 기본 수집에서 제외할 레거시 테스트군을 식별하고 marker 또는 디렉터리 정책을 정한다.
2. `pytest` 기본 경로를 현행 구조 기준으로 재정의한다.
3. `78 passed` subset을 새 기본 기준선의 출발점으로 승격한다.
4. 레거시 golden/performance harness는 즉시 archive 또는 임시 비활성화한다.

### 검증

- `python -m pytest`
- 선택된 legacy/archived 테스트는 기본 수집에서 제외되는지 확인
- `python -m pytest tests/app/settings/test_constants.py tests/application/use_cases/duplicate_detection/test_pipeline_basic.py tests/gui/workers/test_duplicate_detection_worker.py tests/infrastructure/db/test_sqlite_index_repository.py tests/integration/test_scan_with_index_repository.py -q`

### 완료 기준

- 기본 `pytest`가 collection 오류 없이 실행된다.
- 현행 테스트 기준선과 레거시 테스트군의 경계가 문서화된다.

### 리스크

- 테스트를 단순 제외만 하면 커버리지 착시가 생길 수 있다.
- 유지 가치 있는 시나리오가 archive로 함께 사라지지 않도록 분류 기준이 필요하다.

## Phase 1. 문서와 운영 기준 정본화

### 목표

- 현재 구조를 설명하는 단일 정본 문서 집합을 만든다.
- README, pyproject, requirements, entry_points 문서의 모순을 제거한다.

### 대상

- `README.md`
- `docs/entry_points.md`
- `docs/refactoring*`
- `docs/refactoring_plan_v1.4/*`
- `docs/phase1_completion_report.md`
- `AGENTS.md`
- `persona/README.md`
- `persona/novelguard_developer.md`
- `protocols/README.md`
- `protocols/development_protocol.md`
- `.gitignore`
- `requirements.txt`
- `pyproject.toml`

### 작업 항목

1. 현행 진입점과 레이어 구조를 설명하는 canonical 문서를 만든다.
2. `docs/refactoring*`와 완료 보고서류는 archive 영역으로 이동하거나 historical 표기를 추가한다.
3. Python 버전, 설치 방법, 개발 의존성, 검증 명령의 단일 정본을 결정한다.
4. `.gitignore`의 tracked 경로 중복 규칙과 운영 문서 중복 규칙을 정리한다.

### 검증

- 문서 간 경로/버전/명령 모순 수동 점검
- `python -m pytest`
- `python -m black --check .`

### 완료 기준

- 엔트리포인트, 지원 Python 버전, 개발 검증 명령을 두고 서로 다른 문서가 충돌하지 않는다.
- historical 문서와 current-state 문서가 구분된다.

### 리스크

- 기존 리팩토링 기록을 너무 강하게 정리하면 의사결정 맥락을 잃을 수 있다.
- archive 정책 없이 이동만 하면 다시 링크가 깨질 수 있다.

## Phase 2. application-gui 계약 재설계

### 목표

- `IJobRunner`와 GUI 사이의 암묵적 결합을 제거한다.
- `app` 레이어가 조립 책임을 다시 명확히 가진다.

### 대상

- `src/application/ports/job_runner.py`
- `src/gui/view_models/scan_view_model.py`
- `src/gui/view_models/duplicate_view_model.py`
- `src/gui/services/qt_job_manager.py`
- `src/gui/views/main_window.py`
- 관련 GUI worker/view/model 테스트

### 작업 항목

1. 현재 GUI가 실제로 요구하는 명령/이벤트 목록을 계약으로 재정의한다.
2. `hasattr(...)` 기반 결합을 protocol 또는 adapter 기반 호출로 치환한다.
3. `set_file_data_store` 같은 wiring 성격 메서드의 책임 위치를 재조정한다.
4. GUI와 application 경계에 대한 테스트를 추가한다.

### 검증

- `python -m pytest tests/gui/workers/test_duplicate_detection_worker.py -q`
- 관련 GUI/view-model 테스트
- `python -m mypy src`

### 완료 기준

- GUI가 concrete `QtJobManager` shape를 직접 가정하지 않는다.
- `IJobRunner` 또는 새 adapter 계약이 문서와 코드에서 일치한다.

### 리스크

- Qt signal 모델과 Python protocol을 섞는 과정에서 테스트성이 잠시 나빠질 수 있다.
- 구조 변경이 넓게 퍼지므로 작은 단위 커밋이 필요하다.

## Phase 3. 정적 품질 hotspot 상환

### 목표

- lint/type 실패의 중심 파일부터 안정화한다.
- domain 핵심 규칙과 infra 핵심 구현의 신뢰도를 올린다.

### 우선순위 파일

- `src/domain/services/containment_detector.py`
- `src/domain/value_objects/filename_parse_result.py`
- `src/gui/views/components/duplicate_groups_table_view.py`
- `src/gui/models/duplicate_groups_table_model.py`
- `src/gui/models/file_data_store.py`
- `src/gui/views/components/file_list_table.py`
- `src/gui/views/tabs/settings_tab.py`
- `src/gui/views/tabs/scan_tab.py`
- `src/gui/views/main_window.py`
- `src/gui/services/qt_job_manager.py`
- `src/infrastructure/db/sqlite_index_repository.py`
- `src/infrastructure/fs/scanner.py`
- `src/infrastructure/logging/in_memory_log_sink.py`

### 작업 항목

1. domain 타입 오류와 optional 처리 오류를 먼저 수정한다.
2. GUI enum/Qt 타입 사용 패턴을 정리하고 반복 오류를 줄인다.
3. `print(...)` 디버그 출력과 공백/포맷 이슈를 정리한다.
4. 대규모 포맷 변경은 분리된 change set으로 수행한다.

### 검증

- `python -m mypy src`
- `python -m ruff check .`
- `python -m black --check .`
- 관련 subset tests

### 완료 기준

- 우선순위 파일군에서 mypy/ruff/black 기준선이 유의미하게 회복된다.
- domain/infra 핵심 경로에서 타입 오류가 구조적 문제가 아닌 잔여 작업 수준으로 내려간다.

### 리스크

- 포맷과 로직 수정이 섞이면 리뷰가 어려워진다.
- GUI 파일군은 수정 파급 범위가 넓어 회귀 테스트가 필요하다.

## Phase 4. 스텁·자산·벤치마크 정리

### 목표

- 유지 가치가 없는 코드와 자산을 정리하고, 남길 것은 현재 구조 기준으로 재연결한다.

### 대상

- `src/gui/view_models/_stubs/`
- `src/gui/views/tabs/small_file_tab.py`
- `src/gui/views/tabs/undo_tab.py`
- `sample.html`
- `scripts/verify_phase_completion.py`
- `tests/performance/*`
- `docs/performance/*`
- `tests/fixtures/*`
- `tests/snapshots/*`

### 작업 항목

1. `_stubs`와 placeholder 탭의 유지/삭제/실구현 여부를 결정한다.
2. `sample.html`, stale benchmark JSON, verify script의 필요성을 판정한다.
3. 성능/골든 테스트를 유지한다면 현재 아키텍처 기준으로 다시 정의한다.
4. fixture와 snapshot의 소비 경로를 문서화한다.

### 검증

- 유지 대상으로 남긴 자산이 실제 테스트/스크립트에서 소비되는지 확인
- `python -m pytest`
- 성능/골든 체계를 유지한다면 별도 실행 가이드 검증

### 완료 기준

- repo에 남은 자산은 "현재 쓰이는 것"과 "archive"가 명확히 구분된다.
- 설명 문서와 실제 소비 경로가 일치한다.

### 리스크

- fixture를 잘못 정리하면 회귀 재현 능력을 잃을 수 있다.
- benchmark를 유지할지 폐기할지 조직적 합의가 필요할 수 있다.

## Phase 5. 마감 및 지속 운영 기준선

> **완료 보고**: [documents/reports/Phase5_operational_baseline_closure.md](reports/Phase5_operational_baseline_closure.md)

### 목표

- 정리된 기준선을 팀 운영 규칙과 CI 흐름에 고정한다.

### 대상

- `AGENTS.md`
- `.cursor/rules/*`
- `README.md`
- `pyproject.toml`
- CI/검증 스크립트

### 작업 항목

1. 최종 개발 표준을 `AGENTS.md + .cursor/rules/* + pyproject.toml`에 반영한다.
2. 완료 보고 형식, 검증 명령, 문서 우선순위를 확정한다.
3. 이후 리팩토링/기능 개발이 새 기준선을 깨지 않도록 체크리스트를 남긴다.

### 검증

- `python -m pytest`
- `python -m ruff check .`
- `python -m mypy src`
- `python -m black --check .`

### 완료 기준

- 신규 작업자가 현재 표준을 한 번에 찾을 수 있다.
- 문서, 코드, 검증 기준선이 다시 서로 어긋나지 않는다.

### 리스크

- 문서만 고정하고 실제 CI가 따라오지 않으면 다시 드리프트가 생긴다.

## 권장 실행 순서

1. Phase 0: 테스트 기준선 복구
2. Phase 1: 문서/운영 기준 정본화
3. Phase 2: `IJobRunner`-GUI 계약 재설계
4. Phase 3: 정적 품질 hotspot 상환
5. Phase 4: 스텁·자산·벤치마크 정리
6. Phase 5: 지속 운영 기준선 고정

## 성공 기준

- 기본 `pytest`가 collection 오류 없이 돈다.
- 현재 구조를 설명하는 문서 정본이 하나로 합쳐진다.
- GUI가 concrete job manager 구현에 직접 결합하지 않는다.
- lint/type/format 기준선이 "대규모 실패" 상태에서 "남은 작업이 보이는 상태"로 내려간다.
- 죽은 코드와 stale 자산이 current/legacy/archive로 명확히 분리된다.

## 검증 계획

- [x] `pytest`
- [x] `ruff check .`
- [x] `mypy src`
- [x] `black --check .`

## 승인

- 승인자:
- 승인일:
