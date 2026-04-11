# 개발 완료 보고서: Phase 1 문서·운영 기준 정본화

> **범위**: 2026-04-11 저장소 감사 후속 — [Phase 1 문서와 운영 기준 정본화](../2026-04-11_repo_audit_remediation_plan.md)  
> **완료일**: 2026-04-11  
> **상태**: 완료

---

## 1. 목표 달성 요약

| 목표 | 결과 |
|------|------|
| 현재 구조를 설명하는 단일 정본 문서 집합 | 달성: `docs/current_architecture.md` 신설, README·AGENTS에서 링크 |
| README / pyproject / requirements / entry_points 모순 제거 | 달성: Python `3.12+`, 런타임 vs `.[dev]`, 진입점은 실제 `src/app/main.py` 조립과 일치 |
| 리팩터링·완료 보고 문서의 역사 구역 구분 | 달성: 상단 배너 + `docs/refactoring/README.md` 허브 (대규모 경로 이동 없음) |
| `.gitignore`의 tracked 트리 오·중복 ignore 정리 | 달성: `tests/` 등 소스 디렉터리 ignore 제거, 중복 항목 정리 |
| 운영 정책 문서 계층 | 달성: `AGENTS.md` + `.cursor/rules/*` 정본, persona/protocol은 위임 문구 보강 |

---

## 2. 배경 (감사 P0 문서·P1-1·P3-1)

- `docs/entry_points.md` 등이 존재하지 않는 `bootstrap.py`·구형 유스케이스 조립을 서술해 **현재 코드와 불일치**.
- README는 Python 3.10+, `pyproject.toml`은 `>=3.12`, `requirements.txt`는 pytest·psutil 포함 등 **정본이 갈림**.
- `.gitignore` 하단에 이미 추적 중인 `tests/`, `protocols/`, `persona/`, `scripts/` 등이 포함되어 **신규 파일 추적 리스크**(Phase 0 보고서 §6에서도 언급).
- `docs/refactoring*` 및 v1.4 완료 보고가 **현행 설계 문서처럼 읽히는** 문제.

---

## 3. 변경 사항

### 3.1 정본 아키텍처 문서 (신규)

| 파일 | 내용 |
|------|------|
| `docs/current_architecture.md` | 지원 환경(`pyproject`), 공식 진입점, composition root 실제 객체 목록, `src/` 레이어 표, 테스트·검증 명령, 관련 링크 |

### 3.2 진입점·루트 문서

| 파일 | 내용 |
|------|------|
| `docs/entry_points.md` | `src/main.py` → `app.main.main()`, `app/main.py` 직접 조립 흐름, 보조 `python -m app.main`, 금지 사항·FAQ |
| `README.md` | 정본 링크, Python 3.12+, 디렉터리 트리, `pip install -r` / `pip install -e .` / `pip install -e ".[dev]"`, 런타임 라이브러리 표 |
| `AGENTS.md` | 문서 정본 한 줄, 빌드 표에 런타임·개발 설치 구분 |

### 3.3 의존성 정본

| 파일 | 내용 |
|------|------|
| `requirements.txt` | 런타임 4종만 (`PySide6`, `charset-normalizer`, `pydantic`, `xxhash`), `pyproject` `[project].dependencies`와 동일 하한 |
| `pyproject.toml` | `[project.optional-dependencies] dev`에 `psutil>=5.9.0` 추가 (`pytest` 등과 함께 개발 스위트) |

### 3.4 역사 문서 표기 (물리 이동 최소)

| 파일 | 내용 |
|------|------|
| `docs/refactoring/README.md` | 신설: 역사 기록 안내 + `current_architecture.md` 링크 |
| `docs/refactoring/reports/README.md` | 상단 역사 구역 배너 |
| `docs/refactoring_plan_v1.4/README.md` | 상단 역사·계획 아카이브 배너 |
| `docs/phase1_completion_report.md` | v1.4 관점 Phase 1 보고임을 명시(현 코드와 불일치 가능) |

### 3.5 운영 문서 계층 (P3-1 완화)

| 파일 | 내용 |
|------|------|
| `protocols/README.md` | 정책 정본은 AGENTS + `.cursor/rules` 우선 |
| `persona/README.md` | 게이트·검증 정본은 AGENTS |
| `persona/novelguard_developer.md` | 플랜 승인·검증은 AGENTS 정본 |

**참고**: 해결 계획서 대상에 `protocols/development_protocol.md`가 포함되어 있으나, 본 Phase에서는 **절차·컨벤션 본문의 대대적 개정 없이** 정본 위임은 README 계층으로 처리함. 향후 절차 문서와 `docs/current_architecture.md` 간 교차 링크만 보강해도 충분함.

### 3.6 `.gitignore`

- `tests/`, `protocols/`, `persona/`, `scripts/`, `.cursor/`, `.vscode/` 등 **소스 트리를 가리던 규칙 블록 제거**.
- `logs/`·`.cursorignore` **중복 제거** (Cursor 관련은 상단 블록 유지).
- 로컬 산출물로 `.benchmark/`만 명시 유지.

---

## 4. 검증

| 항목 | 결과 |
|------|------|
| 문서 간 경로 / Python 버전 / 설치·검증 명령 | 수동 교차 점검: README · `current_architecture` · `entry_points` · AGENTS 일치 |
| `python -m pytest` | **142 passed** (기본 `testpaths`; 환경에 따라 건수 소폭 차이 가능) |
| `python -m black --check .` | **미달성(既知 부채)**: 다수 파일 포맷 대상 — 감사 리포트 및 Remediation Phase 3 범위. 본 Phase는 문서·설정 중심 변경으로 전체 `black` 적용은 범위 외 |

---

## 5. 완료 기준 대조 (해결 계획서)

- 엔트리포인트·지원 Python·개발 검증 명령이 문서 간 충돌하지 않음 — **충족** (black은 저장소 전체 기준선은 별도 과제).
- historical vs current-state 구분 — **충족** (배너·허브 문서).

---

## 6. 범위 외 (후속 페이즈)

- `IJobRunner`·GUI 계약 재설계 — Remediation **Phase 2**.
- `ruff` / `mypy` / 저장소 전역 `black` — **Phase 3**.
- 스텁·벤치·골든 재정의 — **Phase 4** 등.

---

## 7. Phase 0 보고서와의 정합

- Phase 0 보고서 §6에서 `.gitignore`로 인한 `tests/` 등 신규 파일 추적 이슈를 언급했음 → **본 Phase에서 해당 ignore 블록 제거로 완화**.

---

## 8. 참고 문서

- `../2026-04-11_repo_audit_remediation_plan.md` — Phase 1 정의
- `../2026-04-11_repo_audit_report.md` — P0 문서, P1-1, P3-1
- `../../docs/current_architecture.md` — 현행 구조 정본
- `../../docs/entry_points.md` — 진입점 상세
- `../../tests/README.md` — 테스트 레이아웃 정본
