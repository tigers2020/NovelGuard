# 리팩토링 보고서: dark_theme.py

> **우선순위**: P2-2 (중간)  
> **파일**: `src/gui/styles/dark_theme.py`  
> **작성일**: 2025-01-11  
> **상태**: 분석 완료, 리팩토링 대기

---

## 1. 파일 개요 및 현황

### 1.1 기본 정보
- **LOC**: 347 lines
- **함수 수**: 1개 (`get_dark_theme_stylesheet()`)
- **최대 함수 길이**: 약 330 lines (전체의 95%)
- **의존성**: colors 모듈

### 1.2 현재 구조
```python
def get_dark_theme_stylesheet() -> str:
    """다크 테마 스타일시트 반환."""
    return f"""
    /* 메인 윈도우 */
    QMainWindow {{
        background-color: {BG_BODY};
        ...
    }}
    ...
    """  # 330 lines의 QSS 문자열
```

### 1.3 주요 문제
1. **함수 과대화**: 단일 함수에 모든 스타일 포함 (330 lines)
2. **하드코딩**: QSS 문자열이 Python 코드에 하드코딩
3. **테스트 어려움**: QSS 문자열을 독립적으로 테스트 불가
4. **유지보수성**: 스타일 수정 시 Python 코드 수정 필요

---

## 2. 문제점 분석

### 2.1 함수 과대화
**현재 문제**:
- `get_dark_theme_stylesheet()` 함수가 **330 lines**로 구성
- 모든 QSS 스타일이 단일 함수에 포함
- 스타일 섹션별로 분리 가능

**영향**:
- 가독성 저하: 330 lines 함수는 이해하기 어려움
- 유지보수성: 스타일 수정 시 함수 전체 수정 필요
- 테스트 어려움: 특정 스타일만 테스트 불가

### 2.2 하드코딩 문제
**현재 문제**:
- QSS 문자열이 Python 코드에 하드코딩
- 외부 파일로 분리 불가
- 스타일 수정 시 코드 재컴파일 필요

**영향**:
- 유연성 부족: 스타일 수정 시 코드 수정 필요
- 재사용성 부족: 다른 테마에서 스타일 재사용 어려움

---

## 3. 리팩토링 목표

### 3.1 핵심 목표
1. **상수/토큰 분리**: 색상/스타일 토큰을 별도 모듈로 추출
2. **함수 분리**: 스타일 섹션별로 함수 분리
3. **외부 파일화 (선택적)**: QSS를 `.qss` 파일로 분리

### 3.2 원칙
- **단일 책임**: 각 함수는 하나의 스타일 섹션만 담당
- **재사용성**: 스타일 토큰은 재사용 가능
- **유지보수성**: 스타일 수정 시 해당 섹션만 수정

---

## 4. 구체적인 리팩토링 계획

### 4.1 새로운 파일 구조

```
src/
├── gui/
│   └── styles/
│       ├── dark_theme.py              # 리팩토링 (150 lines 이하로 축소)
│       ├── theme_tokens.py             # 새 파일 (토큰)
│       └── qss/
│           ├── __init__.py
│           ├── main_window.qss         # 새 파일 (선택적)
│           ├── sidebar.qss             # 새 파일 (선택적)
│           └── ...                     # 기타 섹션별 QSS 파일 (선택적)
```

### 4.2 클래스 설계

#### 4.2.1 `ThemeTokens` (스타일 토큰)

```python
# gui/styles/theme_tokens.py

class ThemeTokens:
    """테마 토큰 정의."""
    
    # 색상 토큰 (기존 colors 모듈 사용)
    BG_BODY = "{BG_BODY}"
    BG_CONTAINER = "{BG_CONTAINER}"
    # ...
    
    # 스타일 토큰
    FONT_FAMILY = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Noto Sans KR', sans-serif"
    FONT_SIZE = "14px"
    
    @classmethod
    def get_base_styles(cls) -> str:
        """기본 스타일 반환."""
        return f"""
        QWidget {{
            background-color: {cls.BG_CONTAINER};
            color: {cls.TEXT_PRIMARY};
            font-family: {cls.FONT_FAMILY};
            font-size: {cls.FONT_SIZE};
        }}
        """
```

#### 4.2.2 리팩토링된 `get_dark_theme_stylesheet()`

