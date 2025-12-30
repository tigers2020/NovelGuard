# NovelGuard 개발 프로토콜

> **목표**: 텍스트 소설 파일 정리 도구를 **안전하고 체계적으로** 개발하기 위한 절차와 규칙을 정의한다.

---

## 0) 프로토콜 개요

이 프로토콜은 NovelGuard 프로젝트의 모든 개발 활동을 규율한다:
- 개발 절차 및 규칙
- 코딩 컨벤션
- 작업 흐름 정의
- 품질 관리 기준

**핵심 원칙**: 안전성 > 기능성 > 성능

---

## 1) 개발 절차 및 규칙

### 1.1 개발 단계 (MVP → v1.5 → v2)

#### MVP v1 (2-3주 목표)
**필수 기능**:
1. ✅ 파일 스캔 + raw hash 중복 제거
2. ✅ 텍스트 정규화 + normalized hash
3. ✅ 기본 무결성 검사 (인코딩, 0바이트)
4. ✅ PySide6 GUI (폴더 선택, 미리보기, 실행)
5. ✅ dry-run + 리포트 생성

**완료 기준**:
- 1000개 파일 스캔 < 30초
- 중복 판정 정확도 > 95%
- GUI 반응성 (프리징 없음)

---

#### v1.5 (+1-2주)
**추가 기능**:
6. 파일명 파싱 (제목/회차/버전)
7. 신구 버전 점수화 (기본 규칙)
8. 백업 + undo 기능

**완료 기준**:
- 파일명 파싱 성공률 > 80%
- 신구 버전 판정 정확도 > 85%
- Undo 기능 테스트 통과

---

#### v2 (+2-3주)
**고급 기능**:
9. 유사본 탐지 (SimHash)
10. 커스텀 규칙 엔진
11. 시리즈 그룹핑

**완료 기준**:
- 유사본 탐지 정확도 > 90%
- 커스텀 규칙 적용 성공
- 시리즈 그룹핑 정확도 > 75%

---

### 1.2 작업 흐름

#### 기능 개발 워크플로우
```
1. 이슈/요구사항 정의
   ↓
2. 설계 문서 작성 (필요시)
   ↓
3. 브랜치 생성 (feature/기능명)
   ↓
4. 개발 + 단위 테스트
   ↓
5. 통합 테스트
   ↓
6. 코드 리뷰 (self-review)
   ↓
7. 메인 브랜치 병합
   ↓
8. 배포 준비
```

#### 버그 수정 워크플로우
```
1. 버그 재현 + 로그 수집
   ↓
2. 원인 분석
   ↓
3. 수정 + 테스트
   ↓
4. 회귀 테스트
   ↓
5. 핫픽스 브랜치 병합
```

---

### 1.3 브랜치 전략

- **main**: 안정 버전 (배포 가능)
- **develop**: 개발 통합 브랜치
- **feature/기능명**: 기능 개발
- **fix/버그명**: 버그 수정
- **hotfix/긴급수정**: 긴급 패치

**규칙**:
- main에 직접 푸시 금지
- feature 브랜치는 develop에서 분기
- 병합 전 최소 1명 리뷰 (self-review 포함)

---

### 1.4 커밋 메시지 규칙

**형식**:
```
<type>: <짧은 설명>

<상세 설명 (선택)>

<이슈 번호 (선택)>
```

**타입**:
- `feat`: 새로운 기능
- `fix`: 버그 수정
- `refactor`: 리팩토링
- `test`: 테스트 추가/수정
- `docs`: 문서 수정
- `chore`: 빌드/설정 변경
- `perf`: 성능 개선

**예시**:
```
feat: 파일명 파싱 기능 추가

- 제목, 작가, 회차 추출 로직 구현
- 정규식 패턴 매칭 엔진 추가

Closes #12
```

---

## 2) 코딩 컨벤션

### 2.1 Python 스타일 가이드

**기준**: PEP 8 + 프로젝트 특화 규칙

#### 들여쓰기 및 공백
- 4칸 들여쓰기 (탭 금지)
- 최대 줄 길이: 100자 (PEP 8 기본값 79자보다 여유)
- 연산자 주변 공백: `a + b` (O), `a+b` (X)

