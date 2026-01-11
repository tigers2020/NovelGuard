# NovelGuard 진입점 문서

## 단일 엔트리포인트 원칙

NovelGuard는 **단일 엔트리포인트 원칙**을 준수합니다. 모든 실행은 정의된 진입점을 통해야 합니다.

---

## 진입점

### 주 진입점: `src/main.py` (권장)

**사용법**:
```bash
python src/main.py
```

**설명**:
- NovelGuard 애플리케이션의 **유일한 공식 진입점**입니다.
- `app.main`을 통해 Bootstrap을 호출하여 의존성을 주입합니다.
- sys.path 설정은 이 파일에서만 수행됩니다.

**실행 스크립트**:
- `run.bat` (Windows CMD)
- `run.ps1` (Windows PowerShell)

모두 `python src/main.py`를 실행합니다.

---

### 보조 진입점: `src/app/main.py` (직접 실행 비권장)

**사용법** (권장하지 않음):
```bash
# src 폴더로 이동
cd src
python -m app.main
```

**설명**:
- Bootstrap을 통해 애플리케이션을 초기화합니다.
- **직접 실행하지 마세요** - `src/main.py`를 통해 실행해야 합니다.
- 직접 실행 시 경고 메시지를 표시합니다.

---

## Bootstrap 구조

```
src/main.py (단일 진입점)
  ↓
src/app/main.py (애플리케이션 메인)
  ↓
src/app/bootstrap.py (의존성 주입)
  ↓
MainWindow (GUI)
```

**의존성 흐름**:
1. `src/main.py`: sys.path 설정 (단일 진입점에서만)
2. `src/app/main.py`: Bootstrap 호출
3. `src/app/bootstrap.py`: 의존성 생성 및 주입
   - FileRepository 생성
   - ScanFilesUseCase 생성 (repository 주입)
   - Logger 초기화
   - MainWindow 생성 (scan_usecase, repository, logger 주입)

---

## 개발자 실행 방법

### 일반 실행
```bash
# 프로젝트 루트에서
python src/main.py

# 또는 실행 스크립트 사용
run.bat      # CMD
run.ps1      # PowerShell
```

### 모듈로 실행 (개발 중)
```bash
# 프로젝트 루트에서
cd src
python -m app.main
```

### 테스트 실행
```bash
# 전체 테스트
python -m pytest tests/

# 특정 테스트
python -m pytest tests/app/ -v
python -m pytest tests/integration/test_golden_scenarios.py -v
```

---

## 주의사항

### ❌ 하지 말아야 할 것

1. **`src/app/main.py`를 직접 실행하지 마세요**
   ```bash
   # 잘못된 방법
   cd src/app
   python main.py  # ❌ import 오류 발생
   ```

2. **다른 파일에서 sys.path를 수정하지 마세요**
   - sys.path 설정은 `src/main.py`에서만 허용됩니다.
   - 다른 파일에서 sys.path를 수정하면 의존성 관리가 복잡해집니다.

3. **GUI 컴포넌트를 직접 실행하지 마세요**
   ```bash
   # 잘못된 방법
   python src/gui/views/main_window.py  # ❌
   ```

### ✅ 해야 할 것

1. **항상 `src/main.py`를 통해 실행하세요**
2. **테스트는 pytest를 통해 실행하세요**
3. **새로운 진입점이 필요한 경우 문서화하세요**

---

## Phase 1.1.4 완료 내역

### 변경사항
- `src/main.py`: 단일 진입점으로 설정, `app.main`을 호출하도록 수정
- `src/app/main.py`: sys.path hack 제거, Bootstrap 호출만 수행
- 직접 실행 경고 추가: `src/app/main.py`를 직접 실행하면 경고 표시

### 목적
- 단일 엔트리포인트 원칙 적용
- import 경로 혼란 방지
- 의존성 관리 단순화

---

## 문제 해결

### Q: "ModuleNotFoundError: No module named 'app'" 오류
**A**: `src/main.py`를 통해 실행하세요. 직접 다른 파일을 실행하면 안 됩니다.

### Q: GUI가 시작되지 않아요
**A**: 
1. 의존성 설치 확인: `pip install -r requirements.txt`
2. Python 버전 확인: Python 3.10 이상
3. `src/main.py`를 통해 실행하는지 확인

### Q: 테스트가 실패해요
**A**: 
1. 프로젝트 루트에서 실행하세요: `python -m pytest tests/`
2. sys.path 설정이 올바른지 확인하세요 (테스트 파일 참조)

---

마지막 업데이트: 2026-01-09 (Phase 1.1.4)
