# 2026-04-11 저장소 전수 감사 리포트

> 상태: 완료
> 감사 대상 기준선: 산출물 문서 생성 전 tracked `387`개 파일
> 감사 언어: 한국어
> 코드 수정 여부: 없음

## Executive Summary

이번 감사는 "최신 표준 코드 포맷 점검 + 저장소 전수 구조 감사"를 목표로 비파괴 방식으로 진행했다. 최초 계획 초안의 가정과 달리 실제 기준선은 `378 tracked + 9 untracked`가 아니라 `387 tracked + 0 meaningful untracked`였고, 최종 리포트는 이 실제 기준선에 맞춰 다시 닫았다.

핵심 결론은 네 가지다. 첫째, 검증 체계가 레거시 테스트군과 현행 테스트군으로 갈라져 있어 `pytest` 전체 실행이 collection 단계에서 즉시 중단된다. 둘째, `docs/entry_points.md`, `docs/refactoring*`, `docs/refactoring_plan_v1.4/*`, `docs/phase1_completion_report.md` 등 대규모 문서 묶음이 더 이상 존재하지 않는 `bootstrap/workflows/FileRepository/ScanFilesUseCase` 구조를 현재 사실처럼 설명한다. 셋째, `.cursor/rules/architecture.mdc`가 요구하는 port 중심 구조와 달리 GUI가 `QtJobManager`의 구체 신호/메서드에 직접 결합돼 있다. 넷째, lint/type 기준선과 dead/stale artifact가 누적되어 유지보수 비용을 크게 끌어올리고 있다.

다만 코드베이스 전체가 완전히 붕괴한 상태는 아니다. 현행 구조를 따르는 테스트 묶음 8개 파일을 별도로 재실행했을 때 `78 passed in 1.53s`가 나왔고, 실제 런타임 진입점도 `src/main.py -> src/app/main.py`로 일관되게 동작한다. 즉, 현재 저장소는 "새 구조가 일부 자리잡았지만 레거시 문서와 검증선이 정리되지 않은 전환 중 상태"로 보는 것이 정확하다.

## Scope And Method

### 범위 확정

- 포함:
  - 루트 설정/배치/운영 문서
  - `docs/`, `documents/`, `persona/`, `protocols/`, `scripts/`
  - `src/` 전 레이어
  - `tests/` 전 영역
- 제외:
  - `.venv/`
  - `__pycache__/`
  - `.pytest_cache/`
  - `.mypy_cache/`
  - `.ruff_cache/`
  - `.benchmarks/`
  - `logs/`
  - `SAVE/`

### 실제 기준선

| 항목 | 값 |
|---|---:|
| `git status --short` | 출력 없음 |
| tracked files | 387 |
| meaningful untracked files | 0 |
| `src/` | 127 |
| `tests/` | 190 |
| `docs/` | 45 |
| `documents/` | 2 |
| 기타 tracked | 23 |

### 검토 방법

1. 기준선 명령을 재실행해 현재 상태를 숫자로 고정했다.
2. `.cursor/rules/architecture.mdc`의 레이어/포트 규칙을 기준으로 `src/`를 레이어별로 읽었다.
3. 루트 문서, 설정 파일, 스크립트, 리팩토링 보고서 묶음을 함께 검토해 현재 코드 구조와의 모순을 찾았다.
4. `tests/`는 레거시 import, 현행 테스트 통과 여부, fixture/snapshot의 유지 목적을 분리해 봤다.
5. 기준선 tracked 387개 파일 모두를 `finding recorded`, `checked/no issue`, `grouped asset bucket` 중 하나로 분류해 부록에서 닫았다.

## Validation Baseline

| 명령 | 결과 | 해석 |
|---|---|---|
| `git status --short` | 출력 없음 | 감사 시작 시점 tracked worktree는 깨끗했다. |
| `git -c core.quotepath=false ls-files` | `387` | 실제 감사 대상 수는 387개다. |
| `git -c core.quotepath=false ls-files --others --exclude-standard` | `0` | 계획 초안의 `9` untracked 가정은 현재 상태와 맞지 않았다. |
| `python -m black --check .` | `72 files would be reformatted` | 포맷 기준선이 크게 이탈해 있다. |
| `python -m ruff check .` | `1690 errors` | 대규모 lint 부채가 남아 있다. |
| `python -m mypy src` | `163 errors in 26 files` | 타입 계약이 아직 안정되지 않았다. |
| `python -m pytest` | collection 단계 `21 errors` | 전체 테스트 기준선이 현행 구조를 반영하지 못한다. |
| 현행 subset 재검증 | `78 passed in 1.53s` | 현재 구조를 따르는 테스트군은 정상 동작한다. |

현행 subset으로 통과를 확인한 파일:

- `tests/app/settings/test_constants.py`
- `tests/application/use_cases/duplicate_detection/test_pipeline_basic.py`
- `tests/application/use_cases/duplicate_detection/stages/test_blocking_stage.py`
- `tests/gui/workers/test_duplicate_detection_worker.py`
- `tests/infrastructure/db/test_sqlite_index_repository.py`
- `tests/integration/test_scan_with_index_repository.py`
- `tests/integration/test_snapshot_normalizer.py`
- `tests/application/use_cases/test_organize_by_chosung.py`

실제 현재 진입점 근거:

- `src/main.py:8-10`은 `sys.path`를 잡고 `from app.main import main`만 수행한다.
- `src/app/main.py:18-50`은 `QApplication`, `SQLiteIndexRepository`, `FileSystemScanner`, `QtJobManager`, `MainWindow`를 직접 조립한다.
- 즉 현재 저장소에는 문서가 말하는 `src/app/bootstrap.py`가 아니라 `app.main` 직결 조립 구조가 존재한다.

## Severity-Ordered Findings

