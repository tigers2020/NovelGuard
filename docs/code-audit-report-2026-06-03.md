# 코드 정밀 분석 보고서 - 2026-06-03

대상: 현재 작업트리 기준 `F:\Python_Projects\NovelGuard`

## 요약

**2026-06-03 hotfix + PR #23 merge 이후:** `python scripts/verify_phase_completion.py` 7/7 PASS. 아래 §결론 참고.

- `python -m pytest`: 통과 (146)
- `npm run test --prefix web`: 통과 (95)
- `npm run build --prefix web`: 통과
- `npm run lint --prefix web`: 통과
- `python -m ruff check .`: 통과
- `python -m mypy src`: 통과

이 문서 본문의 일부 발견 사항은 **hotfix 이전** 스냅샷을 기록한 것이다. 현재 코드 기준 재검증은 verify gate 및 PR #23 CI를 따른다.

## 발견 사항

### 1. Python 품질 게이트 실패

심각도: 높음

근거:

- `src/app/session_factory.py:32`에서 `scan_folder`가 import되지만 사용되지 않는다.
- `src/infrastructure/filesystem_scanner.py:9-13`에서 타입 별칭 선언 뒤 import가 나와 `E402`를 발생시킨다.
- `src/infrastructure/sqlite_library_index.py:12-14` import 정렬이 깨져 있다.
- `tests/test_bridge_contract.py:42-58`에서 `_norm_folder = ...` 할당이 import 블록 중간에 있어 `E402`/`I001`이 발생한다.

영향:

- CI 또는 릴리스 게이트가 `ruff check .`를 요구하면 현재 브랜치는 병합/릴리스 불가 상태다.
- 테스트가 통과해도 코드베이스 정책상 "완료"로 볼 수 없다.

권장 조치:

- import 블록 정리.
- 미사용 `scan_folder` 제거.
- 테스트 파일의 `_norm_folder` 할당을 import 블록 아래로 이동.

### 2. `mypy` 실패: Tkinter folder picker 타입 불일치

심각도: 중간

근거:

- `src/application/library_session.py:189-194`
- `picker_kwargs: dict[str, str]`를 `filedialog.askdirectory(**picker_kwargs)`에 넘기고 있다.
- `mypy` 결과:
  - `Argument 1 to "askdirectory" has incompatible type "**dict[str, str]"; expected "bool | None"`
  - `Argument 1 to "askdirectory" has incompatible type "**dict[str, str]"; expected "Misc | None"`

영향:

- 런타임보다 정적 타입 게이트 문제에 가깝다.
- 현재 테스트가 통과하므로 기능 결함은 아직 입증되지 않았지만, 타입 게이트는 실패한다.

권장 조치:

- `picker_kwargs` 타입을 더 구체적으로 맞추거나 `askdirectory(title=..., initialdir=...)` 형태로 분기 호출한다.

### 3. 스캔 완료 처리 중 `pipeline_running`을 너무 빨리 내림

심각도: 높음

근거:

- `src/application/library_session.py:1057-1079`
- `_scan_folder(...)`가 끝난 직후 `self._pipeline_running = False`와 `self._pipeline_cancellable = False`를 먼저 설정한다.
- 마지막 `flush_batch()`는 그 이후인 `1079`에서 실행된다.
- 정확 중복 인덱스/품질 인덱스 갱신은 `1081-1116`에서 이어진다.

문제:

- 마지막 배치 저장, 정확 중복 인덱스, 품질 인덱스 갱신 전에도 외부에서 세션이 "busy 아님"으로 보일 수 있다.
- `BridgeApi.start_scan()`/`select_folder()`는 `is_apply_or_scan_busy()`에 의존하므로, 아주 짧은 타이밍에 새 scan/select/finalize 계열 액션이 들어오면 부분 인덱스 또는 중간 상태를 밟을 가능성이 있다.

권장 조치:

- `_run_scan`의 전체 저장/인덱스/품질 캐시 갱신이 끝날 때까지 `pipeline_running=True` 유지.
- `post_scan_running`으로 넘기는 순간까지 busy 경계가 끊기지 않게 처리.
- 이 경계에 대한 회귀 테스트 추가: 스캔 마지막 배치 직후 select/start/finalize가 거부되는지 확인.

### 4. 스캔 취소 시 마지막 버퍼 처리 전 취소 판단

심각도: 중간

근거:

- `src/application/library_session.py:1045-1053`에서 `_scan_folder`가 `out=on_record`로 레코드를 누적한다.
- `on_record`는 배치 크기 도달 전까지 `probe_buffer`에만 보관한다.
- `src/application/library_session.py:1070-1077`에서 취소 요청이면 `flush_batch()` 전에 백업 복원을 수행하고 반환한다.

영향:

- 취소 동작이 "부분 결과 폐기" 정책이라면 의도일 수 있다.
- 하지만 현재 구현은 스캐너가 정상 종료한 직후와 마지막 버퍼 저장 전 사이에 취소 플래그가 켜지면, 실제 스캔은 끝났는데 결과는 취소로 처리될 수 있다.

권장 조치:

- 취소 정책을 명확히 분리한다.
  - 스캐너가 취소로 중단됨: 백업 복원.
  - 스캐너가 정상 완료됨: 남은 버퍼 저장 후 완료 처리.
- `scan_folder_stream`이 취소 완료 여부를 반환하지 않으므로, 현재는 정상 완료와 취소 반환을 구분하기 어렵다. 반환값 또는 상태 객체가 필요하다.

### 5. SQLite 배치 저장의 `reset=True`가 전체 `files` 테이블을 삭제함

심각도: 중간

근거:

- `src/infrastructure/sqlite_library_index.py:287-291`
- `append_files_batch(..., reset=True)`에서 `DELETE FROM files`를 실행한다.
- 반면 `replace_files()`는 `DELETE FROM files WHERE folder_path = ?`를 사용한다.

영향:

- 현재 런타임이 "라이브러리별 DB"라는 전제라면 실질 영향은 제한적이다.
- 그러나 같은 DB에 여러 `folder_path`가 남을 수 있는 테스트/마이그레이션/임시 pending DB 흐름에서는 의도치 않게 다른 폴더 파일 행을 삭제할 수 있다.

권장 조치:

- 실제로 per-library DB가 불변 계약인지 문서/테스트로 고정.
- 그렇지 않다면 `DELETE FROM files WHERE folder_path = ?`로 좁힌다.
- `reset=True`가 다른 folder row를 보존하는지 회귀 테스트 추가.

### 6. Post-scan 백그라운드 실패가 UI에는 성공처럼 보일 수 있음

심각도: 중간

근거:

- `src/application/library_session.py:1124-1144`
- `_start_post_scan_detection_thread()`에서 예외를 로그만 남기고 `finally`에서 `_deep_analysis_complete=True`, `_pipeline_phase="idle"`, `_pipeline_label="대기 중"`으로 설정한다.

영향:

- 근사 중복/관계 분석 실패 시 사용자는 분석이 완료된 것처럼 볼 수 있다.
- 로그를 보지 않으면 데이터가 누락된 상태를 성공 상태로 오해할 수 있다.

권장 조치:

- post-scan 실패 플래그 또는 경고 카운트를 snapshot에 노출.
- 실패 시 `deep_analysis_complete=False` 또는 별도 `deep_analysis_status="error"` 상태 도입.
- 해당 경로를 테스트로 고정.

### 7. Frontend ESLint 경고: TanStack Table과 React Compiler 호환성

심각도: 낮음

근거:

- `web/src/components/grid/VirtualizedDataGrid.tsx:95`
- `useReactTable()` 사용부에서 `react-hooks/incompatible-library` 경고가 발생한다.

영향:

- 현재 `npm run lint --prefix web`는 exit code 0이고 빌드/테스트도 통과한다.
- 다만 React Compiler 최적화가 해당 컴포넌트를 스킵할 수 있어, 장기적으로 성능 기대치와 다를 수 있다.

권장 조치:

- 의도된 경고라면 파일 단위/라인 단위로 명시적 예외 처리.
- 아니면 테이블 훅 결과를 memoized child에 전달하지 않는 구조인지 점검.

## 테스트 커버리지 관찰

현재 테스트 수는 적지 않지만 특정 위험 경계가 약하다.

- Python 브리지 계약 테스트는 많고 통과한다.
- Frontend 계약/브리지 테스트도 통과한다.
- 하지만 스캔 파이프라인의 동시성 경계, 마지막 배치 flush 시점, post-scan 실패 노출은 직접적인 테스트가 부족하다.

추가된 regression 테스트 (2026-06-03 hotfix):

- `test_run_scan_keeps_busy_until_tail_flush_and_indexes_complete`
- `test_scan_normal_completion_flushes_tail_buffer_even_if_cancel_requested_after_scanner_returns`
- `test_append_files_batch_reset_preserves_other_folder_rows`
- `test_post_scan_exception_is_exposed_in_snapshot`

## 우선순위 (처리 완료)

1. ~~`ruff` 실패 수정.~~
2. ~~`mypy` 실패 수정.~~
3. ~~`_run_scan`의 busy 상태 전환과 마지막 배치 flush 순서 재정리.~~
4. ~~post-scan 실패 상태를 snapshot/API 계약에 반영.~~
5. ~~SQLite batch reset 범위 계약 확정.~~
6. ~~Frontend ESLint 경고를 의도적으로 처리.~~

## 결론

**`MERGE-READY` (hotfix slice, 2026-06-03).**

`python scripts/verify_phase_completion.py` 7/7 PASS (`pytest`, `ruff`, `mypy`, `black`, `npm run lint`, `npm run test`, packaging verify). 스캔 busy 경계, `ScanStreamResult` 취소 정책, folder-scoped SQLite reset, `deepAnalysisStatus`/`deepAnalysisError` snapshot 계약, ScanWorkspace 오류 배너가 반영되었다.

브랜치 `pr42-bridge-regression`에 hotfix 6커밋이 분리되어 있으며, 동일 브랜치의 unstaged WIP(스캔 스트리밍·셸 UI 등)는 별도 슬라이스로 PR/커밋 정리가 필요할 수 있다.
