# Deprecated → Removed 전환 기준

## 📋 개요

**목적**: Deprecated 코드를 언제 완전히 제거할 수 있는지에 대한 명확한 기준 제시  
**원칙**: 안전성 우선, 점진적 제거

---

## 🎯 Deprecated vs Removed 구분

### Deprecated (현재 상태)

**특징**:
- ⚠️ Deprecation 경고 포함
- ✅ 하위 호환성 유지
- ✅ 기존 코드에서 여전히 import 가능
- ✅ 실제 사용 가능 (경고만 발생)

**예시**:
```python
# domain/models/duplicate_group.py
import warnings
warnings.warn(
    "domain.models.duplicate_group is deprecated. "
    "Use domain.aggregates.duplicate_group instead.",
    DeprecationWarning,
    stacklevel=2
)
```

### Removed (최종 상태)

**특징**:
- ❌ 파일 완전 삭제
- ❌ import 불가능
- ❌ Deprecation 경고 없음
- ✅ 새 위치로만 접근 가능

---

## 📊 제거 가능 여부 판정 기준

### 기준 1: 사용처 없음 확인

**체크리스트**:
- [ ] 실제 코드에서 import 확인
  ```bash
  grep -r "from domain.models.<name>" src/
  # 결과: 없음 또는 __init__.py만
  ```
- [ ] 테스트 코드에서 import 확인
  ```bash
  grep -r "from domain.models.<name>" tests/
  # 결과: 없음
  ```
- [ ] 타입 힌트에서 사용 확인
  ```bash
  grep -r "domain.models.<name>" src/ --include="*.py"
  # 결과: 없음
  ```

**결과**: ✅ 모든 조건 충족 시 제거 가능

---

### 기준 2: 마이그레이션 기간 경과

**권장 기간**:
- **최소 기간**: 1개 릴리스 주기
- **권장 기간**: 2-3개 릴리스 주기 (약 3-6개월)

**현재 상태**:
- Phase 2.1 완료: 2026-01-09
- 현재: 2026-01-09
- **경과 기간**: 즉시 (아직 마이그레이션 기간 미경과)

**판정**: ⚠️ **마이그레이션 기간 필요**

---

### 기준 3: 대체 경로 확인

**체크리스트**:
- [ ] 새 위치로의 마이그레이션 경로 명확
- [ ] 마이그레이션 가이드 문서 존재
- [ ] 자동 마이그레이션 스크립트 존재 (선택적)

**예시**:
- ✅ `DuplicateGroup` → `domain.aggregates.duplicate_group` 명확
- ✅ `Evidence` → `domain.value_objects.evidence` 명확
- ⚠️ `FileRecord` → `domain.entities.file` (복잡, 별도 가이드 필요)

**결과**: ✅ 대체 경로 명확 시 제거 가능

---

### 기준 4: 테스트 커버리지 확인

**체크리스트**:
- [ ] 새 위치의 테스트 커버리지 충분
- [ ] Deprecated 코드 사용 테스트 없음
- [ ] 전체 테스트 스위트 통과

**현재 상태**:
- ✅ `domain/aggregates/`: 60개 테스트
- ✅ `domain/entities/`: 40개 테스트
- ✅ `domain/value_objects/`: 87개 테스트
- ✅ 전체 테스트: 326 passed

**결과**: ✅ **테스트 커버리지 충분**

---

## 🔄 전환 프로세스

### Phase A: Deprecated 선언 (현재 상태)

**작업**:
- [x] Deprecation 경고 추가
- [x] 새 위치 명시
- [x] 하위 호환성 유지
- [x] 마이그레이션 가이드 제공

**기간**: 즉시 완료 ✅

---

### Phase B: 사용처 마이그레이션

**작업**:
- [ ] 실제 사용처 식별
- [ ] 사용처별 마이그레이션
- [ ] 테스트 업데이트
- [ ] 검증

**기간**: 1-2주

**현재 상태**: ⏳ **진행 필요**

---

### Phase C: 사용처 제거 확인

**작업**:
- [ ] 모든 import 경로 확인
- [ ] 사용처 0건 확인
- [ ] Deprecation 경고 없음 확인

**조건**:
```bash
# 모든 조건 충족 확인
grep -r "from domain.models.duplicate_group" src/ tests/
# 결과: 없음 (또는 __init__.py만)

python -m pytest tests/ -W error::DeprecationWarning
# 결과: 경고 없음 또는 허용된 Deprecated만
```

