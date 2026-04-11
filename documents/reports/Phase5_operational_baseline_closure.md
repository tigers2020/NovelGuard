# 개발 완료 보고서: Phase 5 마감 및 지속 운영 기준선

> **범위**: [2026-04-11 저장소 감사 후속 해결 계획서](../2026-04-11_repo_audit_remediation_plan.md) — Phase 5  
> **완료일**: 2026-04-11  
> **상태**: 완료

---

## 1. 목표 대조 (해결 계획서)

| 목표 | 결과 |
|------|------|
| 정리된 기준선을 운영 규칙·CI에 고정 | 달성: `AGENTS.md`, `README.md`, `docs/current_architecture.md`, `.cursor/rules/cursor-usage.mdc`, `pyproject.toml`, `.github/workflows/ci.yml`, `scripts/verify_phase_completion.py` |
| 검증 명령 단일 진입점 | 달성: `python scripts/verify_phase_completion.py` (pytest → ruff → mypy → black `--check`, fail-fast) |
| 문서·코드·검증 어긋남 방지 | 달성: 전역 `ruff check .` / `black --check .` 통과; 제외 정책을 `pyproject.toml`에 명시 |

---

## 2. 변경 요약

### 2.1 `pyproject.toml`

- **`tool.ruff.exclude`**: 캐시·가상환경·`tests/_archive` 및 pytest `collect_ignore`와 동일한 레거시 트리(`tests/common`, `tests/domain`, `tests/infra`), `tests/app/test_bootstrap.py`, `tests/app/test_workflows.py`.
- **`tool.black.extend-exclude`**: `tests/_archive/` (기존 유지).

### 2.2 코드·테스트

- `ruff check . --fix` 및 `black .`로 저장소 전역 포맷·정렬 정리.
- 활성 통합/인프라 테스트에서 중복 `sys.path` 조작 제거 (`tests/conftest.py`의 `pythonpath`와 정합): `test_scan_with_index_repository.py`, `test_snapshot_normalizer.py`, `test_sqlite_index_repository.py`.
- 불필요한 no-op/미사용 코드 일부 정리 (`test_scan_with_index_repository.py`).

### 2.3 검증 스크립트

- **`scripts/verify_phase_completion.py`**: 위 네 단계 파이프라인; 로그는 CI 호환을 위해 요약 문구는 영어.

### 2.4 CI

- **`.github/workflows/ci.yml`**: Python 3.12, `pip install -e ".[dev]"`, `pytest` → `ruff check .` → `mypy src` → `black --check .` (`push`/`pull_request` to `main`/`master`).

### 2.5 문서

- **`AGENTS.md`**: 통합 검증 행, PR·머지 전 체크리스트.
- **`README.md`**: `scripts/` 트리 설명, 검증 한 줄, 기여 절차.
- **`docs/current_architecture.md`**: 스크립트·제외 정책 안내.
- **`.cursor/rules/cursor-usage.mdc`**: 로컬 검증 권장 한 줄.

---

## 3. 검증 (실행 시점 기준)

| 명령 | 결과 |
|------|------|
| `python -m pytest` | 144 passed (기본 testpaths) |
| `python -m ruff check .` | All checks passed |
| `python -m mypy src` | Success |
| `python -m black --check .` | All files unchanged |
| `python scripts/verify_phase_completion.py` | Exit 0 |

환경 예: Windows, Python 3.13.x (로컬). CI는 Python 3.12.

---

## 4. 알려진 한계·후속

- **`tests/unit/` Git 추적**: `testpaths`에 포함되므로 **저장소에 추적**되어야 클론·CI에서 문서상 건수(예: 144 passed)가 재현된다. 미추적이었던 경우 보고서와 불일치가 나므로, 정책은 “항상 `git ls-files tests/unit`로 비어 있지 않게 유지”한다.
- **기타 산출물**: `persona/` 역할 카드·`scripts/run_duplicate_check_cli.py` 등은 편의용이다. 추적 여부는 팀 선택이나, **미추적만 두면** 로컬 워크트리와 “저장소 기준 완료”가 어긋날 수 있으므로, 필요하면 함께 커밋하거나 README/본 문서에 “선택·미추적 가능”을 명시한다.
- **`tests/_archive/`**: 포팅 없음; pytest/ruff/black에서 제외. 수동 실행 시 실패 가능 — [tests/_archive/README.md](../../tests/_archive/README.md).
- **기본 브랜치 이름**: 워크플로는 `main`/`master`만 트리거. 저장소 기본 브랜치가 다르면 `ci.yml`의 `branches` 목록을 맞출 것.
- **레거시 트리**: ruff에서 제외된 `tests/domain` 등은 여전히 저장소에 있으며, black은 이번 작업에서 포맷됨; 향후 해당 트리를 삭제·포팅하면 exclude를 축소할 수 있음.

---

## 5. 참고

- [../2026-04-11_repo_audit_remediation_plan.md](../2026-04-11_repo_audit_remediation_plan.md)  
- [../../AGENTS.md](../../AGENTS.md)  
- [../../docs/current_architecture.md](../../docs/current_architecture.md)
