# Domain Models 분류 계획서

**작성일**: 2026-01-09  
**Phase**: 2.1 - Domain Models 재분류

## 개요

`domain/models/` 폴더의 모든 모델을 DDD 원칙에 따라 재분류합니다.

## 분류 기준

### Entity (엔티티)
- **특징**: 식별자(ID)를 가짐, 생명주기 있음, 일부 속성 변경 가능
- **예**: File, IntegrityIssue

### ValueObject (값 객체)
- **특징**: 불변(frozen), 식별자 없음, 값으로만 비교
- **예**: FileMetadata, FileHashInfo, CandidateEdge, Evidence

### Aggregate (집합 루트)
- **특징**: 여러 Entity/ValueObject를 묶는 일관성 경계
- **예**: DuplicateGroup, ActionPlan

## 분류 결과

### 1. DuplicateGroup → **Aggregate**

**현재 위치**: `domain/models/duplicate_group.py`  
**목표 위치**: `domain/aggregates/duplicate_group.py`

**책임 분석**:
- ✅ 여러 파일을 하나의 중복 그룹으로 묶음
- ✅ 일관성 경계 제공 (그룹 내 파일들의 관계 보장)
- ✅ 불변이지만 Aggregate 역할

**변경 사항**:
- [x] `frozen=True` 유지 (불변성)
- [x] **File 객체 직접 참조 금지**: `member_ids: list[int]` (ID만 저장)
- [ ] CandidateEdge, Evidence를 ValueObject로 포함
- [ ] 함수형 업데이트 메서드 추가 (`with_added_member()` 등)
- [ ] Service를 통한 File lookup

**검증 항목**:
- [ ] File 객체 직접 참조 없음
- [ ] ID 기반 참조만 사용
- [ ] 불변성 유지

---

### 2. CandidateEdge → **ValueObject**

**현재 위치**: `domain/models/candidate_edge.py`  
**목표 위치**: `domain/value_objects/candidate_edge.py`

**책임 분석**:
- ✅ 두 파일 간 관계 표현 (불변)
- ✅ 값으로만 비교 (식별자 없음)
- ✅ 상태만 표현 (비즈니스 로직 없음)

**변경 사항**:
- [x] 이미 `frozen=True` (불변)
- [x] **File 객체 참조 금지**: `a_id: int`, `b_id: int` (ID만 저장)
- [ ] 검증 로직 유지
- [ ] `slots=True` 추가 (메모리 최적화)

**검증 항목**:
- [ ] File 객체 직접 참조 없음
- [ ] ID 기반 참조만 사용
- [ ] 불변성 유지

---

### 3. Evidence → **ValueObject**

**현재 위치**: `domain/models/evidence.py`  
**목표 위치**: `domain/value_objects/evidence.py`

**책임 분석**:
- ✅ 중복 판정 근거 표현 (불변)
- ✅ 값으로만 비교
- ✅ 상태만 표현

**변경 사항**:
- [x] 이미 `frozen=True` (불변)
- [ ] `slots=True` 추가
- [ ] **File 객체 참조 확인**: `detail`에 File 객체 포함되지 않도록

**검증 항목**:
- [ ] File 객체 직접 참조 없음
- [ ] detail에 ID만 저장
- [ ] 불변성 유지

---

### 4. FileFeature → **ValueObject 통합 검토**

**현재 위치**: `domain/models/file_feature.py`  
**목표 위치**: `domain/value_objects/file_metadata.py` (통합)

**책임 분석**:
- ✅ 파일 특징 표현 (불변)
- ⚠️ FileMetadata와 중복 가능성

**변경 사항**:
- [ ] FileMetadata와 통합 검토
- [ ] 중복 필드 제거
- [ ] 단일 ValueObject로 통합 또는 별도 유지 결정

**결정**: 검토 후 통합 또는 별도 유지

---

### 5. FileMeta → **현재 유지**

**현재 위치**: `domain/models/file_meta.py`  
**목표**: 경량 스캔용 모델로 유지