#### 네이밍 규칙
- **클래스**: `PascalCase` (예: `FileRecord`, `DuplicateAnalyzer`)
- **함수/변수**: `snake_case` (예: `scan_directory`, `file_path`)
- **상수**: `UPPER_SNAKE_CASE` (예: `MAX_FILE_SIZE`, `DEFAULT_ENCODING`)
- **프라이빗**: `_leading_underscore` (예: `_calculate_hash`)

#### 타입 힌팅
- **필수**: 모든 함수 시그니처에 타입 어노테이션
- **Optional**: `Optional[Type]` 또는 `Type | None` (Python 3.10+)
- **제네릭**: `List[FileRecord]`, `Dict[str, int]`

**예시**:
```python
def scan_directory(
    root_path: Path,
    extensions: list[str] = None,
    max_size: int = MAX_FILE_SIZE
) -> list[FileRecord]:
    """디렉토리를 스캔하여 FileRecord 리스트 반환."""
    ...
```

---

### 2.2 모듈 구조

#### 파일 조직
```
src/
├── __init__.py
├── main.py                 # GUI 진입점
├── models/
│   ├── __init__.py
│   └── file_record.py      # FileRecord 모델
├── scanners/
│   ├── __init__.py
│   ├── file_scanner.py     # 파일 스캔
│   └── hash_calculator.py  # 해시 계산
├── analyzers/
│   ├── __init__.py
│   ├── duplicate_analyzer.py
│   └── metadata_extractor.py
├── checkers/
│   ├── __init__.py
│   └── integrity_checker.py
├── gui/
│   ├── __init__.py
│   ├── main_window.py
│   └── widgets/
└── utils/
    ├── __init__.py
    └── text_normalizer.py
```

#### import 순서
1. 표준 라이브러리
2. 서드파티 라이브러리
3. 로컬 모듈

**예시**:
```python
# 표준 라이브러리
from pathlib import Path
from typing import Optional
import hashlib

# 서드파티
from pydantic import BaseModel
from PySide6.QtWidgets import QMainWindow

# 로컬
from models.file_record import FileRecord
from utils.text_normalizer import normalize_text
```

---

### 2.3 문서화 규칙

#### Docstring 형식
**Google 스타일** 사용:

```python
def analyze_duplicates(
    file_records: list[FileRecord],
    threshold: float = 0.95
) -> list[list[FileRecord]]:
    """중복 파일 그룹을 분석하여 반환.
    
    Args:
        file_records: 분석할 FileRecord 리스트
        threshold: 유사도 임계값 (0.0 ~ 1.0)
    
    Returns:
        중복 그룹 리스트. 각 그룹은 FileRecord 리스트.
    
    Raises:
        ValueError: threshold가 0.0 ~ 1.0 범위를 벗어날 때
    
    Example:
        >>> records = [FileRecord(...), FileRecord(...)]
        >>> groups = analyze_duplicates(records, threshold=0.9)
        >>> len(groups)
        1
    """
    ...
```

#### 주석 규칙
- **Why 주석**: 복잡한 로직의 이유 설명
- **What 주석 금지**: 코드 자체가 설명하는 경우 불필요
- **TODO 주석**: `# TODO: v2에서 SimHash 구현`

---

### 2.4 에러 핸들링

#### 예외 처리 원칙
- **구체적 예외**: `FileNotFoundError`, `UnicodeDecodeError` 등
- **에러 메시지**: 사용자 친화적 + 기술적 디테일 (로그)
- **복구 가능성**: 가능하면 자동 복구 시도

**예시**:
```python
def read_file_content(file_path: Path) -> str:
    """파일 내용을 읽어 반환. 인코딩 자동 감지."""
    try:
        # charset-normalizer로 인코딩 감지
        detected = charset_normalizer.detect(file_path.read_bytes())
        encoding = detected['encoding'] or 'utf-8'
        return file_path.read_text(encoding=encoding)
    except UnicodeDecodeError as e:
        logger.error(f"인코딩 오류: {file_path} - {e}")
        raise FileEncodingError(
            f"파일 인코딩을 감지할 수 없습니다: {file_path}"
        ) from e
    except Exception as e:
        logger.error(f"파일 읽기 오류: {file_path} - {e}")
        raise
```

#### 커스텀 예외
```python
class NovelGuardError(Exception):
    """NovelGuard 기본 예외."""
    pass

class FileEncodingError(NovelGuardError):
    """파일 인코딩 관련 오류."""
    pass

class DuplicateAnalysisError(NovelGuardError):
    """중복 분석 오류."""
    pass
```