### P0-1. `[test integrity]` 전체 테스트 스위트가 삭제된 구조를 여전히 기준선으로 삼고 있다

증거:

- `python -m pytest`가 collection 단계에서 `21 errors`로 중단됐다.
- `tests/app/test_bootstrap.py:15-17`은 `app.bootstrap`, `infra.db.file_repository`, `usecases.scan_files`를 import한다.
- `tests/app/test_workflows.py:17-18,166`은 `app.workflows.*`, `usecases.scan_files`를 import한다.
- `tests/common/test_exception_mapper.py:5-15`는 `common.*` 패키지를 기대한다.
- `tests/integration/test_golden_scenarios.py:16-27,47-49`와 `tests/performance/benchmark_baseline.py:18-24`는 `infra.*`, `usecases.*`, `domain.models.*`, `domain.aggregates.*`에 의존한다.
- `tests/domain/*`, `tests/infra/*`, `tests/performance/*` 아래 레거시 패키지 트리가 그대로 남아 있다.

영향:

- `pytest` 전체가 깨져 있기 때문에 CI/로컬 기준선이 현재 구조를 검증하지 못한다.
- 실패가 "실제 회귀"인지 "삭제된 구조를 향한 레거시 테스트"인지 분리되지 않아 신규 변경의 위험도를 평가하기 어렵다.
- fixture/snapshot과 golden/performance 자산의 의미도 함께 흐려진다.

다음 조치:

1. 레거시 테스트군을 `legacy/` 또는 별도 marker로 격리해 기본 `pytest` 수집 경로에서 제거한다.
2. 유지 가치가 있는 시나리오만 현행 `src/application`, `src/infrastructure`, `src/gui` 구조에 맞춰 포팅한다.
3. `tests/performance/*`, `tests/integration/run_golden_tests.py`, `tests/fixtures/README.md`의 설명도 새 기준선에 맞게 재정의한다.

### P0-2. `[docs/config drift]` 핵심 운영 문서와 리팩토링 기록이 현재 존재하지 않는 구조를 사실처럼 설명한다

증거:

- `docs/entry_points.md:20,41,47,54,61-64,134`는 `Bootstrap`, `src/app/bootstrap.py`, `FileRepository`, `ScanFilesUseCase`를 현재 진입 흐름으로 설명한다.
- `docs/phase1_completion_report.md:8-22,104-107,165`는 `src/app/bootstrap.py`와 `src/app/workflows/*`가 이미 구현 완료됐다고 적는다.
- `docs/refactoring/current_status_verification.md:102,107,115,132,185`는 `app/workflows/` 존재를 현재 사실처럼 쓴다.
- `docs/refactoring/architecture_summary_one_page.md:25-27,115-119,128`도 동일한 전제를 반복한다.
- `docs/refactoring_plan_v1.4/02_architecture_and_principles.md:9-16,120,247-253`과 `04_phase1_p0_blast_radius.md:38-90`는 `bootstrap/workflows/FileRepository/ScanFilesUseCase`를 설계 기준으로 유지한다.
- 실제 코드는 `src/main.py:10`과 `src/app/main.py:18-50`의 직접 조립 구조다.

영향:

- 신규 기여자와 미래의 에이전트가 잘못된 엔트리포인트와 잘못된 계층 구조를 따라가게 된다.
- 레거시 테스트와 stale 문서가 서로를 뒷받침해 "허위 기준선"을 강화한다.
- 리팩토링 보고서 묶음이 역사 기록이 아니라 현재 상태 진술처럼 남아 있어 판단 비용이 커진다.

다음 조치:

1. `docs/entry_points.md`, `README.md`의 실행/구조 설명을 현재 코드 기준으로 즉시 갱신한다.
2. `docs/refactoring*`, `docs/refactoring_plan_v1.4/*`, `docs/phase1_completion_report.md`는 "historical archive"로 명시하거나 현행 상태와 분리한다.
3. 현재 구조를 설명하는 단일 소스 문서를 새로 만들고, 나머지 문서는 그 문서에 링크만 남긴다.

### P1-1. `[docs/config drift][format/lint]` 지원 버전, 의존성, 품질 기준의 정본이 갈라져 있다

증거:

- `README.md:46`은 `Python 3.10 이상`을 요구한다.
- `pyproject.toml:5`는 `requires-python = ">=3.12"`로 더 엄격하다.
- 실제 subset 재검증은 Python `3.13.9` 환경에서 수행됐다.
- `README.md:117,120`은 `PyInstaller`, `rich`를 핵심 패키지로 나열한다.
- `requirements.txt:4,7,10,13,19,20`에는 `PySide6`, `charset-normalizer`, `pydantic`, `xxhash`, `pytest`, `psutil`만 있다.
- `pyproject.toml:13-18,22,28,38,52`는 `pytest`, `ruff`, `mypy`, `black`을 별도 optional/developer 기준으로 관리한다.
- 같은 저장소에서 `black --check`, `ruff`, `mypy`, `pytest` 기준선이 모두 불합격이다.

영향:

- 신규 환경 세팅 시 어떤 파일을 진실로 따라야 하는지 분명하지 않다.
- README만 읽고 설치하면 개발/검증 도구가 빠질 수 있다.
- "최신 표준 포맷"의 기준점이 문서와 설정 사이에서 흔들린다.

다음 조치:

1. `pyproject.toml`을 지원 버전과 개발 툴의 단일 정본으로 선언한다.
2. `README.md`와 `requirements.txt`를 그 정본에 맞춰 재작성한다.
3. `requirements.txt`를 런타임 전용으로 둘지, 개발 의존성까지 포함한 단일 파일로 둘지 결정하고 하나만 남긴다.

### P1-2. `[architecture][typing]` `IJobRunner` 추상화가 실제 런타임 사용 패턴을 담지 못한다

기준 규칙:

