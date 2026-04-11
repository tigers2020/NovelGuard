# 2026-04-11 저장소 전수 감사 리서치

> 상태: 완료
> 작성일: 2026-04-11
> 목적: 코드 수정 없이 저장소 전반의 현재 상태를 계측하고, 최종 감사 리포트의 범위와 증거 체계를 확정한다.

## 1. 감사 범위 결정

- 최초 계획 초안은 `378 tracked + 9 untracked`를 가정했지만, 실제 감사 기준선은 달랐다.
- 기준선 명령 재실행 결과:
  - `git status --short`: 출력 없음
  - `git -c core.quotepath=false ls-files`: `387` tracked files
  - `git -c core.quotepath=false ls-files --others --exclude-standard`: `0` meaningful untracked files
- 따라서 2026-04-11 감사 대상은 "문서 작성 전 시점의 tracked 387개 파일 전체"로 확정했다.
- 이번 작업에서 생성하는 `documents/2026-04-11_repo_audit_*.md` 3개 파일은 감사 산출물이며, 감사 대상 기준선에는 포함하지 않았다.

## 2. 포함/제외 규칙

- 포함:
  - 루트 설정 및 운영 문서
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

## 3. 인벤토리 스냅샷

| 버킷 | 파일 수 |
|---|---:|
| `docs/` | 45 |
| `documents/` | 2 |
| `persona/` | 2 |
| `protocols/` | 2 |
| `scripts/` | 2 |
| `src/` | 127 |
| `tests/` | 190 |
| 루트 기타 | 17 |
| 합계 | 387 |

세부 하위 트리 확인:

| 경로 | 파일 수 |
|---|---:|
| `src/app/` | 5 |
| `src/application/` | 40 |
| `src/domain/` | 17 |
| `src/gui/` | 52 |
| `src/infrastructure/` | 11 |
| `tests/app/` | 5 |
| `tests/application/` | 13 |
| `tests/domain/` | 25 |
| `tests/fixtures/` | 122 |
| `tests/gui/` | 3 |
| `tests/infrastructure/` | 2 |
| `tests/integration/` | 6 |
| `tests/performance/` | 4 |
| `tests/snapshots/` | 4 |

## 4. 감사 버킷 설계

최종 리포트의 전수 커버리지는 아래 세 상태로 닫는다.

| 상태 | 의미 | 파일 수 |
|---|---|---:|
| `finding recorded` | 모순, 결함, 드리프트, 죽은 코드, stale artifact가 확인된 파일 | 121 |
| `checked/no issue` | 읽고 검토했으나 이번 감사에서 별도 리스크를 기록하지 않은 파일 | 140 |
| `grouped asset bucket` | 개별 자산은 모두 검토했지만, 성격상 묶어서 설명하는 fixture/snapshot 계열 | 126 |
| 합계 |  | 387 |

- `121 + 140 + 126 = 387`로 기준선 tracked 파일 수와 일치한다.
- 정본 per-file ledger는 최종 리포트 부록에 수록한다.

## 5. 기준선 재실행 요약

감사 중 비파괴 기준선을 다시 돌린 결과는 아래와 같다.

| 명령 | 결과 |
|---|---|
| `python -m black --check .` | `72 files would be reformatted` |
| `python -m ruff check .` | `1690 errors`, 그중 `1345`개 자동 수정 가능 |
| `python -m mypy src` | `163 errors in 26 files` |
| `python -m pytest` | collection 단계에서 `21 errors`로 중단 |
| 선택한 현행 테스트 묶음 | `78 passed in 1.53s` |

현행 구조를 따르는 테스트 묶음은 아래 8개 파일로 다시 확인했다.

- `tests/app/settings/test_constants.py`
- `tests/application/use_cases/duplicate_detection/test_pipeline_basic.py`
- `tests/application/use_cases/duplicate_detection/stages/test_blocking_stage.py`
- `tests/gui/workers/test_duplicate_detection_worker.py`
- `tests/infrastructure/db/test_sqlite_index_repository.py`
- `tests/integration/test_scan_with_index_repository.py`
- `tests/integration/test_snapshot_normalizer.py`
- `tests/application/use_cases/test_organize_by_chosung.py`

## 6. 초기 핵심 신호

1. 검증 체계가 두 세계로 갈라져 있다.
   - 레거시 테스트는 삭제된 `app.bootstrap`, `app.workflows`, `infra.*`, `usecases.*`, `domain.models.*`를 import한다.
   - 반면 현행 구조를 따르는 테스트들은 정상 통과한다.
2. 문서와 실제 코드 구조가 심하게 어긋난다.
   - `docs/entry_points.md`, `docs/refactoring*`, `docs/refactoring_plan_v1.4/*`, `docs/phase1_completion_report.md` 다수가 존재하지 않는 `src/app/bootstrap.py`, `src/app/workflows/`, `FileRepository`, `ScanFilesUseCase`를 현재 사실처럼 기록한다.
   - 실제 진입점은 `src/main.py -> src/app/main.py` 직결 구조다.
3. 포트 추상화가 GUI 계층에서 무너진다.
   - `.cursor/rules/architecture.mdc`는 GUI가 application DTO/use case에만 의존하고 concrete infrastructure 세부를 직접 알지 말라고 규정한다.
   - 하지만 `scan_view_model.py`, `duplicate_view_model.py`, `main_window.py`는 `IJobRunner`에 없는 `job_started`, `start_duplicate_detection`, `set_file_data_store`에 직접 의존한다.
4. 정적 품질 기준선이 낮다.
   - GUI 계층, `containment_detector.py`, `filename_parse_result.py`, `sqlite_index_repository.py`가 현재 lint/type hotspot이다.
5. 미연결 스텁과 stale artifact가 쌓여 있다.
   - `_stubs/` view model, `sample.html`, `verify_phase_completion.py`, 레거시 golden/performance 자산이 현재 구조와 어긋난다.

## 7. 커버리지 레저 정책

- 모든 in-scope tracked 파일은 최종 리포트 부록에서 정확히 한 번만 분류한다.
- 분류 기준:
  - `finding recorded`: 본문에서 직접 근거를 인용한 파일
  - `checked/no issue`: 읽었지만 별도 위험을 남기지 않은 파일
  - `grouped asset bucket`: fixture/snapshot처럼 묶어서 설명한 파일
- 산출물 문서 3개는 감사 결과물이지 감사 대상 기준선이 아니므로 부록에서 제외한다.
