# NovelGuard 현행 구조 (정본)

이 문서는 **현재 코드와 설정**을 기준으로 한 단일 정본이다. 리팩터링 계획서·완료 보고·성능 메모 등 역사 자료는 [`docs/archive/`](archive/README.md)에 모여 있으며 과거 기록일 수 있으므로, 동작·경로·의존성은 여기와 [`pyproject.toml`](../pyproject.toml)를 우선한다.

## 지원 환경

- **Python**: `pyproject.toml`의 `requires-python`과 동일 (현재 `>=3.12`).
- **의존성(런타임)**: `pyproject.toml` `[project].dependencies`와 [`requirements.txt`](../requirements.txt)가 같은 하한을 쓴다.
- **개발·검증 도구**: `pip install -e ".[dev]"` — `pytest`, `ruff`, `mypy`, `black`, (선택) `psutil`.

## 실행 진입점

1. **권장**: 저장소 루트에서 `python src/main.py`.
2. [`src/main.py`](../src/main.py)가 `src/`를 `sys.path`에 넣은 뒤 `app.main.main()`을 호출한다.
3. [`src/app/main.py`](../src/app/main.py)가 **composition root**다. 별도의 `bootstrap.py` 모듈은 없다.

### Composition root에서 생성되는 객체 (요약)

- `InMemoryLogSink` — 로그 디렉터리: 프로젝트 루트의 `logs/`
- `SQLiteIndexRepository` — 인덱스 저장소
- `FileSystemScanner` — 파일 시스템 스캔
- `AppState` — 전역 UI 상태; `set_log_sink` 후 `file_data_store`를 한 번 확보해 아래와 공유
- `QtJobManager` — 스캐너·인덱스·로그·**`AppState.file_data_store`**를 주입받아 스캔·중복 탐지 워커를 띄움
- `MainWindow` — `index_repo`, `log_sink`, `job_manager`와 **동일 `AppState` 인스턴스** 주입

**Job 포트 (`application.ports.job_runner.IJobRunner`)**: GUI는 구체 클래스가 아니라 이 계약에만 의존한다. 메서드는 `start_scan`, `start_duplicate_detection`, `cancel`, `get_status`, `subscribe(JobEvent)`이며, 진행·완료·실패는 `subscribe`로 수신한다 (구현체는 `gui.services.qt_job_manager.QtJobManager`).

자세한 실행 방법·금지 사항은 [entry_points.md](entry_points.md)를 본다.

## 소스 레이아웃 (`src/`)

| 경로 | 역할 |
|------|------|
| `src/domain/` | 도메인 모델·서비스·규칙 |
| `src/application/` | 유스케이스, DTO, 애플리케이션 포트 |
| `src/infrastructure/` | DB, FS, 로깅 등 어댑터 구현 |
| `src/gui/` | PySide6 UI, 뷰모델, 서비스 |
| `src/app/` | 설정 상수, 팩토리 등 앱 조립 보조 (`main.py`가 진입 조립 담당) |

## 테스트 기본 스위트

- **정본**: [`pyproject.toml`](../pyproject.toml)의 `[tool.pytest.ini_options] testpaths` 및 [`tests/README.md`](../tests/README.md).
- 기본 `pytest`는 현행 레이아웃 테스트만 수집하고, 레거시는 `tests/_archive/` 등으로 분리된다.
- **재현성**: `testpaths`에 나열된 디렉터리(예: `tests/unit/`)는 Git에 추적된 파일이어야 한다. 클론만 한 트리에서의 `pytest` 건수가 문서 기술과 맞는지가 “저장소 기준 완료”의 판단에 쓰인다.

## 검증 명령 (로컬)

[`AGENTS.md`](../AGENTS.md)와 동일. 한 번에 돌리려면 프로젝트 루트에서:

- `python scripts/verify_phase_completion.py` — `pytest` → `ruff check .` → `mypy src` → `black --check .` (fail-fast)

단계별로 실행할 때:

- `pytest`
- `ruff check .`
- `mypy src`
- `black --check .` (CI와 동일; 로컬에서 포맷 적용만 할 때는 `black .`)

Ruff/Black 제외: `tests/_archive/` 및 레거시 `tests/common`, `tests/domain`, `tests/infra` 일부 등은 [`pyproject.toml`](../pyproject.toml)의 `tool.ruff.exclude` / `tool.black.extend-exclude`를 본다.

## 관련 링크

- [AGENTS.md](../AGENTS.md) — Cursor·운영 게이트, 규칙 우선순위
- [entry_points.md](entry_points.md) — 진입점 상세
- [tests/README.md](../tests/README.md) — 테스트 디렉터리 정책
