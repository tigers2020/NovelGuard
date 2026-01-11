# 테스트 픽스처 데이터

이 디렉토리는 NovelGuard의 리팩토링 전 동작을 검증하기 위한 고정된 테스트 데이터셋을 포함합니다.

## 디렉토리 구조

```
fixtures/
├── small/          # 소규모 데이터셋 (10~50개 파일)
├── medium/         # 중규모 데이터셋 (100~500개 파일)
└── edge_cases/     # 엣지 케이스 데이터셋
```

## 데이터셋 설명

### small/ - 소규모 데이터셋

**목적**: 기본 기능 검증 (완전 중복, 정규화 후 중복 등)

**구성**:
- `novel_exact_dup_*.txt` (3개): 완전 동일 파일 (MD5 해시 동일)
- `novel_normalized_*.txt` (3개): 정규화 후 동일 파일 (공백/줄바꿈만 다름)
- `novel_unique_*.txt` (2개): 고유 파일

**예상 결과**:
- 중복 그룹 2개 탐지 (exact_dup 그룹, normalized 그룹)

### medium/ - 중규모 데이터셋

**목적**: 성능 테스트 및 다양한 패턴 검증

**구성**:
- `group_*_file_*.txt`: 10개의 중복 그룹, 각 그룹당 5개 파일 (총 50개)
- `unique_*.txt`: 50개의 고유 파일

**예상 결과**:
- 중복 그룹 10개 탐지
- 총 100개 파일 스캔

### edge_cases/ - 엣지 케이스 데이터셋

**목적**: 특수한 상황에서의 동작 검증

**구성**:

1. **제목이 다르지만 내용 동일**
   - `novel_title_A.txt`, `novel_title_B.txt`
   - 동일한 본문, 다른 제목

2. **포함 관계**
   - `novel_1-114.txt`: 114화까지 포함
   - `novel_1-158.txt`: 158화까지 포함 (1-114화를 포함)
   - 포함 관계 탐지 테스트

3. **인코딩이 섞인 텍스트**
   - `novel_utf8.txt`: UTF-8 인코딩
   - `novel_euckr.txt`: EUC-KR 인코딩 (플랫폼 지원 시)
   - 인코딩 감지 및 처리 테스트

4. **빈 파일**
   - `empty_file.txt`: 0 bytes
   - 빈 파일 처리 테스트

5. **매우 작은 파일**
   - `tiny_file.txt`: 1 byte (< 512 bytes)
   - 작은 파일 처리 테스트

6. **대용량 파일**
   - `large_file.txt`: 대용량 테스트용 (실제로는 작게 생성)
   - 대용량 파일 처리 테스트

7. **바이너리 파일**
   - `binary.bin`: 바이너리 데이터
   - 텍스트/바이너리 구분 테스트

8. **특수 문자 포함**
   - `special_chars.txt`: 탭, 줄바꿈(CRLF/LF) 등 특수 문자
   - 특수 문자 처리 테스트

## 데이터셋 생성

### 자동 생성

```bash
python tests/fixtures/generate_fixtures.py
```

이 스크립트는 다음을 수행합니다:
1. 디렉토리 구조 생성
2. 모든 테스트 파일 생성
3. 생성된 파일 수 출력

### 수동 생성

필요한 경우 직접 파일을 생성할 수 있습니다. 단, **파일 내용과 이름은 일관성을 유지**해야 합니다.

## 사용 예시

### Golden Tests에서 사용

```python
from pathlib import Path
from tests.fixtures import FIXTURES_DIR

fixture_path = FIXTURES_DIR / "small"
result = execute_scan(fixture_path)
```

### 성능 벤치마크에서 사용

```python
from pathlib import Path
from tests.fixtures import FIXTURES_DIR

medium_fixture = FIXTURES_DIR / "medium"
# 성능 측정 수행
```

## 주의사항

1. **고정성**: 이 데이터셋은 **리팩토링 전 기준선**을 나타냅니다. 내용을 변경하지 마세요.

2. **Git 관리**: 
   - 이 디렉토리의 모든 파일은 Git에 커밋됩니다
   - `.gitignore`에서 제외하지 않습니다

3. **OS 독립성**: 
   - 경로 정규화를 통해 OS 간 동일한 결과를 보장합니다
   - 스냅샷 테스트에서 경로는 정규화됩니다

4. **인코딩**: 
   - 일부 인코딩(EUC-KR 등)은 플랫폼에 따라 생성되지 않을 수 있습니다
   - 이는 정상 동작입니다

## 업데이트 규칙

리팩토링 후에도 이 데이터셋은 **변경하지 않습니다**. 새로운 테스트 케이스가 필요하면:
- 새로운 파일을 추가 (기존 파일 수정 금지)
- 또는 새로운 서브디렉토리 생성

## 참고

- Phase 0.5.1에서 생성됨
- Golden Tests (Phase 0.5.2)에서 사용됨
- 성능 벤치마크 (Phase 0.5.3)에서 사용됨