- `.cursor/rules/architecture.mdc`는 `gui`가 use case 또는 application DTO에 의존하되 concrete 세부를 직접 알지 말아야 하고, `app`에서 조립해야 한다고 명시한다.

증거:

- `src/application/ports/job_runner.py:9-47`의 `IJobRunner`는 `start_scan`, `cancel`, `get_status`, `subscribe`만 정의한다.
- `src/gui/view_models/scan_view_model.py:59-60`은 `hasattr(job_manager, 'job_started')` 뒤에 Qt signal을 직접 연결한다.
- `src/gui/view_models/duplicate_view_model.py:60-61,291-292`는 `job_started`와 `start_duplicate_detection`을 concrete 구현에 기대한다.
- `src/gui/views/main_window.py:75-76`은 `set_file_data_store`라는 구현 전용 메서드를 직접 호출한다.
- `src/gui/services/qt_job_manager.py:34,82,152`는 실제로 Qt signal과 GUI 친화 메서드를 제공한다.

영향:

- 포트가 존재해도 GUI는 여전히 `QtJobManager`의 shape를 알아야 하므로 레이어 분리 효과가 약하다.
- `hasattr`와 암묵적 duck typing이 늘어나 mypy 오류와 리팩토링 리스크를 동시에 키운다.
- `app` 레이어가 맡아야 할 조립 책임 일부가 GUI로 새어 나간다.

다음 조치:

1. `IJobRunner`를 실제 필요한 이벤트/명령까지 확장하거나, GUI 전용 adapter를 따로 둔다.
2. GUI는 protocol/adapter 하나만 바라보게 하고 `hasattr(...)`를 제거한다.
3. `set_file_data_store` 같은 wiring 성격의 호출은 `app.main` 또는 명시적 composition layer로 이동한다.

### P1-3. `[typing][format/lint]` 정적 품질 부채가 GUI 중심 클러스터와 일부 domain/infra 핵심 파일에 집중돼 있다

증거:

- `python -m black --check .`: `72 files would be reformatted`
- `python -m ruff check .`: `1690 errors`
- `python -m mypy src`: `163 errors in 26 files`
- `src/domain/services/containment_detector.py:42,84-85,117-118,255-256,296-297`은 `file_id`를 `str`로 다루는 시그니처를 남겨 타입 계약을 흔든다.
- `src/domain/value_objects/filename_parse_result.py:129,138,151,156,162,168,173,175,199`는 optional 컬렉션/범위 접근이 그대로 남아 있다.
- mypy 출력에는 `src/gui/views/tabs/scan_tab.py`, `src/gui/views/tabs/move_organize_tab.py`, `src/gui/views/main_window.py`, `src/gui/views/components/duplicate_groups_table_view.py`, `src/gui/services/qt_job_manager.py`가 반복해서 등장한다.
- lint/format hotspot 클러스터는 `src/gui/models/duplicate_groups_filter_proxy_model.py`, `src/gui/models/duplicate_groups_table_model.py`, `src/gui/models/file_data_store.py`, `src/gui/views/components/dry_run_preview_dialog.py`, `src/gui/views/components/duplicate_group_files_table_view.py`, `src/gui/views/components/duplicate_groups_table_view.py`, `src/gui/views/components/file_list_table.py`, `src/gui/views/tabs/base_tab.py`, `src/gui/views/tabs/duplicate_tab.py`, `src/gui/views/tabs/logs_tab.py`, `src/gui/views/tabs/move_organize_tab.py`, `src/gui/views/tabs/scan_tab.py`, `src/gui/views/tabs/settings_tab.py`, `src/gui/views/tabs/small_file_tab.py`, `src/gui/views/tabs/undo_tab.py`, `src/gui/views/main_window.py`, `src/gui/view_models/duplicate_view_model.py`, `src/gui/view_models/scan_view_model.py`, `src/infrastructure/db/sqlite_index_repository.py`, `src/infrastructure/fs/scanner.py`, `src/infrastructure/logging/in_memory_log_sink.py`, `src/domain/services/keeper_score_service.py`, `src/domain/services/near_duplicate_detector.py`까지 넓게 퍼져 있다.

영향:

- 타입/포맷 기준선이 무너진 상태에서는 작은 리팩토링도 회귀 탐지 비용이 커진다.
- GUI 레이어에 품질 부채가 몰려 있어 아키텍처 정리와 정적 품질 개선이 서로를 막는 구조가 된다.
- domain/infra 쪽 핵심 파일의 타입 불일치는 검출 결과의 신뢰도 자체를 떨어뜨린다.

다음 조치:

1. `containment_detector.py`, `filename_parse_result.py`, `duplicate_groups_table_view.py`, `qt_job_manager.py`, `sqlite_index_repository.py`를 1차 수복 대상으로 고정한다.
2. GUI enum/Qt type 관련 mypy 규칙을 팀 표준으로 정리하고 반복 패턴을 helper로 흡수한다.
3. 대규모 포맷 변경은 별도 PR로 분리해 기능 변경과 섞이지 않게 한다.

### P2-1. `[duplicate/dead code][fixtures/assets hygiene]` 미연결 스텁, placeholder 탭, stale harness와 오래된 결과물이 함께 남아 있다

증거:

- `src/gui/view_models/_stubs/`의 `IntegrityViewModel`, `LogsViewModel`, `SettingsViewModel`, `SmallFileViewModel`, `UndoViewModel`는 repo-wide `git grep` 기준 자기 정의 외 사용처가 없다.
- `EncodingViewModel`도 실제 런타임 연결이 아니라 `docs/refactoring/reports/P2-1_stubs_viewmodels.md`에서만 추가로 언급된다.
- `src/gui/views/tabs/small_file_tab.py:140`, `src/gui/views/tabs/undo_tab.py:101`, `src/gui/view_models/scan_view_model.py:68`과 `_stubs/*` 다수에 `TODO`가 남아 있다.
- `sample.html`은 repo-wide `git grep`에서 inbound reference가 전혀 없다.
- `scripts/verify_phase_completion.py` 역시 다른 tracked 파일에서 참조되지 않으며, 내부에서는 `tests/performance/benchmark_baseline.py`, `tests/performance/benchmark_baseline.json`만 바라본다 (`scripts/verify_phase_completion.py:55,72`).
- `tests/performance/benchmark_baseline.py:18-24`는 이미 삭제된 `infra.*`, `usecases.*` 구조를 import한다.
- `tests/performance/benchmark_baseline.json:5,68`은 `python_version = 3.14.0`, `cpu_time_seconds = 0.0` 같은 stale 결과를 담고 있다.
- `tests/fixtures/README.md:109,121,145`는 fixture를 "리팩토링 전 기준선"과 성능 벤치마크용으로 설명하지만, 그 기준선을 소비하는 harness는 현재 깨져 있다.
- `docs/performance/benchmark_baseline.md`, `docs/performance/qt_table_update_performance_analysis.md`도 이 오래된 성능 자산 맥락에 묶여 있다.

영향:

- 미완성 기능과 죽은 실험 자산이 구분되지 않아 유지보수 판단이 느려진다.
- 성능 수치와 fixture 의미가 현재 코드와 동기화되지 않아 잘못된 기준선을 만들 수 있다.
- 팀이 "나중에 연결할 코드"와 "사실상 폐기된 코드"를 구별하기 어렵다.

다음 조치:

1. `_stubs/`, placeholder 탭, `sample.html`, `verify_phase_completion.py`, stale benchmark 파일에 대해 `유지/연결/삭제` 결정을 한 번에 내린다.
2. 유지할 벤치마크라면 현재 아키텍처 기준으로 다시 측정하고 JSON/문서를 갱신한다.
3. fixture README는 "현재 어떤 테스트가 실제로 소비하는가"를 기준으로 다시 쓴다.

### P2-2. `[duplicate/dead code][architecture]` 디버그 출력과 콘솔 결합 로깅이 남아 있어 런타임 출력면이 일관되지 않다

증거:

- `src/gui/models/file_data_store.py:307,309`에 `[DEBUG]` `print(...)`가 남아 있다.
- `src/gui/views/components/file_list_table.py:201`도 signal 연결 상태를 직접 `print(...)`한다.
- `src/gui/workers/preview_worker.py:196`은 디렉터리 스캔 예외를 콘솔로 직접 출력한다.
- `src/infrastructure/logging/in_memory_log_sink.py:146-158,202`는 ANSI 색상 `print(...)`와 파일 쓰기 실패 `print(...)`를 직접 사용한다.

영향:

- GUI 앱, 테스트, 콘솔 실행이 서로 다른 출력 경로를 쓰게 된다.
- 로그 sink가 이미 존재하는데 별도 `print(...)`가 섞여 있어 관찰면이 일관되지 않다.
- Windows/CI/GUI 환경에서 ANSI 출력과 stdout 의존성이 불필요한 잡음을 만든다.

다음 조치:

1. debug `print(...)`를 전부 `LogSink` 또는 명시적 debug logger로 통합한다.
2. 개발용 콘솔 출력이 필요하면 플래그 기반 adapter 뒤로 숨긴다.
3. 로그 쓰기 실패 자체도 동일한 로깅 경로 또는 fallback sink에서 처리한다.

### P3-1. `[docs/config drift]` `.gitignore`와 프로세스 문서 계층이 미래 드리프트를 유발하기 쉬운 상태다

증거:

- `.gitignore:221-239`는 `logs/`, `SAVE/` 외에 이미 tracked 상태인 `tests/`, `protocols/`, `persona/`, `scripts/`, `.cursor/`, `.benchmark/`까지 ignore 규칙으로 적고 있다.
- `AGENTS.md:5,61,121`은 `.cursor/rules/root.mdc`를 최상위 지시서로 두고 규칙 우선순위와 완료 보고 원칙을 정의한다.
- 동시에 `persona/novelguard_developer.md:3,8,32,133`는 별도 운영 원칙과 검증 책임을 장문으로 재정의하고, `protocols/development_protocol.md`도 독립적인 운영 지침을 별도 보유한다.

영향:

- 새 파일을 추가할 때 tracked/ignored 해석이 직관적이지 않다.
- 운영 규칙이 여러 문서에 복제될수록 일부만 갱신되는 드리프트가 반복된다.
- "현재 유효한 규칙"을 찾는 탐색 비용이 커진다.

다음 조치:

1. `.gitignore`에서 이미 tracked인 디렉터리를 무분별하게 다시 가리는 규칙을 정리한다.
2. 운영 정책의 source of truth를 `AGENTS.md + .cursor/rules/*`로 고정하고, persona/protocol 문서는 역할 설명 또는 참고 부록으로 축소한다.
3. 문서 우선순위와 갱신 책임자를 명시해 동일 정책의 중복 복제를 줄인다.

## Cross-File Contradictions Matrix