**기간**: 1일

**현재 상태**: ❌ **조건 미충족**

---

### Phase D: 제거 가능 선언

**작업**:
- [ ] 모든 기준 충족 확인
- [ ] 제거 계획 문서화
- [ ] 팀 리뷰 (필요시)
- [ ] 제거 일정 확정

**기간**: 1일

**현재 상태**: ⏳ **대기 중**

---

### Phase E: 실제 제거

**작업**:
- [ ] 파일 삭제
- [ ] `__init__.py`에서 export 제거
- [ ] 문서 업데이트
- [ ] 최종 테스트 실행

**기간**: 1일

**현재 상태**: ❌ **조건 미충족**

---

## 📋 파일별 제거 가능 여부

### 즉시 제거 가능 (0건 사용)

| 파일 | 새 위치 | 사용처 | 제거 가능 |
|------|---------|--------|----------|
| `candidate_edge.py` | `value_objects/candidate_edge.py` | 0곳 | ✅ 즉시 가능 |

**작업**: 즉시 삭제 가능

---

### 마이그레이션 후 제거 가능 (사용처 존재)

| 파일 | 새 위치 | 사용처 | 마이그레이션 필요 | 제거 가능 |
|------|---------|--------|----------------|----------|
| `duplicate_group.py` | `aggregates/duplicate_group.py` | 6곳 | ✅ 필요 | ⏳ 마이그레이션 후 |
| `action_plan.py` | `aggregates/action_plan.py` | 5곳 | ✅ 필요 | ⏳ 마이그레이션 후 |
| `integrity_issue.py` | `entities/integrity_issue.py` | 6곳 | ✅ 필요 | ⏳ 마이그레이션 후 |
| `evidence.py` | `value_objects/evidence.py` | 1곳 | ✅ 필요 | ⏳ 마이그레이션 후 |
| `preview_stats.py` | `value_objects/preview_stats.py` | 3곳 | ✅ 필요 | ⏳ 마이그레이션 후 |

**작업**: 마이그레이션 계획서대로 진행

---

### 특별 검토 필요 (복잡한 마이그레이션)

| 파일 | 새 위치 | 사용처 | 상태 | 제거 가능 |
|------|---------|--------|------|----------|
| `file_record.py` | `entities/file.py` | 8곳 | 복잡 | ⏳ 검토 후 결정 |
| `file_feature.py` | - (미정) | 0곳 | 검토 필요 | ⏳ 검토 후 결정 |

**작업**: 별도 검토 필요

---

### 유지 (Deprecated 아님)

| 파일 | 이유 | 상태 |
|------|------|------|
| `file_meta.py` | 경량 스캔용, 계속 사용 | ✅ 유지 |

**작업**: 유지

---

## ✅ 제거 가능 여부 판정 매트릭스

### 즉시 제거 가능

**조건**:
- ✅ 사용처 0건
- ✅ 대체 경로 명확
- ✅ 테스트 커버리지 충분

**파일**: `candidate_edge.py`

**작업**: 즉시 삭제

---

### 마이그레이션 후 제거 가능

**조건**:
- ⚠️ 사용처 존재 (1-6곳)
- ✅ 대체 경로 명확
- ✅ 테스트 커버리지 충분
- ⏳ 마이그레이션 필요

**파일**: `duplicate_group.py`, `action_plan.py`, `integrity_issue.py`, `evidence.py`, `preview_stats.py`

**작업**: 마이그레이션 계획서대로 진행 → 마이그레이션 완료 후 제거

---

### 검토 후 결정

**조건**:
- ⚠️ 사용처 많음 (8곳)
- ⚠️ 마이그레이션 복잡
- ⚠️ 또는 용도 불명확

**파일**: `file_record.py`, `file_feature.py`

**작업**: 별도 검토 및 결정

---

## 🔍 제거 전 최종 확인 체크리스트

### 파일별 확인

각 Deprecated 파일에 대해:

- [ ] **사용처 확인**:
  ```bash
  grep -r "from domain.models.<name>" src/ tests/
  grep -r "import domain.models.<name>" src/ tests/
  # 결과: 없음 또는 __init__.py만
  ```

- [ ] **타입 힌트 확인**:
  ```bash
  grep -r "domain.models.<name>" src/ tests/ --include="*.py"
  # 결과: 없음
  ```

