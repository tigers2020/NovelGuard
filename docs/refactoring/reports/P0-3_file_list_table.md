# 리팩토링 보고서: file_list_table.py

> **우선순위**: P0-3 (최우선)  
> **파일**: `src/gui/views/components/file_list_table.py`  
> **작성일**: 2025-01-11  
> **상태**: 분석 완료, 리팩토링 대기

---

## 1. 파일 개요 및 현황

### 1.1 기본 정보
- **LOC**: 499 lines
- **클래스 수**: 2개 (`DuplicateColumnsDelegate`, `FileListTableWidget`)
- **최대 메서드 길이**: 약 100+ lines
- **의존성**: Qt, FileDataStore, Constants

### 1.2 현재 구조
```python
class DuplicateColumnsDelegate(QStyledItemDelegate):
    - _extract_title_from_filename()  # 정규식 처리
    - initStyleOption()                # 렌더링

class FileListTableWidget(QWidget):
    - _setup_ui()                      # UI 설정
    - _connect_signals()               # 시그널 연결
    - _on_file_added()                 # 단일 파일 추가
    - _on_files_added_batch()          # 배치 파일 추가
    - _on_file_updated()               # 단일 업데이트
    - _on_files_updated_batch()        # 배치 업데이트
    - _flush_pending_files()           # 배치 처리
    - _add_file_row()                  # 행 추가
    - _update_file_row()               # 행 업데이트
    - _find_row_by_file_id()           # 행 탐색 (O(n))
```

---

## 2. 문제점 분석

### 2.1 Delegate에서 문자열 생성/정규식 처리 혼재
**현재 문제**:
- `DuplicateColumnsDelegate`가 **렌더링 + 문자열 처리 + 정규식 처리**를 모두 담당
- `_extract_title_from_filename()` 메서드가 복잡한 정규식 처리 포함
- 렌더링 로직과 데이터 처리 로직이 혼재

**영향**:
- 테스트 어려움: Delegate 렌더링 테스트 복잡
- 재사용성 부족: 파일명 파싱 로직을 다른 곳에서 사용 불가
- 유지보수성: 정규식 패턴 수정 시 Delegate 수정 필요

### 2.2 테이블 업데이트 정책 섞임
**현재 문제**:
- `FileListTableWidget`가 **배치 처리 타이머 + 행 캐시 + 업데이트 정책**을 모두 관리
- 배치 처리 정책이 위젯 내부에 하드코딩 (`FileListUpdatePolicy`)
- 테이블 렌더링과 업데이트 정책이 혼재

**영향**:
- 단일 책임 위반: 위젯이 너무 많은 책임을 가짐
- 테스트 어려움: 업데이트 정책을 독립적으로 테스트 불가
- 확장성 부족: 다른 업데이트 정책 적용 시 위젯 수정 필요

### 2.3 print() 디버그 코드 존재
**현재 문제**:
- line 201: `print(f"[DEBUG] FileListTableWidget._connect_signals...")`
- 디버그 코드가 제품 코드에 남아있음

---

## 3. 리팩토링 목표

### 3.1 핵심 목표
1. **Delegate 분리**: 렌더링과 데이터 처리 분리
2. **파일명 파싱 로직 추출**: 재사용 가능한 유틸리티로 분리
3. **업데이트 정책 분리**: UpdateCoordinator로 추출 (선택적)
4. **디버그 코드 제거**: print() 제거

### 3.2 원칙
- **단일 책임**: 각 클래스는 하나의 책임만
- **재사용성**: 파일명 파싱 로직은 유틸리티로
- **테스트 가능성**: 각 컴포넌트를 독립적으로 테스트 가능

---

## 4. 구체적인 리팩토링 계획

### 4.1 새로운 파일 구조

```
src/
├── gui/
│   ├── utils/
│   │   ├── __init__.py
│   │   └── filename_title_extractor.py  # 새 파일
│   │
│   └── views/
│       └── components/
│           ├── file_list_table.py       # 리팩토링
│           └── delegates/
│               ├── __init__.py
│               └── duplicate_columns_delegate.py  # 새 파일
```

### 4.2 클래스 설계

#### 4.2.1 `FilenameTitleExtractor` 유틸리티

```python
# gui/utils/filename_title_extractor.py

import re
from pathlib import Path

class FilenameTitleExtractor:
    """파일명에서 소설 타이틀 추출 유틸리티."""
    
    # 파일명에서 타이틀 추출용 정규식 패턴
    _TITLE_EXTRACT_PATTERNS = [
        re.compile(r'\s+\d+\s*[-~]\s*\d+.*$'),  # " 1-176" 또는 " 1~176" 형식
        re.compile(r'\s+\d+[화권장회부].*$'),  # " 1화", " 1권" 등
        re.compile(r'\s+본편\s+\d+.*$'),  # " 본편 1-1213" 등
        re.compile(r'\s+외전\s+\d+.*$'),  # " 외전 1-71" 등
    ]
    
    @classmethod
    def extract_title(cls, filename: str) -> str:
        """파일명에서 소설 타이틀을 추출.
        
        Args:
            filename: 파일명 (확장자 포함 또는 제외).
            
        Returns:
            추출된 타이틀.
        """
        # 확장자 제거
        name = filename.rsplit('.', 1)[0] if '.' in filename else filename
        
        # 회차 범위 패턴 제거
        for pattern in cls._TITLE_EXTRACT_PATTERNS:
            name = pattern.sub('', name)
        
        # 태그 패턴 제거 (예: "(완)", "[에필]", "@태그")
        name = re.sub(r'\([^)]*\)', '', name)  # (태그)
        name = re.sub(r'\[[^\]]*\]', '', name)  # [태그]
        name = re.sub(r'@[^\s]+', '', name)  # @태그
        
        # 양쪽 공백 제거
        title = name.strip()
        
        return title if title else filename  # 추출 실패 시 원본 반환
```