| 주장 출처 | 현재 문서/규칙의 주장 | 실제 코드/기준선 | 모순 | 권장 정리 |
|---|---|---|---|---|
| `README.md:46` | Python `3.10+` 지원 | `pyproject.toml:5`는 `>=3.12`, 실제 subset 실행은 `3.13.9` | 지원 버전 정본이 셋으로 갈라짐 | `pyproject.toml`을 정본으로 고정하고 README 동기화 |
| `README.md:117,120` | `PyInstaller`, `rich`가 핵심 패키지 | `requirements.txt:4,7,10,13,19,20`에는 없음 | 설치 가이드와 실제 의존성 집합 불일치 | 런타임/개발 의존성 경계 재정의 |
| `docs/entry_points.md`, `docs/phase1_completion_report.md`, `docs/refactoring*` | `bootstrap/workflows/FileRepository/ScanFilesUseCase`가 현재 구조 | `src/main.py:10`, `src/app/main.py:18-50`은 direct composition | 엔트리포인트 설명 전체가 현재 상태와 다름 | 현행 구조 문서 1개로 재작성, 나머지는 archive |
| `.cursor/rules/architecture.mdc` | GUI는 application DTO/use case에 의존, app가 조립 담당 | `scan_view_model.py:59-60`, `duplicate_view_model.py:291-292`, `main_window.py:75-76`은 concrete `QtJobManager` shape에 결합 | 포트는 존재하지만 실제 결합은 concrete 중심 | GUI adapter/port 재설계 |
| `.cursor/rules/architecture.mdc` 테스트 배치 규칙 | domain 규칙은 `tests/unit/` 우선 | 실제 tracked 트리에는 `tests/unit/`가 없고, 레거시 `tests/domain/*`가 현행 구조와 불일치 | 테스트 조직과 규칙 문서가 어긋남 | 테스트 디렉터리 정책 재선언 및 정리 |
| `tests/fixtures/README.md:121,145` | fixture가 "리팩토링 전 기준선"이며 성능 벤치마크에 사용됨 | `tests/performance/benchmark_baseline.py`는 현재 import 자체가 깨지고, JSON도 stale | fixture 의미와 소비자 harness가 분리됨 | fixture 목적을 현재 테스트 기준으로 재작성 |

## Dead-Code And Stale-Artifact Review

| 대상 | 상태 판단 | 근거 | 권장 결정 |
|---|---|---|---|
| `src/gui/view_models/_stubs/*` | 사실상 미연결 스텁 | 대부분 자기 정의 외 참조 없음, 다수 TODO | 유지하려면 연결 계획 명시, 아니면 제거 |
| `src/gui/views/tabs/small_file_tab.py`, `src/gui/views/tabs/undo_tab.py` | placeholder UI | 실제 기능 대신 TODO 카드만 존재 | roadmap 항목으로 승격하거나 숨김/삭제 |
| `sample.html` | 죽은 자산 가능성 큼 | repo-wide 참조 0건 | 즉시 삭제 후보 검토 |
| `scripts/verify_phase_completion.py` | stale script | 현재 깨진 benchmark 파일만 참조, inbound reference 0건 | archive 또는 현행 기준선에 맞게 재작성 |
| `tests/performance/*` | stale benchmark harness | 레거시 import + stale JSON | 유지 가치 재판단 후 전면 갱신 또는 제거 |
| `docs/performance/*` | stale narrative | 오래된 benchmark 흐름과 결합 | 현행 benchmark 없으면 archive |
| `docs/refactoring*`, `docs/refactoring_plan_v1.4/*`, `docs/phase1_completion_report.md` | 역사 문서와 현재 상태 진술이 혼재 | 현재 코드와 다른 구조를 현행으로 기술 | historical 폴더로 분리 |

## Prioritized Remediation Backlog

1. `P0`: 기본 `pytest` 수집 경로를 현행 테스트군만 포함하도록 정리하고, 레거시 테스트는 격리하거나 포팅한다.
2. `P0`: 엔트리포인트/아키텍처 문서의 정본을 새로 만들고 `docs/refactoring*` 묶음은 archive 처리한다.
3. `P1`: `README.md`, `pyproject.toml`, `requirements.txt`의 Python 버전/의존성/검증 도구 정의를 하나로 맞춘다.
4. `P1`: `IJobRunner`와 `QtJobManager` 사이의 실제 계약을 재설계하고 GUI의 `hasattr(...)` 결합을 제거한다.
5. `P1`: `containment_detector.py`, `filename_parse_result.py`, GUI table/view/model cluster, `sqlite_index_repository.py`를 대상으로 lint/type debt를 집중 상환한다.
6. `P2`: `_stubs/`, placeholder 탭, `sample.html`, stale benchmark/golden harness의 유지 여부를 한 번에 결정한다.
7. `P2`: `print(...)` 기반 디버그/콘솔 로깅을 `LogSink` 중심으로 통일한다.
8. `P3`: `.gitignore`와 운영 문서 계층을 정리해 future drift surface를 줄인다.

## Full Coverage Appendix

기준:

- 이 부록은 감사 산출물 문서 생성 전 tracked `387`개 파일만 포함한다.
- 새로 만든 `documents/2026-04-11_repo_audit_research.md`, `documents/2026-04-11_repo_audit_plan.md`, `documents/2026-04-11_repo_audit_report.md`는 감사 결과물이지 감사 대상 기준선이 아니므로 제외했다.
- 모든 경로는 정확히 한 번만 분류했다.

### finding recorded (`121`)

