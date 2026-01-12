# 리팩토링 보고서: filename_parser.py

> **우선순위**: P1-2 (높음)  
> **파일**: `src/domain/services/filename_parser.py`  
> **작성일**: 2025-01-11  
> **상태**: 분석 완료, 리팩토링 대기

---

## 1. 파일 개요 및 현황

### 1.1 기본 정보
- **LOC**: 386 lines
- **클래스 수**: 1개 (`FilenameParser`)
- **최대 메서드 길이**: 약 171 lines
- **의존성**: re, Path, FilenameParseResult

### 1.2 현재 구조
```python
class FilenameParser:
    - parse()                      # 메인 파싱 메서드
    - _parse_with_patterns()       # 정규식 패턴 파싱
    - _parse_with_heuristics()     # 휴리스틱 파싱
    - _parse_fallback()            # 폴백 파싱
    # 정규식 패턴들 (클래스 변수)
```

### 1.3 주요 책임 (현재 혼재됨)
1. **정규식 패턴 정의**: 클래스 변수로 패턴 저장
2. **파싱 규칙**: 패턴 매칭 로직
3. **파싱 정책**: 언어/태그 처리
4. **결과 스키마**: FilenameParseResult 생성

---

## 2. 문제점 분석

### 2.1 규칙/정책/정규식이 한 덩어리
**현재 문제**:
- `FilenameParser`가 **정규식 패턴 + 파싱 규칙 + 태그 정책 + 결과 생성**을 모두 담당
- 정규식 패턴이 클래스 변수로 하드코딩 (20+ lines)
- 파싱 로직과 정규식 패턴이 한 클래스에 혼재

**영향**:
- 테스트 어려움: 정규식 패턴을 독립적으로 테스트 불가
- 재사용성 부족: 정규식 패턴을 다른 곳에서 사용 불가
- 유지보수성: 패턴 수정 시 클래스 전체 수정 필요

### 2.2 클래스 과대화
**현재 문제**:
- 단일 클래스에 모든 파싱 로직 포함
- 패턴별 파싱 메서드가 복잡함 (100+ lines)

**영향**:
- 가독성 저하: 클래스가 커서 이해하기 어려움
- 확장성 부족: 새로운 패턴 추가 시 클래스 수정 필요

---

## 3. 리팩토링 목표

### 3.1 핵심 목표
1. **규칙 분리**: 정규식 패턴을 별도 클래스/모듈로 추출
2. **정책 분리**: 태그 처리 정책을 별도 클래스로 추출
3. **결과 스키마 분리**: FilenameParseResult 생성 로직 명확화
4. **Strategy Pattern**: 패턴별 파서를 전략으로 분리 (선택적)

### 3.2 원칙
- **단일 책임**: 각 클래스는 하나의 책임만
- **재사용성**: 정규식 패턴은 재사용 가능
- **확장성**: 새로운 패턴 추가 시 기존 코드 수정 최소화

---

## 4. 구체적인 리팩토링 계획

### 4.1 새로운 파일 구조

```
src/
├── domain/
│   └── services/
│       ├── filename_parser.py           # 리팩토링 (100 lines 이하로 축소)
│       └── filename_parsing/
│           ├── __init__.py
│           ├── patterns.py               # 새 파일 (정규식 패턴)
│           ├── tag_policy.py             # 새 파일 (태그 정책)
│           └── parsers/
│               ├── __init__.py
│               ├── pattern_parser.py     # 새 파일 (패턴 파서)
│               └── heuristic_parser.py   # 새 파일 (휴리스틱 파서, 선택적)
```

### 4.2 클래스 설계

#### 4.2.1 `FilenamePatterns` (정규식 패턴)

```python
# domain/services/filename_parsing/patterns.py

import re
from typing import ClassVar

class FilenamePatterns:
    """파일명 파싱용 정규식 패턴 정의."""
    
    # 패턴 1: "작품명 1-170" 형식
    PATTERN_RANGE_HYPHEN: ClassVar[re.Pattern] = re.compile(
        r'^(.+?)\s+(\d+)\s*-\s*(\d+)(?:([화권장회])|\(([^)]+)\))?(.*)$'
    )
    
    # 패턴 2: "작품명 1~170" 형식
    PATTERN_RANGE_TILDE: ClassVar[re.Pattern] = re.compile(
        r'^(.+?)\s+(\d+)\s*~\s*(\d+)(?:([화권장회])|\(([^)]+)\))?(.*)$'
    )
    
    # 패턴 3: "작품명 1권" 형식 (단일 범위)
    PATTERN_SINGLE_RANGE: ClassVar[re.Pattern] = re.compile(
        r'^(.+?)\s+(\d+)([화권장회부])(.*)$'
    )
    
    # 패턴 4: "작품명 본편 1-1213 외전 1-71" 형식 (복합 세그먼트)
    PATTERN_MULTI_SEGMENT: ClassVar[re.Pattern] = re.compile(
        r'^(.+?)\s+(본편|외전|에필|후기|1부|2부|3부|4부)\s+(\d+)\s*-\s*(\d+)(?:\s+(본편|외전|에필|후기|1부|2부|3부|4부)\s+(\d+)\s*-\s*(\d+))?(.*)$',
        re.IGNORECASE
    )
    
    # 태그 패턴
    PATTERN_TAGS: ClassVar[re.Pattern] = re.compile(
        r'\(([^)]+)\)|\[([^\]]+)\]|@([^\s]+)|(완결|완전판|완본|후기|에필|에필로그)',
        re.IGNORECASE
    )
```

