# 리팩토링 보고서: 순환 의존 제거 (main_window, scan_tab, base_tab)

> **우선순위**: P0-6 (최우선)  
> **파일**: `src/gui/views/main_window.py`, `src/gui/views/tabs/scan_tab.py`, `src/gui/views/tabs/base_tab.py`  
> **작성일**: 2025-01-11  
> **상태**: 분석 완료, 리팩토링 대기

---

## 1. 문제 개요

### 1.1 순환 의존 구조
```
main_window.py
  └─> scan_tab.py (import)
       └─> base_tab.py (import)
            └─> main_window.py (순환!)
```

### 1.2 현재 구조
- **main_window.py**: `from gui.views.tabs.scan_tab import ScanTab` (line 141)
- **scan_tab.py**: `from gui.views.tabs.base_tab import BaseTab` (line 25)
- **base_tab.py**: `_get_main_window()` 메서드에서 `MainWindow` 타입 체크 (line 71-82)

### 1.3 문제점
- **순환 의존**: main_window → scan_tab → base_tab → main_window
- **타입 안전성 부족**: `_get_main_window()`가 문자열 기반 타입 체크 사용 (`__class__.__name__ == "MainWindow"`)
- **확장성 문제**: 새로운 탭 추가 시 import 지뢰 발생 가능
- **테스트 어려움**: 순환 의존으로 인한 테스트 복잡도 증가

---

## 2. 리팩토링 목표

### 2.1 핵심 목표
1. **순환 의존 제거**: base_tab이 main_window를 직접 참조하지 않도록
2. **의존성 역전**: base_tab이 필요한 기능을 인터페이스/콜백으로 받도록
3. **타입 안전성**: 문자열 기반 타입 체크 제거
4. **확장성**: 새로운 탭 추가 시 의존성 문제 없도록

### 2.2 원칙
- **의존성 역전**: 구체 클래스 대신 인터페이스/콜백 사용
- **단방향 의존**: main_window → tabs 방향으로만 의존성 흐름
- **타입 안전성**: 타입 힌팅 및 Protocol 사용

---

## 3. 구체적인 리팩토링 계획

### 3.1 접근 방법: 의존성 역전 (Dependency Inversion)

#### 3.1.1 `IMainWindowProvider` Protocol 정의

```python
# gui/views/tabs/main_window_provider.py (새 파일)

from typing import Protocol, Optional
from PySide6.QtWidgets import QWidget

class IMainWindowProvider(Protocol):
    """MainWindow 기능 제공 인터페이스."""
    
    def get_file_data_store(self) -> Optional["FileDataStore"]:
        """FileDataStore 반환."""
        ...
    
    def get_app_state(self) -> Optional["AppState"]:
        """AppState 반환."""
        ...
    
    def show_tab(self, tab_name: str) -> None:
        """특정 탭 표시."""
        ...
```

#### 3.1.2 `BaseTab` 수정

```python
# gui/views/tabs/base_tab.py (리팩토링 후)

from typing import Optional, TYPE_CHECKING
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from gui.views.tabs.main_window_provider import IMainWindowProvider

if TYPE_CHECKING:
    from gui.models.file_data_store import FileDataStore
    from gui.models.app_state import AppState

class BaseTab(QWidget):
    """탭 기본 클래스."""
    
    def __init__(
        self,
        parent: Optional[QWidget] = None,
        main_window_provider: Optional[IMainWindowProvider] = None
    ) -> None:
        """탭 초기화.
        
        Args:
            parent: 부모 위젯.
            main_window_provider: MainWindow 기능 제공자 (선택적).
        """
        super().__init__(parent)
        self._main_window_provider = main_window_provider
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)
        
        layout.addWidget(self._create_page_title())
        self._setup_content(layout)
    
    def _get_main_window_provider(self) -> Optional[IMainWindowProvider]:
        """MainWindow 기능 제공자 반환.
        
        Returns:
            IMainWindowProvider 인스턴스 또는 None.
        """
        if self._main_window_provider:
            return self._main_window_provider
        
        # 부모 위젯을 통해 찾기 (타입 체크 없이 Protocol 체크)
        parent = self.parent()
        while parent:
            if hasattr(parent, 'get_file_data_store') and hasattr(parent, 'get_app_state'):
                return parent  # type: ignore
            parent = parent.parent()
        return None
    
    def _get_file_data_store(self) -> Optional["FileDataStore"]:
        """FileDataStore 반환."""
        provider = self._get_main_window_provider()
        if provider:
            return provider.get_file_data_store()
        return None
    
    def _get_app_state(self) -> Optional["AppState"]:
        """AppState 반환."""
        provider = self._get_main_window_provider()
        if provider:
            return provider.get_app_state()
        return None
```

#### 3.1.3 `MainWindow` 수정