---

## 3) 품질 관리

### 3.1 테스트 전략

#### 단위 테스트
- **커버리지 목표**: 핵심 로직 80% 이상
- **테스트 파일**: `tests/test_모듈명.py`
- **픽스처**: 실제 파일 샘플 사용 (테스트 데이터 폴더)

**예시**:
```python
# tests/test_duplicate_analyzer.py
def test_analyze_exact_duplicates():
    """완전 동일 파일 중복 탐지 테스트."""
    records = [
        FileRecord(path=Path("file1.txt"), md5_hash="abc123"),
        FileRecord(path=Path("file2.txt"), md5_hash="abc123"),
    ]
    groups = analyze_duplicates(records)
    assert len(groups) == 1
    assert len(groups[0]) == 2
```

#### 통합 테스트
- **시나리오**: 전체 워크플로우 검증
- **테스트 데이터**: 다양한 실제 파일 샘플

---

### 3.2 코드 리뷰 체크리스트

#### 필수 확인 사항
- [ ] 타입 힌팅 적용
- [ ] Docstring 작성
- [ ] 에러 핸들링 적절
- [ ] 테스트 코드 작성
- [ ] 로깅 적절히 사용
- [ ] 성능 고려 (대용량 파일)
- [ ] 보안 고려 (경로 조작 등)

#### 안전성 확인
- [ ] 파일 삭제는 사용자 승인 필수
- [ ] 원본 보존 확인
- [ ] Dry-run 모드 지원
- [ ] 롤백 가능성

---

### 3.3 성능 기준

#### 목표 성능
- **스캔 속도**: 1000개 파일 < 30초
- **해시 계산**: 평균 파일당 < 50ms
- **GUI 반응성**: 작업 중에도 UI 프리징 없음

#### 최적화 전략
- **병렬 처리**: 해시 계산은 `multiprocessing` 활용
- **캐싱**: 스캔 결과 SQLite 저장
- **점진적 처리**: 대량 파일도 메모리 효율적으로

---

## 4) 라이브러리 및 의존성

### 4.1 필수 라이브러리

#### PySide6
- **용도**: GUI 프레임워크
- **이유**: Qt 기반, 안정적, 크로스 플랫폼
- **사용 예**: 메인 윈도우, 파일 목록, 비교 뷰

#### charset-normalizer
- **용도**: 파일 인코딩 자동 감지
- **이유**: 정확도 높음, 다양한 인코딩 지원
- **사용 예**: 텍스트 파일 읽기 전 인코딩 감지

#### pydantic
- **용도**: 데이터 모델 검증
- **이유**: 타입 안전성, 자동 검증, 직렬화
- **사용 예**: `FileRecord` 모델 정의

#### PyInstaller
- **용도**: 실행 파일 패키징
- **이유**: 단일 실행 파일 생성, 배포 용이
- **사용 예**: Windows/Mac/Linux 배포판 생성

---

### 4.2 강력 추천 라이브러리

#### rich
- **용도**: CLI 디버깅, 로그 출력
- **이유**: 예쁜 터미널 출력, 개발 편의성
- **사용 예**: 개발 중 디버그 정보 출력

#### sqlite3 (표준 라이브러리)
- **용도**: 스캔 결과 캐싱
- **이유**: 경량, 파일 기반, 표준 라이브러리
- **사용 예**: 스캔 결과 저장/로드

---

### 4.3 v2용 라이브러리

#### datasketch
- **용도**: MinHash/SimHash 유사도 계산
- **이유**: 대용량 데이터 효율적 처리
- **사용 예**: 유사본 탐지 (v2)

---

## 5) 배포 프로토콜

### 5.1 버전 관리
- **시맨틱 버전**: `MAJOR.MINOR.PATCH`
- **예시**: `1.0.0` (MVP), `1.5.0` (v1.5), `2.0.0` (v2)

### 5.2 배포 준비
1. **체크리스트**:
   - [ ] 모든 테스트 통과
   - [ ] 문서 업데이트
   - [ ] 버전 번호 업데이트
   - [ ] CHANGELOG 작성

2. **빌드**:
   ```bash
   pyinstaller --onefile --windowed src/main.py
   ```

3. **검증**:
   - 실제 환경에서 테스트
   - 설치/실행 확인

---

## 6) 한 줄 미션 리마인더
"안전하게, 체계적으로, 사용자를 위해."