- [ ] **Deprecation 경고 확인**:
  ```bash
  python -m pytest tests/ -W error::DeprecationWarning 2>&1 | grep "<name>"
  # 결과: 없음 (해당 Deprecation 경고 없음)
  ```

- [ ] **대체 경로 확인**:
  - 새 위치의 파일 존재 확인
  - 새 위치의 테스트 존재 확인
  - 마이그레이션 가이드 존재 확인

- [ ] **의존성 확인**:
  ```bash
  # 다른 Deprecated 파일에서 사용하는지 확인
  grep -r "from domain.models.<name>" src/domain/models/
  # 결과: 없음
  ```

---

## 📅 권장 제거 일정

### 즉시 제거 (리스크 없음)

**파일**: `candidate_edge.py`

**일정**: 즉시 (사용처 0건)

---

### 단기 제거 (1-2주)

**파일**: `evidence.py`, `preview_stats.py`

**조건**:
- 마이그레이션 완료
- 테스트 통과
- 사용처 0건 확인

**일정**: 마이그레이션 완료 후 즉시

---

### 중기 제거 (2-4주)

**파일**: `integrity_issue.py`, `duplicate_group.py`, `action_plan.py`

**조건**:
- 마이그레이션 완료
- 테스트 통과
- 사용처 0건 확인
- 마이그레이션 기간 1주 경과

**일정**: 마이그레이션 완료 + 1주 후

---

### 장기 검토 (검토 후 결정)

**파일**: `file_record.py`, `file_feature.py`

**조건**:
- 용도 검토 완료
- 마이그레이션 전략 결정
- 별도 마이그레이션 계획 수립

**일정**: 검토 완료 후 결정

---

## ⚠️ 제거 시 주의사항

### 1. Git 히스토리 보존

**권장**:
- 파일 삭제 전 커밋
- 삭제 커밋에 "Deprecated 제거" 명시
- 마이그레이션 완료 확인 후 삭제

---

### 2. 하위 호환성 확인

**체크리스트**:
- [ ] 외부 라이브러리에서 사용하는지 확인 (없으면 문제 없음)
- [ ] 공개 API에서 노출되는지 확인
- [ ] 문서에서 언급하는지 확인

**현재 상태**: ✅ 외부 의존성 없음, 내부 프로젝트만 사용

---

### 3. 점진적 제거

**전략**:
1. 사용처 적은 것부터 제거 (evidence, preview_stats)
2. 중간 사용처 제거 (integrity_issue)
3. 많은 사용처 제거 (duplicate_group, action_plan)
4. 복잡한 것 검토 (file_record)

**이유**: 리스크 최소화, 점진적 검증

---

## ✅ 최종 판정 기준 요약

### 제거 가능 판정식

```
제거 가능 = (
    사용처 0건 AND
    대체 경로 명확 AND
    테스트 커버리지 충분 AND
    (마이그레이션 기간 경과 OR 사용처 적음) AND
    의존성 없음
)
```

### 현재 상태 요약

| 파일 | 사용처 | 대체 경로 | 테스트 | 제거 가능 |
|------|--------|----------|--------|----------|
| `candidate_edge.py` | 0곳 | ✅ 명확 | ✅ 충분 | ✅ 즉시 가능 |
| `evidence.py` | 1곳 | ✅ 명확 | ✅ 충분 | ⏳ 마이그레이션 후 |
| `preview_stats.py` | 3곳 | ✅ 명확 | ✅ 충분 | ⏳ 마이그레이션 후 |
| `integrity_issue.py` | 6곳 | ✅ 명확 | ✅ 충분 | ⏳ 마이그레이션 후 |
| `duplicate_group.py` | 6곳 | ✅ 명확 | ✅ 충분 | ⏳ 마이그레이션 후 |
| `action_plan.py` | 5곳 | ✅ 명확 | ✅ 충분 | ⏳ 마이그레이션 후 |
| `file_record.py` | 8곳 | ⚠️ 복잡 | ✅ 충분 | ⏳ 검토 후 결정 |
| `file_feature.py` | 0곳 | ❌ 미정 | ⚠️ 부족 | ⏳ 검토 후 결정 |

---

**작성일**: 2025-01-09  
**다음 단계**: 마이그레이션 계획서대로 순차 진행