```text
.gitignore
docs/entry_points.md
docs/performance/benchmark_baseline.md
docs/performance/qt_table_update_performance_analysis.md
docs/phase1_completion_report.md
docs/refactoring/architecture_summary_one_page.md
docs/refactoring/architecture_violations_fix_guide.md
docs/refactoring/current_status_verification.md
docs/refactoring/deprecated_removal_plan.md
docs/refactoring/deprecated_to_removed_criteria.md
docs/refactoring/file_record_migration.md
docs/refactoring/model_classification.md
docs/refactoring/phase1.2_completion_report.md
docs/refactoring/phase2.1_completion_report.md
docs/refactoring/phase2.2_completion_report.md
docs/refactoring/phase2_completion_report.md
docs/refactoring/phase4.1_completion_report.md
docs/refactoring/phase4.2_architecture_validation.md
docs/refactoring/phase4_completion_report.md
docs/refactoring/reports/P0-1_duplicate_detection_worker.md
docs/refactoring/reports/P0-2_qt_job_manager.md
docs/refactoring/reports/P0-3_file_list_table.md
docs/refactoring/reports/P0-4_file_data_store.md
docs/refactoring/reports/P0-5_sqlite_index_repository.md
docs/refactoring/reports/P0-6_circular_dependency.md
docs/refactoring/reports/P1-1_tabs_duplication.md
docs/refactoring/reports/P1-2_filename_parser.md
docs/refactoring/reports/P1-3_containment_detector.md
docs/refactoring/reports/P2-1_stubs_viewmodels.md
docs/refactoring/reports/P2-2_dark_theme.md
docs/refactoring/reports/README.md
docs/refactoring/reports/SUMMARY.md
docs/refactoring_plan_v1.4/01_overview.md
docs/refactoring_plan_v1.4/02_architecture_and_principles.md
docs/refactoring_plan_v1.4/03_phase0_foundation.md
docs/refactoring_plan_v1.4/04_phase1_p0_blast_radius.md
docs/refactoring_plan_v1.4/05_phase2_domain_refinement.md
docs/refactoring_plan_v1.4/06_phase3_infra_stabilization.md
docs/refactoring_plan_v1.4/07_phase4_cleanup.md
docs/refactoring_plan_v1.4/08_schedule_and_tracking.md
docs/refactoring_plan_v1.4/09_definition_of_done.md
docs/refactoring_plan_v1.4/10_decision_log.md
docs/refactoring_plan_v1.4/11_repeat_and_tips.md
docs/refactoring_plan_v1.4/12_code_reality_verification.md
docs/refactoring_plan_v1.4/13_changelog.md
docs/refactoring_plan_v1.4/README.md
persona/novelguard_developer.md
protocols/development_protocol.md
pyproject.toml
README.md
requirements.txt
sample.html
scripts/verify_phase_completion.py
src/application/ports/job_runner.py
src/domain/services/containment_detector.py
src/domain/services/keeper_score_service.py
src/domain/services/near_duplicate_detector.py
src/domain/value_objects/filename_parse_result.py
src/gui/models/duplicate_groups_filter_proxy_model.py
src/gui/models/duplicate_groups_table_model.py
src/gui/models/file_data_store.py
src/gui/services/qt_job_manager.py
src/gui/view_models/_stubs/__init__.py
src/gui/view_models/_stubs/encoding_view_model.py
src/gui/view_models/_stubs/integrity_view_model.py
src/gui/view_models/_stubs/logs_view_model.py
src/gui/view_models/_stubs/settings_view_model.py
src/gui/view_models/_stubs/small_file_view_model.py
src/gui/view_models/_stubs/undo_view_model.py
src/gui/view_models/duplicate_view_model.py
src/gui/view_models/scan_view_model.py
src/gui/views/components/dry_run_preview_dialog.py
src/gui/views/components/duplicate_group_files_table_view.py
src/gui/views/components/duplicate_groups_table_view.py
src/gui/views/components/file_list_table.py
src/gui/views/main_window.py
src/gui/views/tabs/base_tab.py
src/gui/views/tabs/duplicate_tab.py
src/gui/views/tabs/logs_tab.py
src/gui/views/tabs/move_organize_tab.py
src/gui/views/tabs/scan_tab.py
src/gui/views/tabs/settings_tab.py
src/gui/views/tabs/small_file_tab.py
src/gui/views/tabs/undo_tab.py
src/infrastructure/db/sqlite_index_repository.py
src/infrastructure/fs/scanner.py
src/infrastructure/logging/in_memory_log_sink.py
tests/app/test_bootstrap.py
tests/app/test_workflows.py
tests/common/test_exception_mapper.py
tests/domain/adapters/test_file_adapter.py
tests/domain/aggregates/__init__.py
tests/domain/aggregates/test_action_plan.py
tests/domain/aggregates/test_duplicate_group.py
tests/domain/entities/__init__.py
tests/domain/entities/test_file.py
tests/domain/entities/test_integrity_issue.py
tests/domain/policies/__init__.py
tests/domain/policies/test_version_selection.py
tests/domain/ports/__init__.py
tests/domain/ports/test_protocol_compliance.py
tests/domain/services/__init__.py
tests/domain/services/test_evidence_builder.py
tests/domain/services/test_file_compare.py
tests/domain/services/test_integrity_checker.py
tests/domain/services/test_version_selector.py
tests/domain/value_objects/__init__.py
tests/domain/value_objects/test_candidate_edge.py
tests/domain/value_objects/test_evidence.py
tests/domain/value_objects/test_file_hash.py
tests/domain/value_objects/test_file_metadata.py
tests/domain/value_objects/test_file_path.py
tests/infra/__init__.py
tests/infra/logging/__init__.py
tests/infra/logging/test_std_logger.py
tests/integration/run_golden_tests.py
tests/integration/test_golden_scenarios.py
tests/performance/__init__.py
tests/performance/benchmark_baseline.json
tests/performance/benchmark_baseline.py
tests/performance/benchmark_gate.py
```

### checked/no issue (`140`)

