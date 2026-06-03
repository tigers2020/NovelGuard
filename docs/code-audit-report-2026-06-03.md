# 코드 정밀 분석 보고서 - 2026-06-03

**대상:** `main` @ `56634ba` (PR #23 merge + e2e fix)  
**재검증:** 2026-06-03 — `python scripts/verify_phase_completion.py` **7/7 PASS**, Playwright e2e **29/29 PASS**, GitHub `main` CI **success**

---

## 요약

| 게이트 | 결과 |
|--------|------|
| `python scripts/verify_phase_completion.py` | 7/7 PASS |
| `python -m pytest` | 146 passed |
| `python -m ruff check .` | PASS |
| `python -m mypy src` | PASS |
| `python -m black --check .` | PASS |
| `npm run lint` / `npm run test` / `npm run build` (web) | PASS |
| `npx playwright test` (web/e2e) | 29 passed |
| GitHub Actions `main` | success |

**판정: `MERGE-READY` — 감사 시점 이슈는 hotfix로 해소됨.**

---

## 원본 발견 사항 → 조치 결과

### 1. Python 품질 게이트 (`ruff`)

| 항목 | 원본 | 조치 |
|------|------|------|
| 미사용 `scan_folder` import | `session_factory.py` | 제거 (`scan_folder_stream`만 사용) |
| `E402` import 순서 | `filesystem_scanner.py` | import 블록 상단 정리 |
| import 정렬 | `sqlite_library_index.py` | 정렬 |
| `E402`/`I001` in tests | `test_bridge_contract.py` | import 블록 정리, `normalize_library_folder_path` 직접 사용 |

**상태:** 해소. `ruff check .` PASS.

### 2. `mypy` — Tkinter `askdirectory`

| 항목 | 원본 | 조치 |
|------|------|------|
| `**dict[str, str]` unpacking | `library_session.select_folder` | `title` / `initialdir` 명시 인자 분기 |

**상태:** 해소. `mypy src` PASS.

### 3. 스캔 완료 시 `pipeline_running` 조기 해제

| 항목 | 원본 | 조치 |
|------|------|------|
| `_scan_folder` 직후 `pipeline_running=False` | `_run_scan` | `scan_persist` 단계에서 busy 유지 → tail `flush_batch()` → `post_scan_running`과 **동일 lock**에서 전환 |
| 회귀 테스트 없음 | tests | `test_run_scan_keeps_busy_until_tail_flush_and_indexes_complete` |

**상태:** 해소.

### 4. 스캔 취소 vs 정상 완료 혼동

| 항목 | 원본 | 조치 |
|------|------|------|
| 취소/완료 구분 불명 | `scan_folder_stream` | `ScanStreamResult(completed, cancelled, scanned_count)` 반환 |
| 완료 후 cancel 무시 없음 | `_run_scan` | 스캐너 정상 완료 후 `cancel_run` 무시, tail flush·완료 처리 |
| 회귀 테스트 | tests | `test_scan_normal_completion_flushes_tail_buffer_even_if_cancel_requested_after_scanner_returns`, `test_cancel_scan_discards_partial` (`ScanStreamResult`) |

**상태:** 해소.

### 5. SQLite `append_files_batch(reset=True)` 전체 삭제

| 항목 | 원본 | 조치 |
|------|------|------|
| `DELETE FROM files` | `sqlite_library_index.py` | `DELETE FROM files WHERE folder_path = ?` |
| 회귀 테스트 | tests | `test_append_files_batch_reset_preserves_other_folder_rows` |

**상태:** 해소.

### 6. Post-scan 실패가 UI에 성공처럼 보임

| 항목 | 원본 | 조치 |
|------|------|------|
| 예외 시에도 idle/complete | `_start_post_scan_worker` | `deepAnalysisStatus`: `idle` \| `running` \| `complete` \| `error`; 실패 시 `deepAnalysisComplete=False`, `deepAnalysisError` 설정 |
| snapshot/UI 미노출 | dto + contract + web | `deepAnalysisStatus`, `deepAnalysisError`; ScanWorkspace `data-testid="deep-analysis-error"` 배너 |
| 회귀 테스트 | tests | `test_post_scan_exception_is_exposed_in_snapshot` |

**상태:** 해소.

### 7. Frontend ESLint — TanStack Table

| 항목 | 원본 | 조치 |
|------|------|------|
| `react-hooks/incompatible-library` 경고 | `VirtualizedDataGrid.tsx` | 의도 주석 (`eslint-disable-next-line`) |

**상태:** 해소. `npm run lint` 경고 0.

### 8. E2E — Settings diagnostics (후속 fix `56634ba`)

| 항목 | 원본 | 조치 |
|------|------|------|
| `app-info-diagnostics` not visible | `smoke.spec.ts` | PR-40 2섹션 UI: `settings-nav-app` 클릭 후 assert |

**상태:** 해소. e2e 29/29 PASS.

---

## 테스트 커버리지 (hotfix 이후)

- Python 브리지/계약: 146 tests, 통과.
- Web vitest: 95 tests, 통과.
- Playwright smoke: 29 tests, 통과 (PR-43 full pipeline 포함).
- 스캔 busy / cancel / SQLite reset / post-scan error: 위 §3–§6 regression 4건 + 기존 cancel 테스트 갱신.

---

## 커밋·병합 이력 (참고)

| 커밋/PR | 내용 |
|---------|------|
| PR #23 → `main` | hotfix 6커밋 + release-gate WIP |
| `56634ba` | e2e settings `settings-nav-app` navigation |
| `a5038b7` | 본 보고서 MERGE-READY 갱신 (초안) |

---

## 결론

**`MERGE-READY`.** 감사 당시 `PROCEED WITH CONDITIONS`였던 항목(ruff, mypy, 스캔 busy 경계, 취소 정책, SQLite reset, post-scan snapshot, ESLint, e2e settings)은 **`main`에 반영·검증 완료**다.

남은 추적 작업(로드맵·스펙 범위, hotfix와 무관):

- [plan 046](../superpowers/plans/046-2026-06-03-infra-scan-streaming-phases.md) — 스캔 스트리밍 후속
- [plan 047](../superpowers/plans/047-2026-06-03-feature-ui-layout-pane-hierarchy-minimal.md) — 레이아웃 pane hierarchy

이들은 본 hotfix 범위 밖이며, 별도 PR로 진행한다.
