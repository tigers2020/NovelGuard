# 개발 완료 보고서: Phase 3 정적 품질 hotspot 상환

> **범위**: 2026-04-11 저장소 감사 후속 — [Phase 3 정적 품질 hotspot 상환](../2026-04-11_repo_audit_remediation_plan.md)  
> **완료일**: 2026-04-11  
> **상태**: 완료

---

## 1. 목표 달성 요약

| 목표 | 결과 |
|------|------|
| domain/infra/GUI 우선순위 파일의 mypy·타입 일관성 | 달성: `python -m mypy src` — **127개 파일, 이슈 0** |
| ruff/black (본 Phase에서 수정한 경로) | 달성: 지정 25개 파일에 대해 `ruff check` 통과, `black --check` 통과 |
| 디버그 `print` 정리 | 달성: `FileDataStore`, `FileListTableWidget` → `logging`; `PreviewWorker` → `logger.warning`; `InMemoryLogSink`는 모듈 docstring으로 콘솔 `print` 의도 명시 |
| 회귀 | 달성: 기본 `pytest` **144 passed** |

---

## 2. 배경 (감사 P1-3·P2-2·Remediation Phase 3)

- 감사 시점 `mypy`/`ruff`/`black`이 저장소 전역에서 대량 실패 상태였고, Phase 0–2는 테스트·문서·Job 계약만 정리한 상태였음.
- 본 Phase는 계획서에 명시된 **hotspot 파일**을 중심으로 타입·Qt6 enum·Optional 산술·`print`를 정리하고, 동일 경로에 한해 ruff/black 기준선을 맞춤.

---

## 3. 변경 요약 (주요 파일)

### 3.1 Domain

| 파일 | 내용 |
|------|------|
| `src/domain/value_objects/filename_parse_result.py` | `segments`/`tags` `None` 안전 처리, `segment_type` dict 키 정규화, `range_contains`에서 `range_*` 명시적 narrow |
| `src/domain/services/containment_detector.py` | import 순서·`Any` evidence 타입, `tuple[int,int]` file_id, 세그먼트 `or []`, `_try_version_via_range`에서 `range_end` None 가드 |
| `src/domain/services/near_duplicate_detector.py` | 범위 overlap 시 `range_*` None 가드 |
| `src/domain/services/keeper_score_service.py` | `has_range` 분기에서 `range_start`/`range_end` None 가드 |

### 3.2 Application / Infrastructure

| 파일 | 내용 |
|------|------|
| `src/application/utils/duplicate_json.py` | `evidence_dict: Dict[str, Any]`로 mypy 할당 오류 제거 |
| `src/infrastructure/db/sqlite_index_repository.py` | `lastrowid` None 방어, `list_files` SQL 파라미터 `list[Any]` |
| `src/infrastructure/logging/in_memory_log_sink.py` | 콘솔 `print` 사용 의도를 모듈 docstring에 명시 |

### 3.3 GUI / Qt 6 (PySide6)

| 파일 | 내용 |
|------|------|
| `duplicate_groups_table_model.py` 등 | `QModelIndex \| QPersistentModelIndex`, `Qt.ItemDataRole` / `Qt.Orientation`, 필수 `file_data_store`는 keyword-only `*` |
| `file_list_table.py`, `dry_run_preview_dialog.py`, 테이블 뷰들 | `QAbstractItemView` / `QHeaderView.ResizeMode` / `Qt.SortOrder` 등 enum 네임스페이스 정리 |
| `settings_tab.py` | `QSettings.value` → `typing.cast`, `Qt.Orientation.Horizontal` |
| `scan_tab.py`, `duplicate_tab.py`, `move_organize_tab.py` | `_get_app_state` 및 설정 조회 반환값에 `cast`/`str`/`bool` 정리 |
| `stats_tab.py` | `_format_file_size`에서 float 누적 변수 분리 |
| `sidebar.py`, `header.py`, `base_tab.py` | `CursorShape`, `AlignmentFlag`, `ScrollBarPolicy` |

### 3.4 로깅

| 파일 | 내용 |
|------|------|
| `src/gui/models/file_data_store.py` | 배치 시그널 디버그 `print` → `logger.debug` |
| `src/gui/views/components/file_list_table.py` | 동일 |
| `src/gui/workers/preview_worker.py` | 디렉터리 스캔 예외 `print` → `logger.warning` |

---

## 4. 검증

| 명령 | 결과 |
|------|------|
| `python -m mypy src` | Success, 127 files |
| `python -m pytest` | 144 passed |
| `python -m ruff check` (본 Phase에서 수정한 25개 파일 경로) | All checks passed |
| `python -m black --check` (동일 25개 파일) | All unchanged |

---

## 5. 범위 외 (남은 부채)

- **`ruff check src` / `black --check` 전 저장소**: `pyproject.toml`의 `src` 전체는 여전히 기존 포맷·W293 등 누적이 큼. 본 Phase는 **수정한 파일 집합**에 한해 린트·포맷을 닫았음 (감사 Remediation 및 Phase 1 보고서와 동일한 “전역 black은 별도 과제” 전제).
- **Phase 4**: 스텁·벤치·골든·placeholder 탭 정리 등은 미착수.

---

## 6. 참고 문서

- `../2026-04-11_repo_audit_remediation_plan.md` — Phase 3 정의
- `../2026-04-11_repo_audit_report.md` — P1-3 typing, P2-2 print
- `../../docs/current_architecture.md` — 구조 정본