#### 4.2.2 리팩토링된 `DuplicateColumnsDelegate`

```python
# gui/views/components/delegates/duplicate_columns_delegate.py

from PySide6.QtWidgets import QStyledItemDelegate, QTableWidget
from gui.models.file_data_store import FileData
from gui.utils.filename_title_extractor import FilenameTitleExtractor
from gui.views.components.file_list_constants import FileListColumns

class DuplicateColumnsDelegate(QStyledItemDelegate):
    """중복 그룹, 대표 파일 컬럼을 FileData에서 직접 렌더링."""
    
    def initStyleOption(self, option, index):
        """스타일 옵션 초기화."""
        super().initStyleOption(option, index)
        
        table = self.parent()  # QTableWidget
        row = index.row()
        col = index.column()
        
        # FileData는 파일명 컬럼 item의 FILE_DATA Role에서 가져옴
        base_item = table.item(row, FileListColumns.FILE_NAME)
        if not base_item:
            return
        
        file_data = base_item.data(FileListRoles.FILE_DATA)
        if not isinstance(file_data, FileData):
            return
        
        if col == FileListColumns.DUPLICATE_GROUP:
            option.text = self._format_duplicate_group(file_data)
        elif col == FileListColumns.CANONICAL:
            option.text = self._format_canonical(file_data)
    
    def _format_duplicate_group(self, file_data: FileData) -> str:
        """중복 그룹 컬럼 텍스트 포맷."""
        if file_data.duplicate_group_id is None:
            return "-"
        
        # 파일명에서 타이틀 추출 (유틸리티 사용)
        title = FilenameTitleExtractor.extract_title(file_data.path.name)
        
        group_text = title
        if file_data.similarity_score is not None:
            group_text += f" ({file_data.similarity_score:.0%})"
        
        return group_text
    
    def _format_canonical(self, file_data: FileData) -> str:
        """대표 파일 컬럼 텍스트 포맷."""
        is_representative = file_data.is_canonical or file_data.duplicate_group_id is None
        return "✓" if is_representative else "-"
```

#### 4.2.3 리팩토링된 `FileListTableWidget`

```python
# gui/views/components/file_list_table.py (리팩토링 후)

# DuplicateColumnsDelegate를 별도 파일로 이동
from gui.views.components.delegates.duplicate_columns_delegate import DuplicateColumnsDelegate

class FileListTableWidget(QWidget):
    """파일 리스트 테이블 위젯."""
    
    def __init__(self, data_store: FileDataStore, parent: Optional[QWidget] = None) -> None:
        # ... 기존 코드 ...
        
        # print() 제거
        # logger.debug() 사용 (이미 존재)
    
    def _connect_signals(self) -> None:
        """시그널 연결."""
        # ... 기존 코드 ...
        
        # print() 제거
        logger.debug("FileListTableWidget._connect_signals: files_updated_batch connected=%s", connected)
```

---

## 5. 단계별 작업 계획

### Phase 1: 파일명 파싱 유틸리티 추출
- [ ] `FilenameTitleExtractor` 클래스 생성
- [ ] 기존 `_extract_title_from_filename()` 로직 이동
- [ ] 단위 테스트 작성

### Phase 2: Delegate 분리
- [ ] `DuplicateColumnsDelegate`를 별도 파일로 이동
- [ ] `FilenameTitleExtractor` 사용하도록 수정
- [ ] 기존 코드에서 import 경로 수정

### Phase 3: 디버그 코드 제거
- [ ] `print()` 제거
- [ ] 로거 사용으로 통일

### Phase 4: 통합 테스트
- [ ] 기존 통합 테스트 실행하여 동작 확인
- [ ] 코드 리뷰 및 정리

---

## 6. 예상 효과

### 6.1 코드 품질
- **재사용성**: 파일명 파싱 로직을 다른 곳에서도 사용 가능
- **테스트 가능성**: 각 컴포넌트를 독립적으로 테스트 가능
- **가독성**: Delegate가 렌더링만 담당하여 가독성 향상

### 6.2 유지보수성
- **분리**: 렌더링과 데이터 처리 분리
- **확장성**: 파일명 파싱 로직 수정 시 유틸리티만 수정
- **디버깅**: print() 제거로 디버깅 용이

---

## 7. 체크리스트

### 7.1 코드 작성
- [ ] `FilenameTitleExtractor` 작성
- [ ] `DuplicateColumnsDelegate` 분리
- [ ] `print()` 제거

### 7.2 테스트
- [ ] `FilenameTitleExtractor` 단위 테스트
- [ ] 기존 통합 테스트 통과 확인

### 7.3 문서화
- [ ] 클래스 docstring 작성
- [ ] 메서드 docstring 작성

---

**작성자**: NovelGuard 개발팀  
**검토 상태**: 대기 중  
**다음 단계**: Phase 1 시작
