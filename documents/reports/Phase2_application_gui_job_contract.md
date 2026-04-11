# 개발 완료 보고서: Phase 2 application–GUI Job 계약 재설계

> **범위**: 2026-04-11 저장소 감사 후속 — [Phase 2 application–GUI 계약 재설계](../2026-04-11_repo_audit_remediation_plan.md)  
> **완료일**: 2026-04-11  
> **상태**: 완료

---

## 1. 목표 달성 요약

| 목표 | 결과 |
|------|------|
| `IJobRunner`와 GUI 사이 암묵적 결합(`hasattr`, Qt 시그널 직접 가정) 제거 | 달성: 뷰모델은 `subscribe(JobEvent)` + 포트 메서드만 사용 |
| 중복 탐지 시작을 포트에 명시 | 달성: `start_duplicate_detection(DuplicateDetectionRequest) -> int`를 `IJobRunner`에 추가, `QtJobManager`와 일치 |
| `FileDataStore` 주입 책임을 composition root로 이동 | 달성: `app/main.py`에서 `AppState`·`file_data_store` 확보 후 `QtJobManager`·`MainWindow`에 주입 |
| `set_file_data_store` 등 GUI 쪽 후속 와이어링 제거 | 달성: `QtJobManager`에서 해당 API 제거, `MainWindow`의 `hasattr` 블록 제거 |
| 계약 검증용 테스트 | 달성: `tests/gui/view_models/test_duplicate_view_model_jobs.py`, `tests/gui/conftest.py`의 `qapp` |

---

## 2. 배경 (감사 P1-2·해결 계획 Phase 2)

- `IJobRunner`는 `start_scan` / `subscribe` 등만 정의돼 있었으나, GUI는 `job_started` 시그널·`start_duplicate_detection`·`set_file_data_store`에 `hasattr`로 의존해 **포트 계약과 실제 사용이 불일치**.
- `.cursor/rules/architecture.mdc`에 맞게 **조립은 `app`**, GUI는 application DTO/port에 의존해야 하나, 와이어링이 `MainWindow`에 새어 나가 있었음.

---

## 3. 변경 사항

### 3.1 Application 포트

| 파일 | 내용 |
|------|------|
| `src/application/ports/job_runner.py` | `start_duplicate_detection` 추가, docstring을 `subscribe(JobEvent)` 중심으로 정리 |

### 3.2 GUI 뷰모델

| 파일 | 내용 |
|------|------|
| `src/gui/view_models/scan_view_model.py` | `job_manager.subscribe(self._on_job_event)`; `JobType.SCAN`만 처리하는 이벤트 디스패치 |
| `src/gui/view_models/duplicate_view_model.py` | 동일 패턴(`DUPLICATE`); `start_duplicate_detection(request)` 직접 호출 |

### 3.3 Job 관리·조립

| 파일 | 내용 |
|------|------|
| `src/gui/services/qt_job_manager.py` | `set_file_data_store` 제거; `_jobs` 타입을 `ScanWorker` / `DuplicateDetectionWorker` 유니온으로 명시; 외부 Qt 시그널은 유지(뷰모델은 미사용); `_emit_event`에 리스너 스레드 맥락 설명 docstring; 리스너 예외 시 로그용 import 정리 |
| `src/app/main.py` | `AppState` 생성 → `set_log_sink` → `file_data_store` 확보 → `QtJobManager(..., file_data_store=...)` → `MainWindow(..., app_state=...)` |
| `src/gui/views/main_window.py` | `app_state` 인자(미전달 시 내부 `AppState()`); QSettings 복원 경로 `Path(str(...))`로 타입 정합 |

### 3.4 테스트

| 파일 | 내용 |
|------|------|
| `tests/gui/conftest.py` | 세션 스코프 `qapp` 픽스처 |
| `tests/gui/view_models/test_duplicate_view_model_jobs.py` | `Mock(spec=IJobRunner)`로 `subscribe`·`start_duplicate_detection`·완료/실패 이벤트 경로 검증 |

### 3.5 문서

| 파일 | 내용 |
|------|------|
| `docs/current_architecture.md` | `AppState`·`file_data_store` 주입·`IJobRunner` 메서드 요약 반영 |
| `docs/entry_points.md` | composition 단계에 `AppState`·`QtJobManager` 인자·`MainWindow(app_state=...)` 반영 |

---

## 4. 검증

| 항목 | 결과 |
|------|------|
| `python -m pytest` | **144 passed** (기본 `testpaths`; 환경에 따라 건수 소폭 차이 가능) |
| `python -m pytest tests/gui/workers/test_duplicate_detection_worker.py -q` | 통과 (계획서 회귀 항목) |
| `python -m mypy --follow-imports=silent` (본 Phase에서 수정한 주요 `src` 파일군) | **통과** — 변경 파일 단위 기준선 |
| `python -m mypy src` (저장소 전역) | **미달성(既知 부채)**: 감사 리포트 및 Remediation **Phase 3** 범위 |

---

## 5. 완료 기준 대조 (해결 계획서 Phase 2)

- GUI에 `hasattr(job_manager, 'job_started'|'start_duplicate_detection')` 및 `hasattr(..., 'set_file_data_store')` 없음 — **충족** (`src` 기준 grep).
- `IJobRunner`와 `QtJobManager` 구현 일치(`start_duplicate_detection` 포함) — **충족**.
- `FileDataStore` 연결이 `app/main.py` 조립에서 끝남 — **충족**.

---

## 6. 범위 외 (후속 페이즈)

- 저장소 전역 `ruff` / `mypy` / `black` — **Phase 3**.
- 스텁·플레이스홀더 탭·벤치·골든 재정의 — **Phase 4**.
- 지속 운영 기준선 고정 — **Phase 5**.

---

## 7. Phase 0·1 보고서와의 정합

- Phase 1 보고서 §6에 “`IJobRunner`·GUI 계약 재설계 — Phase 2”로 남겨 두었던 항목 — **본 보고서로 이행 완료**.
- Phase 1에서 정본화한 `entry_points`·`current_architecture` — **본 Phase에서 Job 조립·포트 설명을 추가 갱신**해 드리프트 방지.

---

## 8. 참고 문서

- `../2026-04-11_repo_audit_remediation_plan.md` — Phase 2 정의
- `../2026-04-11_repo_audit_report.md` — P1-2 (GUI·`IJobRunner` 결합)
- `../../docs/current_architecture.md` — 현행 구조 정본
- `../../docs/entry_points.md` — 진입점·composition 상세
- `../../tests/README.md` — 테스트 레이아웃 정본