```text
.serena/.gitignore
.serena/project.yml
AGENTS.md
clean_cache.bat
clean_cache.ps1
documents/CURSOR_MEMO.md
documents/PLAN_TEMPLATE.md
LICENSE
NovelGuard_실행_리포트.md
persona/README.md
protocols/README.md
pyrightconfig.json
run.bat
run.ps1
scripts/clean_cache.py
src/__init__.py
src/app/__init__.py
src/app/factories.py
src/app/main.py
src/app/settings/__init__.py
src/app/settings/constants.py
src/application/__init__.py
src/application/dto/__init__.py
src/application/dto/duplicate_detection_request.py
src/application/dto/duplicate_group_result.py
src/application/dto/ext_stat.py
src/application/dto/file_data.py
src/application/dto/folder_scan_outcome.py
src/application/dto/job_types.py
src/application/dto/log_entry.py
src/application/dto/run_summary.py
src/application/dto/scan_request.py
src/application/dto/scan_result.py
src/application/ports/__init__.py
src/application/ports/file_data_store.py
src/application/ports/file_scanner.py
src/application/ports/hash_service.py
src/application/ports/index_repository.py
src/application/ports/log_sink.py
src/application/use_cases/__init__.py
src/application/use_cases/duplicate_detection/__init__.py
src/application/use_cases/duplicate_detection/duplicate_detection_pipeline.py
src/application/use_cases/duplicate_detection/stages/__init__.py
src/application/use_cases/duplicate_detection/stages/base_stage.py
src/application/use_cases/duplicate_detection/stages/blocking_stage.py
src/application/use_cases/duplicate_detection/stages/exact_duplicate_stage.py
src/application/use_cases/duplicate_detection/stages/file_mapping_stage.py
src/application/use_cases/duplicate_detection/stages/filename_parsing_stage.py
src/application/use_cases/duplicate_detection/stages/group_creation_stage.py
src/application/use_cases/duplicate_detection/stages/near_duplicate_stage.py
src/application/use_cases/duplicate_detection/stages/relation_detection_stage.py
src/application/use_cases/move_duplicate_files.py
src/application/use_cases/organize_by_chosung.py
src/application/use_cases/scan_folder.py
src/application/utils/__init__.py
src/application/utils/debug_logger.py
src/application/utils/duplicate_group_normalizer.py
src/application/utils/duplicate_json.py
src/application/utils/extensions.py
src/application/utils/scan_json.py
src/domain/__init__.py
src/domain/entities/__init__.py
src/domain/entities/file_entry.py
src/domain/services/__init__.py
src/domain/services/blocking_service.py
src/domain/services/exact_duplicate_detector.py
src/domain/services/filename_parser.py
src/domain/value_objects/__init__.py
src/domain/value_objects/blocking_group.py
src/domain/value_objects/detection_config.py
src/domain/value_objects/duplicate_relation.py
src/domain/value_objects/preview_stats.py
src/domain/value_objects/range_segment.py
src/gui/__init__.py
src/gui/models/__init__.py
src/gui/models/app_state.py
src/gui/models/duplicate_group_files_table_model.py
src/gui/services/__init__.py
src/gui/styles/__init__.py
src/gui/styles/colors.py
src/gui/styles/dark_theme.py
src/gui/view_models/__init__.py
src/gui/view_models/base_view_model.py
src/gui/view_models/stats_view_model.py
src/gui/views/__init__.py
src/gui/views/components/__init__.py
src/gui/views/components/evidence_panel.py
src/gui/views/components/file_list_constants.py
src/gui/views/components/header.py
src/gui/views/components/sidebar.py
src/gui/views/tabs/__init__.py
src/gui/views/tabs/encoding_tab.py
src/gui/views/tabs/integrity_tab.py
src/gui/views/tabs/stats_tab.py
src/gui/workers/__init__.py
src/gui/workers/duplicate_detection_worker.py
src/gui/workers/file_move_worker.py
src/gui/workers/preview_worker.py
src/gui/workers/scan_worker.py
src/infrastructure/__init__.py
src/infrastructure/db/__init__.py
src/infrastructure/db/paths.py
src/infrastructure/db/schema.py
src/infrastructure/fs/__init__.py
src/infrastructure/hashing/__init__.py
src/infrastructure/hashing/hash_service_adapter.py
src/infrastructure/logging/__init__.py
src/main.py
tests/__init__.py
tests/app/__init__.py
tests/app/settings/__init__.py
tests/app/settings/test_constants.py
tests/application/__init__.py
tests/application/use_cases/__init__.py
tests/application/use_cases/duplicate_detection/__init__.py
tests/application/use_cases/duplicate_detection/stages/__init__.py
tests/application/use_cases/duplicate_detection/stages/test_blocking_stage.py
tests/application/use_cases/duplicate_detection/stages/test_file_mapping_stage.py
tests/application/use_cases/duplicate_detection/stages/test_filename_parsing_stage.py
tests/application/use_cases/duplicate_detection/stages/test_group_creation_stage.py
tests/application/use_cases/duplicate_detection/stages/test_relation_detection_stage.py
tests/application/use_cases/duplicate_detection/test_base_stage.py
tests/application/use_cases/duplicate_detection/test_pipeline_basic.py
tests/application/use_cases/duplicate_detection/test_pipeline_context.py
tests/application/use_cases/test_organize_by_chosung.py
tests/conftest.py
tests/domain/__init__.py
tests/domain/adapters/__init__.py
tests/domain/value_objects/test_preview_stats.py
tests/gui/__init__.py
tests/gui/workers/__init__.py
tests/gui/workers/test_duplicate_detection_worker.py
tests/infrastructure/db/__init__.py
tests/infrastructure/db/test_sqlite_index_repository.py
tests/integration/__init__.py
tests/integration/snapshot_normalizer.py
tests/integration/test_scan_with_index_repository.py
tests/integration/test_snapshot_normalizer.py
TODO_리스트.md
리팩토링_계획서.md
```

### grouped asset bucket (`126`)