#### 4.2.2 `TagPolicy` (태그 정책)

```python
# domain/services/filename_parsing/tag_policy.py

class TagPolicy:
    """파일명 태그 처리 정책."""
    
    # 완결 태그
    COMPLETE_TAGS: set[str] = {"완", "完", "완결", "완전판", "완본", "complete", "finished", "end"}
    
    # 후기 태그
    EPILOGUE_TAGS: set[str] = {"후기", "에필", "에필로그", "epilogue", "afterword"}
    
    @classmethod
    def is_complete_tag(cls, tag: str) -> bool:
        """완결 태그 여부 확인."""
        return tag.lower() in cls.COMPLETE_TAGS
    
    @classmethod
    def is_epilogue_tag(cls, tag: str) -> bool:
        """후기 태그 여부 확인."""
        return tag.lower() in cls.EPILOGUE_TAGS
    
    @classmethod
    def extract_tags(cls, text: str) -> list[str]:
        """텍스트에서 태그 추출."""
        # ... 기존 로직 ...
```

#### 4.2.3 리팩토링된 `FilenameParser`

```python
# domain/services/filename_parser.py (리팩토링 후)

from domain.services.filename_parsing.patterns import FilenamePatterns
from domain.services.filename_parsing.tag_policy import TagPolicy
from domain.services.filename_parsing.parsers.pattern_parser import PatternParser

class FilenameParser:
    """파일명 파싱 서비스.
    
    파일명에서 작품명, 범위, 태그를 추출하는 도메인 서비스.
    """
    
    def __init__(self, log_sink: Optional["ILogSink"] = None) -> None:
        """FilenameParser 초기화."""
        self._log_sink = log_sink
        self._pattern_parser = PatternParser(log_sink=log_sink)
        self._tag_policy = TagPolicy()
    
    def parse(self, path: Path) -> FilenameParseResult:
        """파일명을 파싱하여 FilenameParseResult 반환.
        
        Args:
            path: 파일 경로.
        
        Returns:
            파일명 파싱 결과.
        """
        filename = path.stem
        
        # 패턴 파싱 시도
        result = self._pattern_parser.parse(filename, path)
        if result.confidence >= 0.7:
            return result
        
        # 휴리스틱 파싱 시도
        result = self._parse_with_heuristics(filename, path)
        if result.confidence >= 0.4:
            return result
        
        # 폴백: 작품명만 추출
        return self._parse_fallback(filename, path)
```

#### 4.2.4 `PatternParser` (패턴 파서)

```python
# domain/services/filename_parsing/parsers/pattern_parser.py

from domain.services.filename_parsing.patterns import FilenamePatterns

class PatternParser:
    """정규식 패턴 기반 파서."""
    
    def __init__(self, log_sink: Optional["ILogSink"] = None) -> None:
        self._log_sink = log_sink
        self._patterns = FilenamePatterns()
    
    def parse(self, filename: str, path: Path) -> FilenameParseResult:
        """패턴 기반 파싱."""
        # 기존 _parse_with_patterns() 로직
        # ...
```

---

## 5. 단계별 작업 계획

### Phase 1: 패턴 분리
- [ ] `FilenamePatterns` 클래스 생성
- [ ] 기존 정규식 패턴 이동
- [ ] 단위 테스트 작성

### Phase 2: 정책 분리
- [ ] `TagPolicy` 클래스 생성
- [ ] 태그 처리 로직 이동
- [ ] 단위 테스트 작성

### Phase 3: 파서 분리 (선택적)
- [ ] `PatternParser` 클래스 생성
- [ ] 패턴 파싱 로직 이동
- [ ] 단위 테스트 작성

### Phase 4: FilenameParser 리팩토링
- [ ] `FilenameParser`를 파서 조합으로 변경
- [ ] 기존 로직 제거

### Phase 5: 통합 테스트
- [ ] 기존 통합 테스트 실행하여 동작 확인
- [ ] 파싱 정확도 테스트

---

## 6. 예상 효과

### 6.1 코드 품질
- **재사용성**: 정규식 패턴을 다른 곳에서도 사용 가능
- **테스트 가능성**: 각 컴포넌트를 독립적으로 테스트 가능
- **가독성**: FilenameParser가 간결해져 가독성 향상

### 6.2 유지보수성
- **분리**: 패턴/정책/파서 분리로 유지보수 용이
- **확장성**: 새로운 패턴 추가 시 PatternParser만 수정

---

## 7. 체크리스트

### 7.1 코드 작성
- [ ] `FilenamePatterns` 작성
- [ ] `TagPolicy` 작성
- [ ] `PatternParser` 작성 (선택적)
- [ ] `FilenameParser` 리팩토링

### 7.2 테스트
- [ ] 각 컴포넌트 단위 테스트
- [ ] 기존 통합 테스트 통과 확인

### 7.3 문서화
- [ ] 클래스 docstring 작성
- [ ] 패턴 문서화

---

**작성자**: NovelGuard 개발팀  
**검토 상태**: 대기 중  
**다음 단계**: Phase 1 시작
