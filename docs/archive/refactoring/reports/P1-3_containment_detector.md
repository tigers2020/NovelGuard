# 리팩토링 보고서: containment_detector.py

> **우선순위**: P1-3 (높음)  
> **파일**: `src/domain/services/containment_detector.py`  
> **작성일**: 2025-01-11  
> **상태**: 분석 완료, 리팩토링 대기

---

## 1. 파일 개요 및 현황

### 1.1 기본 정보
- **LOC**: 330 lines
- **클래스 수**: 1개 (`ContainmentDetector`)
- **최대 메서드 길이**: 약 183 lines
- **의존성**: FileEntry, FilenameParseResult, ContainmentRelation, VersionRelation

### 1.2 현재 구조
```python
class ContainmentDetector:
    - detect_containment()         # 포함 관계 탐지
    - detect_version()             # 버전 관계 탐지
    # 내부 헬퍼 메서드들
```

### 1.3 주요 책임 (현재 혼재됨)
1. **전처리**: 파일 정보 정규화
2. **비교 전략**: 포함/버전 관계 비교 로직
3. **증거 수집**: 판정 근거 수집
4. **판정**: 관계 존재 여부 판정

---

## 2. 문제점 분석

### 2.1 비교 전략/증거 수집/판정 혼재
**현재 문제**:
- `ContainmentDetector`가 **전처리 + 비교 전략 + 증거 수집 + 판정**을 모두 담당
- `detect_containment()` 메서드가 100+ lines로 복잡
- `detect_version()` 메서드가 80+ lines로 복잡

**영향**:
- 테스트 어려움: 비교 전략을 독립적으로 테스트 불가
- 재사용성 부족: 비교 전략을 다른 곳에서 사용 불가
- 유지보수성: 비교 로직 수정 시 메서드 전체 수정 필요

### 2.2 코드 중복
**현재 문제**:
- `detect_containment()`와 `detect_version()` 사이에 유사한 로직 존재
- 증거 수집 로직이 중복됨

---

## 3. 리팩토링 목표

### 3.1 핵심 목표
1. **전처리 분리**: 파일 정보 정규화 로직을 별도 클래스로 추출
2. **비교 전략 분리**: 포함/버전 비교 로직을 Strategy로 분리
3. **증거 수집 분리**: 증거 수집 로직을 별도 클래스로 추출
4. **판정 분리**: 판정 로직을 명확히 분리

### 3.2 원칙
- **단일 책임**: 각 클래스는 하나의 책임만
- **Strategy Pattern**: 비교 전략을 전략으로 분리
- **재사용성**: 비교 전략은 재사용 가능

---

## 4. 구체적인 리팩토링 계획

### 4.1 새로운 파일 구조

```
src/
├── domain/
│   └── services/
│       ├── containment_detector.py      # 리팩토링 (150 lines 이하로 축소)
│       └── relation_detection/
│           ├── __init__.py
│           ├── preprocessor.py           # 새 파일 (전처리)
│           ├── evidence_collector.py     # 새 파일 (증거 수집)
│           └── strategies/
│               ├── __init__.py
│               ├── containment_strategy.py  # 새 파일
│               └── version_strategy.py      # 새 파일
```

### 4.2 클래스 설계

#### 4.2.1 `RelationPreprocessor` (전처리)

```python
# domain/services/relation_detection/preprocessor.py

class RelationPreprocessor:
    """관계 탐지 전처리."""
    
    @staticmethod
    def normalize_file_info(
        file_entry: FileEntry,
        parse_result: FilenameParseResult
    ) -> dict:
        """파일 정보 정규화.
        
        Returns:
            정규화된 파일 정보 딕셔너리.
        """
        # ... 기존 전처리 로직 ...
```

#### 4.2.2 `ContainmentStrategy` (포함 비교 전략)

```python
# domain/services/relation_detection/strategies/containment_strategy.py

from abc import ABC, abstractmethod

class ComparisonStrategy(ABC):
    """비교 전략 인터페이스."""
    
    @abstractmethod
    def compare(
        self,
        file_a: FileEntry,
        parse_a: FilenameParseResult,
        file_b: FileEntry,
        parse_b: FilenameParseResult
    ) -> Optional[dict]:
        """비교 수행.
        
        Returns:
            관계 정보 딕셔너리 또는 None.
        """
        pass


class ContainmentStrategy(ComparisonStrategy):
    """포함 관계 비교 전략."""
    
    def compare(
        self,
        file_a: FileEntry,
        parse_a: FilenameParseResult,
        file_b: FileEntry,
        parse_b: FilenameParseResult
    ) -> Optional[dict]:
        """포함 관계 비교."""
        # 기존 detect_containment() 로직
        # ...
        return {
            "container_file_id": ...,
            "contained_file_id": ...,
            "evidence": ...,
            "confidence": ...
        }
```

#### 4.2.3 `VersionStrategy` (버전 비교 전략)

```python
# domain/services/relation_detection/strategies/version_strategy.py

class VersionStrategy(ComparisonStrategy):
    """버전 관계 비교 전략."""
    
    def compare(
        self,
        file_a: FileEntry,
        parse_a: FilenameParseResult,
        file_b: FileEntry,
        parse_b: FilenameParseResult
    ) -> Optional[dict]:
        """버전 관계 비교."""
        # 기존 detect_version() 로직
        # ...
        return {
            "newer_file_id": ...,
            "older_file_id": ...,
            "evidence": ...,
            "confidence": ...
        }
```

