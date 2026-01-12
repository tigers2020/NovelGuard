# 리팩토링 보고서: Tabs 중복 코드

> **우선순위**: P1-1 (높음)  
> **파일**: `src/gui/views/tabs/duplicate_tab.py`, `scan_tab.py`, `encoding_tab.py`, `integrity_tab.py`, `small_file_tab.py`  
> **작성일**: 2025-01-11  
> **상태**: 분석 완료, 리팩토링 대기

---

## 1. 문제 개요

### 1.1 중복 코드 패턴
다음 탭들 사이에 **동일/유사 블록 코드가 여러 군데 반복**됩니다:

- `duplicate_tab.py`
- `scan_tab.py`
- `encoding_tab.py`
- `integrity_tab.py`
- `small_file_tab.py`

### 1.2 주요 중복 패턴

#### 1.2.1 액션 바 생성 패턴
```python
def _create_action_bar(self) -> QHBoxLayout:
    """액션 바 생성."""
    layout = QHBoxLayout()
    layout.setSpacing(16)
    
    # 시작 버튼
    start_btn = QPushButton("시작")
    start_btn.setObjectName("btnPrimary")
    start_btn.clicked.connect(self._on_start)
    layout.addWidget(start_btn)
    
    # Dry Run 버튼 (선택적)
    # 적용 버튼 (선택적)
    
    layout.addStretch()
    return layout
```

#### 1.2.2 프로그레스 섹션 생성 패턴
```python
def _create_progress_section(self) -> QGroupBox:
    """프로그레스 섹션 생성."""
    group = QGroupBox("진행 상태")
    layout = QVBoxLayout(group)
    
    # 프로그레스 바
    self._progress_bar = QProgressBar()
    self._progress_bar.setMinimum(0)
    self._progress_bar.setMaximum(0)  # 무한 모드
    layout.addWidget(self._progress_bar)
    
    # 상태 레이블
    self._status_label = QLabel("대기 중...")
    layout.addWidget(self._status_label)
    
    # 초기 상태: 숨김
    group.setVisible(False)
    
    return group
```

#### 1.2.3 ViewModel 시그널 연결 패턴
```python
def _connect_view_model_signals(self) -> None:
    """ViewModel 시그널 연결."""
    self._view_model.progress_updated.connect(self._on_progress_updated)
    self._view_model.completed.connect(self._on_completed)
    self._view_model.error.connect(self._on_error)
```

#### 1.2.4 AppState 가져오기 패턴
```python
def _get_app_state(self) -> AppState:
    """AppState 가져오기."""
    parent = self.parent()
    while parent:
        if hasattr(parent, '_app_state'):
            return parent._app_state
        parent = parent.parent()
    return AppState()
```

---

## 2. 리팩토링 목표

### 2.1 핵심 목표
1. **공통 UI 패턴 추출**: BaseTab에 공통 컴포넌트 메서드 추가
2. **TabScaffold 컴포넌트**: 재사용 가능한 UI 컴포넌트 생성
3. **탭별 차이점만 남기기**: ViewModel + Config(문구/옵션/컬럼)만 남김

### 2.2 원칙
- **DRY**: 중복 코드 제거
- **단일 책임**: 각 탭은 비즈니스 로직만 담당
- **재사용성**: 공통 컴포넌트는 재사용 가능

---

## 3. 구체적인 리팩토링 계획

### 3.1 새로운 파일 구조

```
src/
├── gui/
│   ├── views/
│   │   ├── tabs/
│   │   │   ├── base_tab.py              # 리팩토링 (공통 메서드 추가)
│   │   │   ├── tab_scaffold.py           # 새 파일
│   │   │   ├── scan_tab.py               # 리팩토링 (간소화)
│   │   │   ├── duplicate_tab.py          # 리팩토링 (간소화)
│   │   │   └── ...
│   │   │
│   │   └── components/
│   │       └── tab_components.py         # 새 파일 (선택적)
```

### 3.2 클래스 설계

#### 3.2.1 `TabScaffold` 컴포넌트

```python
# gui/views/tabs/tab_scaffold.py

from typing import Optional, Callable
from PySide6.QtWidgets import QGroupBox, QHBoxLayout, QLabel, QProgressBar, QPushButton, QVBoxLayout

class TabScaffold:
    """탭 공통 UI 컴포넌트."""
    
    @staticmethod
    def create_action_bar(
        buttons: list[tuple[str, str, Callable, Optional[str]]]  # (text, object_name, callback, tooltip)
    ) -> QHBoxLayout:
        """액션 바 생성.
        
        Args:
            buttons: 버튼 정의 리스트 (텍스트, 오브젝트명, 콜백, 툴팁).
        
        Returns:
            QHBoxLayout.
        """
        layout = QHBoxLayout()
        layout.setSpacing(16)
        
        for text, object_name, callback, tooltip in buttons:
            btn = QPushButton(text)
            btn.setObjectName(object_name)
            btn.clicked.connect(callback)
            if tooltip:
                btn.setToolTip(tooltip)
            layout.addWidget(btn)
        
        layout.addStretch()
        return layout
    
    @staticmethod
    def create_progress_section() -> tuple[QGroupBox, QProgressBar, QLabel]:
        """프로그레스 섹션 생성.
        
        Returns:
            (그룹 박스, 프로그레스 바, 상태 레이블) 튜플.
        """
        group = QGroupBox("진행 상태")
        layout = QVBoxLayout(group)
        
        progress_bar = QProgressBar()
        progress_bar.setMinimum(0)
        progress_bar.setMaximum(0)  # 무한 모드
        layout.addWidget(progress_bar)
        
        status_label = QLabel("대기 중...")
        layout.addWidget(status_label)
        
        # 초기 상태: 숨김
        group.setVisible(False)
        
        return group, progress_bar, status_label
```

