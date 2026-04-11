# 리팩토링 보고서: _stubs ViewModels

> **우선순위**: P2-1 (중간)  
> **파일**: `src/gui/view_models/_stubs/*.py`  
> **작성일**: 2025-01-11  
> **상태**: 분석 완료, 리팩토링 대기

---

## 1. 파일 개요 및 현황

### 1.1 기본 정보
- **파일 수**: 6개 ViewModel 스텁
  - `encoding_view_model.py`
  - `integrity_view_model.py`
  - `logs_view_model.py`
  - `settings_view_model.py`
  - `small_file_view_model.py`
  - `undo_view_model.py`
- **공통 특징**: TODO 주석, pass 구현

### 1.2 현재 구조
```python
# 각 스텁 파일의 공통 구조
class XXXViewModel(BaseViewModel):
    """XXX ViewModel (스텁)."""
    
    def __init__(self, ...):
        # TODO: 구현 예정
        pass
    
    def some_method(self):
        # TODO: 구현 예정
        pass
```

### 1.3 주요 문제
1. **TODO/pass 스텁**: 제품 코드에 미완성 코드 존재
2. **구조 오염**: 스텁 코드가 구조를 계속 오염시킴
3. **명확한 계약 부재**: 인터페이스/계약이 명확하지 않음

---

## 2. 문제점 분석

### 2.1 스텁 코드의 문제
**현재 문제**:
- 스텁 코드가 제품 코드에 남아있음
- TODO 주석만 있고 실제 구현이 없음
- 명확한 인터페이스/계약이 없음

**영향**:
- 구조 오염: 미완성 코드가 구조를 계속 오염시킴
- 혼란: 개발자가 스텁 코드를 실제 구현으로 착각할 수 있음
- 유지보수 비용: 스텁 코드를 계속 관리해야 함

### 2.2 두 가지 접근 방법

#### 방법 1: 명확한 인터페이스로 정식화
- 스텁을 명확한 인터페이스/Protocol로 정의
- NotImplementedError로 명확히 표시
- 향후 구현 시 인터페이스 계약 준수

#### 방법 2: Feature Flag + 제거
- Feature flag로 기능 활성화/비활성화
- 스텁 코드 제거
- 필요 시 나중에 추가

---

## 3. 리팩토링 목표

### 3.1 핵심 목표
1. **명확한 인터페이스 정의**: Protocol 또는 추상 클래스로 인터페이스 정의
2. **스텁 제거 또는 정식화**: 스텁 코드를 명확한 인터페이스로 정식화
3. **구조 정리**: 미완성 코드가 구조를 오염시키지 않도록

### 3.2 원칙
- **명확성**: 인터페이스/계약이 명확해야 함
- **일관성**: 모든 ViewModel이 동일한 패턴 사용
- **유지보수성**: 스텁 코드를 계속 관리하지 않도록

---

## 4. 구체적인 리팩토링 계획

### 4.1 접근 방법: 명확한 인터페이스로 정식화

#### 4.1.1 ViewModel Protocol 정의

```python
# gui/view_models/base_view_model.py (확장)

from typing import Protocol

class IViewModel(Protocol):
    """ViewModel 인터페이스."""
    
    def initialize(self) -> None:
        """초기화."""
        ...
    
    def cleanup(self) -> None:
        """정리."""
        ...


class BaseViewModel(QObject):
    """ViewModel 기본 클래스."""
    
    def initialize(self) -> None:
        """초기화 (서브클래스에서 구현)."""
        raise NotImplementedError("Subclass must implement initialize")
    
    def cleanup(self) -> None:
        """정리 (서브클래스에서 구현)."""
        raise NotImplementedError("Subclass must implement cleanup")
```

#### 4.1.2 리팩토링된 스텁 ViewModel

```python
# gui/view_models/encoding_view_model.py (리팩토링 후)

class EncodingViewModel(BaseViewModel):
    """인코딩 ViewModel.
    
    현재 미구현 상태. 향후 구현 예정.
    """
    
    def __init__(self, parent: Optional[QObject] = None) -> None:
        """EncodingViewModel 초기화."""
        super().__init__(parent)
        # 초기화 로직은 initialize()에서 수행
    
    def initialize(self) -> None:
        """초기화."""
        raise NotImplementedError(
            "EncodingViewModel is not yet implemented. "
            "This feature is planned for a future release."
        )
    
    def cleanup(self) -> None:
        """정리."""
        raise NotImplementedError(
            "EncodingViewModel is not yet implemented."
        )
    
    # 기타 메서드들도 NotImplementedError로 명확히 표시
```

#### 4.1.3 대안: Feature Flag 방식

```python
# gui/view_models/encoding_view_model.py (Feature Flag 방식)

from app.settings.feature_flags import FeatureFlags

class EncodingViewModel(BaseViewModel):
    """인코딩 ViewModel."""
    
    def __init__(self, parent: Optional[QObject] = None) -> None:
        """EncodingViewModel 초기화."""
        super().__init__(parent)
        
        if not FeatureFlags.ENCODING_FEATURE_ENABLED:
            raise RuntimeError(
                "EncodingViewModel is not available. "
                "This feature is disabled."
            )
        
        # 실제 구현
        self._initialize()
    
    def _initialize(self) -> None:
        """초기화."""
        # 실제 구현 (향후 추가)
        pass
```

---

## 5. 단계별 작업 계획

### Phase 1: 인터페이스 정의
- [ ] `IViewModel` Protocol 정의
- [ ] `BaseViewModel`에 기본 메서드 추가
- [ ] 인터페이스 문서화

### Phase 2: 스텁 정식화 또는 제거
- [ ] 각 스텁 ViewModel 검토
- [ ] 명확한 인터페이스로 정식화 또는 제거 결정
- [ ] NotImplementedError로 명확히 표시

### Phase 3: 통합 테스트
- [ ] 기존 통합 테스트 실행하여 동작 확인
- [ ] NotImplementedError 처리 확인

### Phase 4: 문서화
- [ ] 각 ViewModel의 상태 문서화 (구현/미구현)
- [ ] 향후 구현 계획 문서화

---

## 6. 예상 효과

### 6.1 코드 품질
- **명확성**: 스텁 코드가 명확히 표시됨
- **구조 정리**: 미완성 코드가 구조를 오염시키지 않음
- **일관성**: 모든 ViewModel이 동일한 패턴 사용

### 6.2 유지보수성
- **명확한 계약**: 인터페이스/계약이 명확히 정의됨
- **향후 구현 용이**: 인터페이스를 따르면 쉽게 구현 가능

---

## 7. 체크리스트

### 7.1 코드 작성
- [ ] `IViewModel` Protocol 정의
- [ ] 각 스텁 ViewModel 정식화 또는 제거

### 7.2 테스트
- [ ] NotImplementedError 처리 확인
- [ ] 기존 통합 테스트 통과 확인

### 7.3 문서화
- [ ] 각 ViewModel 상태 문서화
- [ ] 향후 구현 계획 문서화

---

## 8. 참고 사항

### 8.1 결정 필요
- **방법 1 (명확한 인터페이스)**: 향후 구현 시 인터페이스 계약 준수
- **방법 2 (Feature Flag)**: 스텁 코드 제거, 필요 시 나중에 추가

### 8.2 권장 사항
- **명확한 인터페이스 방식**을 권장 (방법 1)
- 이유: 향후 구현 시 인터페이스 계약을 따르면 일관성 유지 가능

---

**작성자**: NovelGuard 개발팀  
**검토 상태**: 대기 중  
**다음 단계**: Phase 1 시작