```python
# gui/styles/dark_theme.py (리팩토링 후)

from gui.styles.theme_tokens import ThemeTokens

def get_dark_theme_stylesheet() -> str:
    """다크 테마 스타일시트 반환."""
    styles = [
        _get_main_window_styles(),
        _get_container_styles(),
        _get_header_styles(),
        _get_sidebar_styles(),
        _get_button_styles(),
        _get_input_styles(),
        _get_table_styles(),
        # ... 기타 스타일 섹션들 ...
    ]
    
    return "\n\n".join(styles)


def _get_main_window_styles() -> str:
    """메인 윈도우 스타일."""
    return f"""
    /* 메인 윈도우 */
    QMainWindow {{
        background-color: {BG_BODY};
        color: {TEXT_PRIMARY};
    }}
    """


def _get_header_styles() -> str:
    """헤더 스타일."""
    return f"""
    /* 헤더 */
    QWidget#header {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {PRIMARY_START}, stop:1 {PRIMARY_END});
        color: white;
        padding: 24px 32px;
        border-bottom: 1px solid {BORDER_PRIMARY};
    }}
    ...
    """


def _get_sidebar_styles() -> str:
    """사이드바 스타일."""
    return f"""
    /* 사이드바 */
    QWidget#sidebar {{
        background-color: {BG_SIDEBAR};
        border-right: 1px solid {BORDER_PRIMARY};
        padding: 24px;
    }}
    ...
    """


# 기타 스타일 함수들...
```

#### 4.2.3 대안: 외부 파일화 (선택적)

```python
# gui/styles/dark_theme.py (외부 파일 방식)

from pathlib import Path
from gui.styles.qss.loader import load_qss_file

def get_dark_theme_stylesheet() -> str:
    """다크 테마 스타일시트 반환."""
    qss_dir = Path(__file__).parent / "qss"
    
    qss_files = [
        "main_window.qss",
        "container.qss",
        "header.qss",
        "sidebar.qss",
        "button.qss",
        # ... 기타 QSS 파일들 ...
    ]
    
    styles = [load_qss_file(qss_dir / f) for f in qss_files]
    return "\n\n".join(styles)


# gui/styles/qss/loader.py

def load_qss_file(qss_path: Path) -> str:
    """QSS 파일 로드."""
    return qss_path.read_text(encoding="utf-8")
```

---

## 5. 단계별 작업 계획

### Phase 1: 함수 분리
- [ ] `_get_main_window_styles()` 함수 생성
- [ ] `_get_header_styles()` 함수 생성
- [ ] `_get_sidebar_styles()` 함수 생성
- [ ] 기타 스타일 함수들 생성

### Phase 2: 토큰 분리 (선택적)
- [ ] `ThemeTokens` 클래스 생성
- [ ] 스타일 토큰 추출

### Phase 3: 외부 파일화 (선택적)
- [ ] `.qss` 파일로 분리
- [ ] QSS 로더 구현

### Phase 4: 통합 테스트
- [ ] 기존 통합 테스트 실행하여 동작 확인
- [ ] 스타일 적용 확인

---

## 6. 예상 효과

### 6.1 코드 품질
- **가독성**: 함수가 작아져 가독성 향상
- **유지보수성**: 스타일 수정 시 해당 함수만 수정
- **테스트 가능성**: 각 스타일 섹션을 독립적으로 테스트 가능

### 6.2 유지보수성
- **분리**: 스타일 섹션별로 분리되어 유지보수 용이
- **재사용성**: 스타일 토큰은 재사용 가능
- **유연성**: 외부 파일화 시 런타임 스타일 변경 가능 (선택적)

---

## 7. 체크리스트

### 7.1 코드 작성
- [ ] 스타일 함수 분리
- [ ] `ThemeTokens` 클래스 작성 (선택적)
- [ ] QSS 파일 분리 (선택적)

### 7.2 테스트
- [ ] 기존 통합 테스트 통과 확인
- [ ] 스타일 적용 확인

### 7.3 문서화
- [ ] 함수 docstring 작성
- [ ] 스타일 구조 문서화

---

## 8. 참고 사항

### 8.1 권장 사항
- **함수 분리**는 필수 (가독성/유지보수성 향상)
- **토큰 분리**는 선택적 (재사용성이 중요한 경우)
- **외부 파일화**는 선택적 (런타임 스타일 변경이 필요한 경우)

### 8.2 우선순위
1. **함수 분리** (필수)
2. **토큰 분리** (선택적)
3. **외부 파일화** (선택적)

---

**작성자**: NovelGuard 개발팀  
**검토 상태**: 대기 중  
**다음 단계**: Phase 1 시작