#### 3.2.2 `BaseTab` 확장

```python
# gui/views/tabs/base_tab.py (리팩토링 후)

from gui.views.tabs.tab_scaffold import TabScaffold

class BaseTab(QWidget):
    """탭 기본 클래스."""
    
    # ... 기존 코드 ...
    
    def _create_action_bar(
        self,
        buttons: list[tuple[str, str, Callable, Optional[str]]]
    ) -> QHBoxLayout:
        """액션 바 생성 (공통 메서드)."""
        return TabScaffold.create_action_bar(buttons)
    
    def _create_progress_section(
        self
    ) -> tuple[QGroupBox, QProgressBar, QLabel]:
        """프로그레스 섹션 생성 (공통 메서드)."""
        return TabScaffold.create_progress_section()
    
    def _get_app_state(self) -> AppState:
        """AppState 가져오기 (공통 메서드)."""
        # ... 기존 로직 ...
```

#### 3.2.3 리팩토링된 `ScanTab`

```python
# gui/views/tabs/scan_tab.py (리팩토링 후)

class ScanTab(BaseTab):
    """파일 스캔 탭."""
    
    def _setup_content(self, layout: QVBoxLayout) -> None:
        """컨텐츠 설정."""
        # 액션 바 (공통 컴포넌트 사용)
        action_bar = self._create_action_bar([
            ("스캔 시작", "btnPrimary", self._on_start_scan, None),
            ("Dry Run", "btnSecondary", self._on_dry_run, None),
        ])
        layout.addLayout(action_bar)
        
        # 프로그레스 섹션 (공통 컴포넌트 사용)
        self._progress_section, self._progress_bar, self._status_label = self._create_progress_section()
        layout.addWidget(self._progress_section)
        
        # 탭별 고유 UI
        folder_group = self._create_folder_group()
        layout.addWidget(folder_group)
    
    def _get_app_state(self) -> AppState:
        """AppState 가져오기 (BaseTab 메서드 사용)."""
        return super()._get_app_state()
```

#### 3.2.4 리팩토링된 `DuplicateTab`

```python
# gui/views/tabs/duplicate_tab.py (리팩토링 후)

class DuplicateTab(BaseTab):
    """중복 파일 정리 탭."""
    
    def _setup_content(self, layout: QVBoxLayout) -> None:
        """컨텐츠 설정."""
        # 액션 바 (공통 컴포넌트 사용)
        action_bar = self._create_action_bar([
            ("중복 탐지 시작", "btnPrimary", self._on_start_detection, None),
            ("Dry Run", "btnSecondary", self._on_dry_run, None),
            ("적용하기", "btnSuccess", self._on_apply, None),
        ])
        layout.addLayout(action_bar)
        
        # 프로그레스 섹션 (공통 컴포넌트 사용)
        self._progress_section, self._progress_bar, self._status_label = self._create_progress_section()
        layout.addWidget(self._progress_section)
        
        # 탭별 고유 UI (결과 테이블 등)
        # ...
```

---

## 4. 단계별 작업 계획

### Phase 1: TabScaffold 컴포넌트 생성
- [ ] `TabScaffold` 클래스 생성
- [ ] `create_action_bar()` 메서드 구현
- [ ] `create_progress_section()` 메서드 구현
- [ ] 단위 테스트 작성

### Phase 2: BaseTab 확장
- [ ] `_create_action_bar()` 공통 메서드 추가
- [ ] `_create_progress_section()` 공통 메서드 추가
- [ ] `_get_app_state()` 공통 메서드 추가

### Phase 3: 각 탭 리팩토링 (순차적)
- [ ] `ScanTab` 리팩토링
- [ ] `DuplicateTab` 리팩토링
- [ ] `EncodingTab` 리팩토링
- [ ] `IntegrityTab` 리팩토링
- [ ] `SmallFileTab` 리팩토링

### Phase 4: 통합 테스트
- [ ] 기존 통합 테스트 실행하여 동작 확인
- [ ] UI 테스트 (각 탭 동작 확인)

---

## 5. 예상 효과

### 5.1 코드 품질
- **중복 제거**: 동일 패턴 코드 제거 (약 50% 감소 예상)
- **가독성**: 탭별 차이점만 남아 가독성 향상
- **유지보수성**: 공통 컴포넌트 수정 시 모든 탭에 반영

### 5.2 개발 효율성
- **새 탭 추가**: 공통 컴포넌트 재사용으로 개발 시간 단축
- **일관성**: 모든 탭이 동일한 UI 패턴 사용

---

## 6. 체크리스트

### 6.1 코드 작성
- [ ] `TabScaffold` 클래스 작성
- [ ] `BaseTab` 확장
- [ ] 각 탭 리팩토링 (5개)

### 6.2 테스트
- [ ] TabScaffold 단위 테스트
- [ ] 기존 통합 테스트 통과 확인
- [ ] UI 테스트

### 6.3 문서화
- [ ] 클래스 docstring 작성
- [ ] 사용 예제 작성

---

**작성자**: NovelGuard 개발팀  
**검토 상태**: 대기 중  
**다음 단계**: Phase 1 시작
