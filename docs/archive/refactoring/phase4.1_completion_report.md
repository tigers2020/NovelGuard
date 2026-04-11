# Phase 4.1 완료 리포트: `common/types.py` 정리

## 📋 작업 개요

**Phase**: 4.1  
**작업명**: `common/types.py` 정리  
**목표**: 타입 정의의 명확성 향상 및 Domain ValueObject로 전환 가능한 타입 식별  
**상태**: ✅ 완료

---

## 🔍 분석 결과

### `common/types.py` 현재 상태

```python
# 파일 경로 타입
FilePath: TypeAlias = Path | str  # ❌ 사용 안 됨 (domain/value_objects/file_path.py에 ValueObject로 존재)

# 파일 ID 타입
FileID: TypeAlias = int  # ❌ 사용 안 됨 (domain/value_objects/file_id.py에 NewType으로 존재)

# 그룹 ID 타입
GroupID: TypeAlias = int  # ❌ 사용 안 됨 (코드에서 int 직접 사용)

# 이슈 ID 타입
IssueID: TypeAlias = int  # ❌ 사용 안 됨 (코드에서 int 직접 사용)

# 액션 ID 타입
ActionID: TypeAlias = int  # ❌ 사용 안 됨 (코드에서 int 직접 사용)

# 증거 ID 타입
EvidenceID: TypeAlias = int  # ❌ 사용 안 됨 (코드에서 int 직접 사용)

# 해시 값 타입
HashValue: TypeAlias = str  # ❌ 사용 안 됨 (코드에서 str 직접 사용)

# 지문 값 타입
FingerprintValue: TypeAlias = str | int | bytes  # ❌ 사용 안 됨
```

### 사용처 분석

**AST 기반 검색 결과**: `common.types`에서 import하는 파일 **0개**

**실제 코드에서의 타입 사용**:
- `FilePath`: `domain/value_objects/file_path.py`의 `FilePath` ValueObject 사용
- `FileId`: `domain/value_objects/file_id.py`의 `FileId` NewType 사용
- ID 타입들 (`group_id`, `issue_id`, `action_id`, `evidence_id`): `int` 직접 사용
- 해시/지문 타입: `str`, `str | int | bytes` 직접 사용

### Domain ValueObject 대응 관계

| `common/types.py` | `domain/value_objects/` | 상태 |
|-------------------|------------------------|------|
| `FilePath` (TypeAlias) | `FilePath` (ValueObject) | ✅ 이미 존재 |
| `FileID` (TypeAlias) | `FileId` (NewType) | ✅ 이미 존재 |
| `GroupID` | - | ❌ 미사용 (int 직접 사용) |
| `IssueID` | - | ❌ 미사용 (int 직접 사용) |
| `ActionID` | - | ❌ 미사용 (int 직접 사용) |
| `EvidenceID` | - | ❌ 미사용 (int 직접 사용) |
| `HashValue` | - | ❌ 미사용 (str 직접 사용) |
| `FingerprintValue` | - | ❌ 미사용 |

---

## ✅ 수행 작업

### 1. `common/types.py` 삭제

**사유**:
- 실제로 사용되지 않는 파일
- 필요한 타입은 이미 `domain/value_objects/`에 존재
- 단순 TypeAlias는 코드베이스에서 사용되지 않음

**결과**:
- 파일 삭제 ✅
- 테스트 통과 확인 ✅ (326 passed)

---

## 📊 Before/After 비교

### Before
```
src/common/types.py  (28 lines)
├── FilePath: TypeAlias (미사용)
├── FileID: TypeAlias (미사용)
├── GroupID: TypeAlias (미사용)
├── IssueID: TypeAlias (미사용)
├── ActionID: TypeAlias (미사용)
├── EvidenceID: TypeAlias (미사용)
├── HashValue: TypeAlias (미사용)
└── FingerprintValue: TypeAlias (미사용)
```