```python
# gui/views/main_window.py (리팩토링 후)

# ... 기존 imports ...

class MainWindow(QMainWindow, IMainWindowProvider):
    """메인 윈도우."""
    
    # ... 기존 코드 ...
    
    def get_file_data_store(self) -> Optional["FileDataStore"]:
        """FileDataStore 반환 (IMainWindowProvider 구현)."""
        return self._file_data_store
    
    def get_app_state(self) -> Optional["AppState"]:
        """AppState 반환 (IMainWindowProvider 구현)."""
        return self._app_state
    
    def show_tab(self, tab_name: str) -> None:
        """특정 탭 표시 (IMainWindowProvider 구현)."""
        self._switch_tab(tab_name)
    
    def _setup_tabs(self) -> None:
        """탭 뷰 설정."""
        from gui.views.tabs.scan_tab import ScanTab
        # ... 기타 imports ...
        
        # ScanTab과 LogsTab에 deps 전달 (main_window_provider 전달)
        tabs = {
            "scan": ScanTab(self, main_window_provider=self, job_manager=self._job_manager, log_sink=self._log_sink),
            # ... 기타 탭들 ...
        }
        
        # ... 기존 코드 ...
```

#### 3.1.4 `ScanTab` 수정

```python
# gui/views/tabs/scan_tab.py (리팩토링 후)

from gui.views.tabs.base_tab import BaseTab
from gui.views.tabs.main_window_provider import IMainWindowProvider

class ScanTab(BaseTab):
    """파일 스캔 탭."""
    
    def __init__(
        self,
        parent: Optional[QWidget] = None,
        main_window_provider: Optional[IMainWindowProvider] = None,
        job_manager=None,
        log_sink: Optional[ILogSink] = None
    ) -> None:
        """스캔 탭 초기화."""
        super().__init__(parent, main_window_provider=main_window_provider)
        
        # ... 기존 코드 ...
        
        # AppState 가져오기 (base_tab의 메서드 사용)
        self._app_state = self._get_app_state()
        
        # ... 기존 코드 ...
```

---

## 4. 단계별 작업 계획

### Phase 1: Protocol 정의
- [ ] `IMainWindowProvider` Protocol 생성
- [ ] 필요한 메서드 정의 (get_file_data_store, get_app_state, show_tab)

### Phase 2: BaseTab 리팩토링
- [ ] `_get_main_window()` 제거
- [ ] `_get_main_window_provider()` 추가
- [ ] `_get_file_data_store()`, `_get_app_state()` 메서드 수정

### Phase 3: MainWindow 리팩토링
- [ ] `IMainWindowProvider` 구현
- [ ] 탭 생성 시 `main_window_provider=self` 전달

### Phase 4: 탭들 리팩토링
- [ ] 각 탭에서 `main_window_provider` 파라미터 추가
- [ ] `_get_app_state()` 사용하도록 수정

### Phase 5: 통합 테스트
- [ ] 기존 통합 테스트 실행하여 동작 확인
- [ ] 순환 의존 제거 확인

---

## 5. 예상 효과

### 5.1 코드 품질
- **순환 의존 제거**: 의존성 방향이 단방향으로 정리
- **타입 안전성**: Protocol 사용으로 타입 안전성 향상
- **확장성**: 새로운 탭 추가 시 의존성 문제 없음

### 5.2 유지보수성
- **명확한 의존성**: 의존성 방향이 명확히 정의됨
- **테스트 용이성**: 순환 의존 제거로 테스트 용이
- **유연성**: Mock 객체로 테스트 가능

---

## 6. 체크리스트

### 6.1 코드 작성
- [ ] `IMainWindowProvider` Protocol 작성
- [ ] `BaseTab` 리팩토링
- [ ] `MainWindow` 리팩토링
- [ ] 각 탭 리팩토링

### 6.2 테스트
- [ ] 기존 통합 테스트 통과 확인
- [ ] 순환 의존 제거 확인

### 6.3 문서화
- [ ] Protocol docstring 작성
- [ ] 의존성 다이어그램 업데이트

---

## 7. 대안 방법 (선택적)

### 7.1 탭 팩토리/레지스트리 패턴
더 큰 리팩토링을 원하는 경우:

```python
# gui/views/tabs/tab_registry.py

class TabRegistry:
    """탭 레지스트리."""
    
    def __init__(self):
        self._tabs: dict[str, type] = {}
    
    def register(self, name: str, tab_class: type) -> None:
        """탭 등록."""
        self._tabs[name] = tab_class
    
    def create(self, name: str, **kwargs) -> QWidget:
        """탭 생성."""
        tab_class = self._tabs.get(name)
        if not tab_class:
            raise ValueError(f"Tab not found: {name}")
        return tab_class(**kwargs)
```

이 방법은 더 큰 리팩토링이 필요하므로 현재는 Protocol 기반 접근을 권장합니다.

---

**작성자**: NovelGuard 개발팀  
**검토 상태**: 대기 중  
**다음 단계**: Phase 1 시작
