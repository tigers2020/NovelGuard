# 개발 완료 보고서: Phase 4 스텁·자산·벤치마크 정리

> **범위**: 2026-04-11 저장소 감사 후속 — [Phase 4 스텁·자산·벤치마크 정리](../2026-04-11_repo_audit_remediation_plan.md)  
> **완료일**: 2026-04-11  
> **상태**: 완료

---

## 1. 목표 달성 요약

| 목표 | 결과 |
|------|------|
| 미연결 `_stubs` ViewModel 정리 | 달성: `src/gui/view_models/_stubs/` 전체 삭제 (런타임 import 없음 확인) |
| placeholder 탭(`small` / `undo`) UX | 달성: 안내 그룹 + 비활성 컨트롤로 **미구현** 명시 |
| 고아 자산 | 달성: 루트 `sample.html` 삭제 |
| `verify_phase_completion.py` 신뢰성 | 달성: 기본 `python -m pytest`만 실행; 아카이브 골든/벤치는 문서로만 안내 |
| fixtures·snapshots·아카이브 문서 정합 | 달성: `tests/README.md`, `tests/fixtures/README.md`, `tests/_archive/README.md`를 실제 소비 경로에 맞게 갱신 |
| 역사 문서 | 달성: `docs/archive/refactoring/reports/P2-1_stubs_viewmodels.md` 상단에 제거 안내; `TODO_리스트.md` 스텁 항목 정리 |

---

## 2. 배경 (감사 P2-1·Remediation Phase 4)

- `_stubs`·placeholder 탭·`sample.html`·stale 벤치 하네스가 혼재해 **쓰이는 것과 죽은 자산** 구분이 어려웠음.
- `scripts/verify_phase_completion.py`가 `tests/_archive/performance/benchmark_baseline.py` 등을 호출했으나, 해당 스크립트는 삭제된 `infra.*` / `usecases.*`에 의존해 **성공 기준이 허위**였음.

---

## 3. 변경 요약

### 3.1 제거

| 대상 | 비고 |
|------|------|
| `src/gui/view_models/_stubs/*` | `__init__.py` 포함 7파일 |
| `sample.html` | 저장소 내 참조 없음 |

### 3.2 GUI

| 파일 | 내용 |
|------|------|
| `src/gui/views/tabs/small_file_tab.py` | 상단 안내(`QGroupBox`), 주요 버튼·콤보 `setEnabled(False)` |
| `src/gui/views/tabs/undo_tab.py` | 동일 패턴 |

### 3.3 스크립트

| 파일 | 내용 |
|------|------|
| `scripts/verify_phase_completion.py` | 프로젝트 루트에서 `python -m pytest`만 실행; docstring에 아카이브 한계 명시 |

### 3.4 문서

| 파일 | 내용 |
|------|------|
| `tests/README.md` | 스냅샷·픽스처 설명 정합; 기준선 개수 약 144로 갱신 |
| `tests/fixtures/README.md` | 기본 스위트에서 `FIXTURES_DIR` 미사용 명시 |
| `tests/_archive/README.md` | 레거시 하네스 수동 실행 시 실패 가능·CI 미포함·Phase 4 판정 명시 |
| `docs/archive/refactoring/reports/P2-1_stubs_viewmodels.md` | 역사 배너 |
| `TODO_리스트.md` | `_stubs` 경로 목록 제거 및 Phase 4 삭제 반영 |

---

## 4. 검증

| 항목 | 결과 |
|------|------|
| `python -m pytest` | **144 passed** (기본 testpaths) |
| `python scripts/verify_phase_completion.py` | 위와 동일하게 pytest만 실행, exit 0 |
| `python -m mypy src` | Success, 120 source files |
| `ruff check` / `black --check` | `small_file_tab.py`, `undo_tab.py`, `verify_phase_completion.py` 대상 통과 |

---

## 5. 범위 외 (남은 부채)

- `tests/_archive/integration/`·`tests/_archive/performance/` **포팅 없음** — 여전히 구 아키텍처 의존.
- `tests/fixtures/` 대량 파일은 **보관만**; 통합 테스트가 `FIXTURES_DIR`를 쓰기 시작하면 README 소비자 목록을 다시 적는다.
- **Phase 5** (지속 운영 기준선·CI 고정): [해결 계획서](../2026-04-11_repo_audit_remediation_plan.md) 차기 페이즈.

---

## 6. 참고 문서

- `../2026-04-11_repo_audit_remediation_plan.md` — Phase 4 정의
- `../2026-04-11_repo_audit_report.md` — P2-1
- `../../tests/README.md` — 테스트 레이아웃 정본
- `../../tests/_archive/README.md` — 아카이브 하네스 한계