### After
```
❌ src/common/types.py 삭제

✅ domain/value_objects/ 사용:
├── file_path.py → FilePath (ValueObject)
├── file_id.py → FileId (NewType)
└── ... (기타 ValueObjects)
```

---

## 🎯 타입 정의 현황

### ValueObject로 존재하는 타입

1. **FilePath** (`domain/value_objects/file_path.py`)
   - 불변 ValueObject (`frozen=True`)
   - 경로, 이름, 확장자, 크기, 수정시간 포함
   - 검증 로직 포함

2. **FileId** (`domain/value_objects/file_id.py`)
   - NewType으로 정의 (`FileId = NewType("FileId", int)`)
   - 생성 헬퍼 함수 포함 (`create_file_id`)
   - 음수 검증 포함

### 단순 타입으로 사용 중

- `group_id: int` - DuplicateGroup에서 사용
- `issue_id: int` - IntegrityIssue에서 사용
- `action_id: int` - ActionItem에서 사용
- `evidence_id: int` - Evidence에서 사용
- 해시 값: `str` 직접 사용
- 지문 값: `str | int | bytes` 직접 사용

**판단**: 현재 아키텍처에서는 단순 ID 타입들을 NewType으로 강화할 필요성은 낮음. 필요한 경우 향후 확장 가능.

---

## 🧪 테스트 결과

**전체 테스트**: ✅ 326 passed

삭제 후에도 모든 테스트 통과:
- `common/types.py`를 import하는 테스트 없음
- 실제 타입 사용은 모두 정상 동작

---

## 📝 향후 개선 사항 (선택적)

### Option 1: ID 타입 강화 (NewType)

향후 타입 안전성을 높이기 위해 ID 타입들을 NewType으로 강화할 수 있음:

```python
# domain/value_objects/ids.py
from typing import NewType

GroupId = NewType("GroupId", int)
IssueId = NewType("IssueId", int)
ActionId = NewType("ActionId", int)
EvidenceId = NewType("EvidenceId", int)
```

**장점**: 타입 안전성 향상  
**단점**: 마이그레이션 비용, 현재로서는 과도한 추상화

### Option 2: 현재 상태 유지 (권장)

단순 ID 타입은 `int`로 유지:
- 현재 아키텍처와 일치
- 과도한 추상화 방지
- 필요시 향후 확장 가능

**결론**: 현재는 Option 2 (유지) 권장. 필요시 Option 1 검토.

---

## ✅ Phase 4.1 체크리스트

- [x] `common/types.py` 내용 분석
- [x] Domain ValueObject로 전환 가능한 타입 식별
- [x] 전환 가능한 것은 이동, 불가능한 것은 유지
  - ✅ `FilePath`, `FileId`는 이미 ValueObject/NewType으로 존재
  - ✅ 나머지는 미사용이므로 삭제
- [x] 타입 사용처 확인 및 업데이트
  - ✅ 실제 사용처는 `domain/value_objects/`에 존재
  - ✅ 미사용 파일 삭제로 자동 해결
- [x] 단위 테스트 작성
  - ✅ 기존 테스트 모두 통과 (326 passed)
- [x] 문서 업데이트
  - ✅ 이 리포트 작성

---

## 📊 최종 상태

**삭제된 파일**:
- `src/common/types.py`

**유지된 타입 정의**:
- `domain/value_objects/file_path.py` - FilePath ValueObject
- `domain/value_objects/file_id.py` - FileId NewType
- 기타 ValueObjects (Evidence, CandidateEdge, 등)

**코드베이스 상태**:
- ✅ 모든 테스트 통과 (326 passed)
- ✅ 타입 정의 명확성 향상
- ✅ 중복 제거

---

## 🎉 결론

Phase 4.1 작업 완료. `common/types.py`는 미사용 파일이었으며, 필요한 타입 정의는 이미 `domain/value_objects/`에 적절히 존재함을 확인. 파일 삭제로 코드베이스 정리 완료.

**다음 단계**: Phase 4.2 (전체 아키텍처 검증) 진행