**책임 분석**:
- ✅ 스캔 단계 경량 데이터
- ✅ File 엔티티로 승격(promote) 가능
- ✅ 별도 목적

**변경 사항**:
- [ ] 현재 상태 유지
- [ ] File 엔티티와의 변환 로직 명확화

---

### 6. PreviewStats → **ValueObject**

**현재 위치**: `domain/models/preview_stats.py`  
**목표 위치**: `domain/value_objects/preview_stats.py`

**책임 분석**:
- ✅ 집계 결과 표현 (불변)
- ✅ 계산 로직 없음 (순수 데이터)

**변경 사항**:
- [x] 이미 `slots=True` (최적화)
- [ ] `frozen=True` 추가 (불변성)
- [ ] 계산 로직은 UseCase/Service로 이동

**검증 항목**:
- [ ] 불변성 확인
- [ ] 계산 로직 분리

---

### 7. ActionPlan → **Aggregate**

**현재 위치**: `domain/models/action_plan.py`  
**목표 위치**: `domain/aggregates/action_plan.py`

**책임 분석**:
- ✅ ActionItem들의 집합
- ✅ 일관성 경계 제공
- ✅ 복잡한 생성 로직 (Service 필요)

**변경 사항**:
- [x] 이미 `frozen=True` (불변)
- [ ] ActionItem은 ValueObject로 포함
- [ ] 생성 로직은 `ActionPlanService`로 이동

**검증 항목**:
- [ ] 불변성 유지
- [ ] Service 분리

---

### 8. IntegrityIssue → **Entity**

**현재 위치**: `domain/models/integrity_issue.py`  
**목표 위치**: `domain/entities/integrity_issue.py`

**책임 분석**:
- ✅ 식별자(`issue_id`) 있음
- ✅ 생명주기 있음
- ⚠️ 현재 `frozen=True` (Entity는 변경 가능할 수 있음)

**변경 사항**:
- [ ] **File 객체 참조 금지**: `file_id: int`만 저장
- [ ] `frozen=True` 유지 또는 제거 검토 (Entity는 변경 가능)
- [ ] 필요 시 상태 변경 메서드 추가

**검증 항목**:
- [ ] File 객체 직접 참조 없음
- [ ] ID 기반 참조만 사용

---

## 마이그레이션 순서

### Step 1: ValueObjects 이동
1. [x] CandidateEdge (2.1.3)
2. [x] Evidence (2.1.3)
3. [ ] PreviewStats (2.1.5)

### Step 2: Aggregates 이동
1. [ ] DuplicateGroup (2.1.2)
2. [ ] ActionPlan (2.1.6)

### Step 3: Entities 이동
1. [ ] IntegrityIssue (2.1.7)

### Step 4: 통합 검토
1. [ ] FileFeature + FileMetadata (2.1.4)

### Step 5: 정리
1. [ ] `domain/models/` 폴더 정리 (2.1.8)
2. [ ] Deprecation 경고 추가
3. [ ] Import 경로 업데이트

---

## 리스크 관리

### 순환 의존성 방지
- **전략**: ID 기반 참조 사용
- **규칙**: Entity/ValueObject는 다른 Entity 객체를 직접 참조하지 않음
- **예외**: Aggregate 내부에서만 ValueObject 직접 포함 가능

### 기존 코드 호환성
- **전략**: 어댑터 패턴 + Deprecation 경고
- **기간**: Phase 2 완료 시까지 병행

### 성능 저하 방지
- **전략**: `slots=True` 사용, 프로파일링
- **기준**: 기존 대비 10% 이내 성능 유지

---

## 완료 기준 (DoD)

- [ ] 모든 모델이 적절한 위치로 이동
- [ ] **ID 기반 참조 강제** (File 객체 직접 참조 없음)
- [ ] 불변성 보장 (ValueObject, Aggregate)
- [ ] 단위 테스트 작성 및 통과
- [ ] 통합 테스트 통과
- [ ] 문서 업데이트
- [ ] Deprecation 경고 추가
- [ ] Import 경로 업데이트

---

**다음 단계**: Phase 2.1.2 (DuplicateGroup Aggregate 분리)