#### 4.2.4 `EvidenceCollector` (증거 수집)

```python
# domain/services/relation_detection/evidence_collector.py

class EvidenceCollector:
    """관계 탐지 증거 수집."""
    
    @staticmethod
    def collect_containment_evidence(
        parse_a: FilenameParseResult,
        parse_b: FilenameParseResult
    ) -> dict:
        """포함 관계 증거 수집."""
        return {
            "segments_a": [(s.segment_type, s.start, s.end, s.unit) for s in parse_a.segments],
            "segments_b": [(s.segment_type, s.start, s.end, s.unit) for s in parse_b.segments],
            "tags_a": parse_a.tags,
            "tags_b": parse_b.tags
        }
    
    @staticmethod
    def collect_version_evidence(
        parse_a: FilenameParseResult,
        parse_b: FilenameParseResult,
        file_a: FileEntry,
        file_b: FileEntry
    ) -> dict:
        """버전 관계 증거 수집."""
        # ... 기존 증거 수집 로직 ...
```

#### 4.2.5 리팩토링된 `ContainmentDetector`

```python
# domain/services/containment_detector.py (리팩토링 후)

from domain.services.relation_detection.strategies.containment_strategy import ContainmentStrategy
from domain.services.relation_detection.strategies.version_strategy import VersionStrategy

class ContainmentDetector:
    """포함/버전 관계 탐지 서비스."""
    
    def __init__(self, log_sink: Optional["ILogSink"] = None) -> None:
        """ContainmentDetector 초기화."""
        self._log_sink = log_sink
        self._containment_strategy = ContainmentStrategy(log_sink=log_sink)
        self._version_strategy = VersionStrategy(log_sink=log_sink)
    
    def detect_containment(
        self,
        file_a: FileEntry,
        parse_a: FilenameParseResult,
        file_b: FileEntry,
        parse_b: FilenameParseResult
    ) -> Optional[ContainmentRelation]:
        """포함 관계 탐지."""
        # 전략 사용
        result = self._containment_strategy.compare(file_a, parse_a, file_b, parse_b)
        if not result:
            return None
        
        # 결과 객체 생성
        return ContainmentRelation(
            container_file_id=result["container_file_id"],
            contained_file_id=result["contained_file_id"],
            evidence=result["evidence"],
            confidence=result["confidence"]
        )
    
    def detect_version(
        self,
        file_a: FileEntry,
        parse_a: FilenameParseResult,
        file_b: FileEntry,
        parse_b: FilenameParseResult
    ) -> Optional[VersionRelation]:
        """버전 관계 탐지."""
        # 전략 사용
        result = self._version_strategy.compare(file_a, parse_a, file_b, parse_b)
        if not result:
            return None
        
        # 결과 객체 생성
        return VersionRelation(
            newer_file_id=result["newer_file_id"],
            older_file_id=result["older_file_id"],
            evidence=result["evidence"],
            confidence=result["confidence"]
        )
```

---

## 5. 단계별 작업 계획

### Phase 1: 전략 인터페이스 정의
- [ ] `ComparisonStrategy` 인터페이스 생성
- [ ] `ContainmentStrategy` 클래스 생성
- [ ] `VersionStrategy` 클래스 생성
- [ ] 단위 테스트 작성

### Phase 2: 증거 수집 분리
- [ ] `EvidenceCollector` 클래스 생성
- [ ] 증거 수집 로직 이동
- [ ] 단위 테스트 작성

### Phase 3: 전처리 분리 (선택적)
- [ ] `RelationPreprocessor` 클래스 생성
- [ ] 전처리 로직 이동

### Phase 4: ContainmentDetector 리팩토링
- [ ] `ContainmentDetector`를 전략 사용하도록 변경
- [ ] 기존 로직 제거

### Phase 5: 통합 테스트
- [ ] 기존 통합 테스트 실행하여 동작 확인
- [ ] 관계 탐지 정확도 테스트

---

## 6. 예상 효과

### 6.1 코드 품질
- **재사용성**: 비교 전략을 다른 곳에서도 사용 가능
- **테스트 가능성**: 각 전략을 독립적으로 테스트 가능
- **가독성**: ContainmentDetector가 간결해져 가독성 향상

### 6.2 유지보수성
- **분리**: 전략/증거/전처리 분리로 유지보수 용이
- **확장성**: 새로운 비교 전략 추가 시 Strategy만 추가

---

## 7. 체크리스트

### 7.1 코드 작성
- [ ] `ComparisonStrategy` 인터페이스 작성
- [ ] `ContainmentStrategy` 작성
- [ ] `VersionStrategy` 작성
- [ ] `EvidenceCollector` 작성
- [ ] `ContainmentDetector` 리팩토링

### 7.2 테스트
- [ ] 각 전략 단위 테스트
- [ ] 기존 통합 테스트 통과 확인

### 7.3 문서화
- [ ] 클래스 docstring 작성
- [ ] 전략 패턴 문서화

---

**작성자**: NovelGuard 개발팀  
**검토 상태**: 대기 중  
**다음 단계**: Phase 1 시작
