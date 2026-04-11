# NovelGuard 진입점 문서

현행 구조의 정본 요약은 [current_architecture.md](current_architecture.md)를 본다.

## 단일 엔트리포인트 원칙

실행은 **`src/main.py`를 통하는 것을 표준**으로 한다. `sys.path`에 `src/`를 넣는 처리는 이 파일 한 곳에서만 한다.

---

## 주 진입점: `src/main.py` (권장)

```bash
python src/main.py
```

- 프로젝트 **루트**에서 실행한다.
- 내부 동작: `src/`를 `sys.path`에 추가한 뒤 `from app.main import main` → `main()` 호출.

**실행 스크립트**: `run.bat`, `run.ps1` — 모두 위와 동일하게 `python src/main.py`를 호출한다.

---

## Composition root: `src/app/main.py`

별도의 `bootstrap.py`는 없다. [`src/app/main.py`](../src/app/main.py)의 `main()`이 다음을 수행한다.

1. `QApplication` 생성, 다크 테마 적용  
2. 프로젝트 루트 경로 계산 (`Path(__file__).parent.parent.parent`)  
3. 의존성 생성 및 주입:
   - `InMemoryLogSink(log_dir=project_root / "logs")`
   - `SQLiteIndexRepository(log_sink=...)`
   - `FileSystemScanner(log_sink=...)`
   - `AppState` — `set_log_sink` 후 `file_data_store` 확보
   - `QtJobManager(scanner, index_repository=index_repo, log_sink=..., file_data_store=app_state.file_data_store)`
4. `MainWindow(index_repo=..., log_sink=..., job_manager=..., app_state=app_state)` 생성 후 표시  
5. `app.exec()` 반환

```
src/main.py          ← sys.path 설정 후 app.main 호출
       ↓
src/app/main.py      ← composition root (위 객체들 생성)
       ↓
MainWindow + Qt 이벤트 루프
```

---

## 보조 실행: 모듈 방식 (개발용)

`src/`가 패키지 탐색 경로에 있어야 하므로, 루트에서 그대로 두고:

```bash
cd src
python -m app.main
```

또는 루트에서 `PYTHONPATH=src` 환경을 두고 `python -m app.main`을 쓸 수 있다(플랫폼에 따라 설정 방식이 다름).

**권장하지 않는 것**

- `src/app/`로 들어가 `python main.py`로 직접 실행 — 패키지 상대 import가 깨질 수 있다.

---

## 테스트 실행

기본 스위트는 `pyproject.toml`의 `testpaths`를 따른다. 루트에서:

```bash
python -m pytest
```

정책·아카이브 경계는 [tests/README.md](../tests/README.md)를 본다. 레거시 골든/퍼포먼스 러너는 기본 수집에서 제외될 수 있다.

---

## 하지 말 것 / 해야 할 것

**하지 말 것**

1. `src/main.py` 없이 임의 모듈만 실행해 앱을 띄우기  
2. `src/main.py` 밖에서 `sys.path`를 조작해 import 우회하기  
3. `python src/gui/views/main_window.py` 같이 뷰 파일만 단독 실행  

**해야 할 것**

1. 앱 실행은 `python src/main.py`(또는 동등한 스크립트)  
2. 테스트는 `python -m pytest`  
3. 진입점이 늘면 이 문서와 [current_architecture.md](current_architecture.md)를 갱신  

---

## 문제 해결

**`ModuleNotFoundError: No module named 'app'`**  
→ 루트에서 `python src/main.py`를 사용하거나, `cd src` 후 `python -m app.main`으로 `src`가 경로에 포함되게 한다.

**GUI가 시작되지 않음**  
→ 런타임 의존성 설치: `pip install -r requirements.txt` (또는 `pip install -e .`). Python 버전은 `>=3.12` ([`pyproject.toml`](../pyproject.toml)).

**테스트 수집 오류**  
→ [tests/README.md](../tests/README.md)의 기본 경로·`_archive` 정책 확인.

---

마지막 갱신: 2026-04-11 (문서 정본화 Phase 1)