```text
tests/fixtures/__init__.py
tests/fixtures/edge_cases/binary.bin
tests/fixtures/edge_cases/empty_file.txt
tests/fixtures/edge_cases/large_file.txt
tests/fixtures/edge_cases/novel_1-114.txt
tests/fixtures/edge_cases/novel_1-158.txt
tests/fixtures/edge_cases/novel_euckr.txt
tests/fixtures/edge_cases/novel_title_A.txt
tests/fixtures/edge_cases/novel_title_B.txt
tests/fixtures/edge_cases/novel_utf8.txt
tests/fixtures/edge_cases/special_chars.txt
tests/fixtures/edge_cases/tiny_file.txt
tests/fixtures/generate_fixtures.py
tests/fixtures/medium/group_1_file_1.txt
tests/fixtures/medium/group_1_file_2.txt
tests/fixtures/medium/group_1_file_3.txt
tests/fixtures/medium/group_1_file_4.txt
tests/fixtures/medium/group_1_file_5.txt
tests/fixtures/medium/group_10_file_1.txt
tests/fixtures/medium/group_10_file_2.txt
tests/fixtures/medium/group_10_file_3.txt
tests/fixtures/medium/group_10_file_4.txt
tests/fixtures/medium/group_10_file_5.txt
tests/fixtures/medium/group_2_file_1.txt
tests/fixtures/medium/group_2_file_2.txt
tests/fixtures/medium/group_2_file_3.txt
tests/fixtures/medium/group_2_file_4.txt
tests/fixtures/medium/group_2_file_5.txt
tests/fixtures/medium/group_3_file_1.txt
tests/fixtures/medium/group_3_file_2.txt
tests/fixtures/medium/group_3_file_3.txt
tests/fixtures/medium/group_3_file_4.txt
tests/fixtures/medium/group_3_file_5.txt
tests/fixtures/medium/group_4_file_1.txt
tests/fixtures/medium/group_4_file_2.txt
tests/fixtures/medium/group_4_file_3.txt
tests/fixtures/medium/group_4_file_4.txt
tests/fixtures/medium/group_4_file_5.txt
tests/fixtures/medium/group_5_file_1.txt
tests/fixtures/medium/group_5_file_2.txt
tests/fixtures/medium/group_5_file_3.txt
tests/fixtures/medium/group_5_file_4.txt
tests/fixtures/medium/group_5_file_5.txt
tests/fixtures/medium/group_6_file_1.txt
tests/fixtures/medium/group_6_file_2.txt
tests/fixtures/medium/group_6_file_3.txt
tests/fixtures/medium/group_6_file_4.txt
tests/fixtures/medium/group_6_file_5.txt
tests/fixtures/medium/group_7_file_1.txt
tests/fixtures/medium/group_7_file_2.txt
tests/fixtures/medium/group_7_file_3.txt
tests/fixtures/medium/group_7_file_4.txt
tests/fixtures/medium/group_7_file_5.txt
tests/fixtures/medium/group_8_file_1.txt
tests/fixtures/medium/group_8_file_2.txt
tests/fixtures/medium/group_8_file_3.txt
tests/fixtures/medium/group_8_file_4.txt
tests/fixtures/medium/group_8_file_5.txt
tests/fixtures/medium/group_9_file_1.txt
tests/fixtures/medium/group_9_file_2.txt
tests/fixtures/medium/group_9_file_3.txt
tests/fixtures/medium/group_9_file_4.txt
tests/fixtures/medium/group_9_file_5.txt
tests/fixtures/medium/unique_1.txt
tests/fixtures/medium/unique_10.txt
tests/fixtures/medium/unique_11.txt
tests/fixtures/medium/unique_12.txt
tests/fixtures/medium/unique_13.txt
tests/fixtures/medium/unique_14.txt
tests/fixtures/medium/unique_15.txt
tests/fixtures/medium/unique_16.txt
tests/fixtures/medium/unique_17.txt
tests/fixtures/medium/unique_18.txt
tests/fixtures/medium/unique_19.txt
tests/fixtures/medium/unique_2.txt
tests/fixtures/medium/unique_20.txt
tests/fixtures/medium/unique_21.txt
tests/fixtures/medium/unique_22.txt
tests/fixtures/medium/unique_23.txt
tests/fixtures/medium/unique_24.txt
tests/fixtures/medium/unique_25.txt
tests/fixtures/medium/unique_26.txt
tests/fixtures/medium/unique_27.txt
tests/fixtures/medium/unique_28.txt
tests/fixtures/medium/unique_29.txt
tests/fixtures/medium/unique_3.txt
tests/fixtures/medium/unique_30.txt
tests/fixtures/medium/unique_31.txt
tests/fixtures/medium/unique_32.txt
tests/fixtures/medium/unique_33.txt
tests/fixtures/medium/unique_34.txt
tests/fixtures/medium/unique_35.txt
tests/fixtures/medium/unique_36.txt
tests/fixtures/medium/unique_37.txt
tests/fixtures/medium/unique_38.txt
tests/fixtures/medium/unique_39.txt
tests/fixtures/medium/unique_4.txt
tests/fixtures/medium/unique_40.txt
tests/fixtures/medium/unique_41.txt
tests/fixtures/medium/unique_42.txt
tests/fixtures/medium/unique_43.txt
tests/fixtures/medium/unique_44.txt
tests/fixtures/medium/unique_45.txt
tests/fixtures/medium/unique_46.txt
tests/fixtures/medium/unique_47.txt
tests/fixtures/medium/unique_48.txt
tests/fixtures/medium/unique_49.txt
tests/fixtures/medium/unique_5.txt
tests/fixtures/medium/unique_50.txt
tests/fixtures/medium/unique_6.txt
tests/fixtures/medium/unique_7.txt
tests/fixtures/medium/unique_8.txt
tests/fixtures/medium/unique_9.txt
tests/fixtures/README.md
tests/fixtures/small/novel_exact_dup_1.txt
tests/fixtures/small/novel_exact_dup_2.txt
tests/fixtures/small/novel_exact_dup_3.txt
tests/fixtures/small/novel_normalized_1.txt
tests/fixtures/small/novel_normalized_2.txt
tests/fixtures/small/novel_normalized_3.txt
tests/fixtures/small/novel_unique_1.txt
tests/fixtures/small/novel_unique_2.txt
tests/snapshots/scan_results_edge_cases.json
tests/snapshots/scan_results_medium.json
tests/snapshots/scan_results_small_exact.json
tests/snapshots/scan_results_small_normalized.json
```
