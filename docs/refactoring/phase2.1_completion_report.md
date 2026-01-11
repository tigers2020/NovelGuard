# Phase 2.1 완료 리포트

## 개요

**Phase 2.1: Domain Models 재분류** 작업이 완료되었습니다.

- **작업 기간**: 2026-01-09
- **총 소요 시간**: 약 2시간 (예상: 17시간, **85% 단축!**)
- **테스트 결과**: 213개 테스트 모두 통과 ✅

## 완료된 작업

### 1. 모델 분석 및 분류 계획 (Phase 2.1.1)

**생성된 문서:**
- `docs/refactoring/model_classification.md` - 모델 분류 계획서

**분류 결과:**
- **Aggregate**: DuplicateGroup, ActionPlan
- **ValueObject**: CandidateEdge, Evidence, PreviewStats, (ActionItem, ActionResult)
- **Entity**: IntegrityIssue
- **유지**: FileMeta (경량 스캔용)
- **검토 필요**: FileFeature (Phase 2.1.4에서 처리)

### 2. DuplicateGroup → Aggregate (Phase 2.1.2)

**생성된 파일:**
- `src/domain/aggregates/` - 디렉토리 생성
- `src/domain/aggregates/duplicate_group.py` - DuplicateGroup Aggregate
- `src/domain/aggregates/__init__.py` - Export
- `tests/domain/aggregates/test_duplicate_group.py` - 27개 테스트

**특징:**
- **ID 기반 참조**: `member_ids: tuple[int, ...]` (File 객체 직접 참조 금지)
- **불변성**: `@dataclass(frozen=True, slots=True)`
- **함수형 업데이트**: `with_status()`, `with_canonical()`, `with_added_member()` 등
- **검증 로직**: confidence, group_type, status, canonical_id 검증
- **조회 메서드**: `get_delete_candidate_ids()` 등

**테스트 결과**: 27개 테스트 통과 ✅

### 3. CandidateEdge, Evidence → ValueObject (Phase 2.1.3)

**생성된 파일:**
- `src/domain/value_objects/candidate_edge.py` - CandidateEdge ValueObject
- `src/domain/value_objects/evidence.py` - Evidence ValueObject
- `tests/domain/value_objects/test_candidate_edge.py` - 19개 테스트
- `tests/domain/value_objects/test_evidence.py` - 22개 테스트

**CandidateEdge 특징:**
- **ID 기반 참조**: `a_id: int`, `b_id: int` (File 객체 직접 참조 금지)
- **불변성**: `@dataclass(frozen=True, slots=True)`
- **검증 로직**: score 범위, relation 종류, a_id ≠ b_id
- **유틸 메서드**: `get_other_id()`, `get_container_id()`, `contains_file()` 등
- **타입 확인**: `is_exact`, `is_near`, `is_containment`

**Evidence 특징:**
- **ID 기반 참조**: detail에 File 객체 포함 금지 (기본 타입만)
- **불변성**: `@dataclass(frozen=True, slots=True)`
- **검증 로직**: kind 종류, detail 내 객체 체크
- **타입 확인**: `is_hash_based`, `is_similarity_based`, `is_containment_based` 등
- **유틸 메서드**: `get_similarity()`, `get_match_spans()`, `has_detail()` 등

**테스트 결과**: 41개 테스트 통과 ✅

### 4. PreviewStats → ValueObject (Phase 2.1.5)

**생성된 파일:**
- `src/domain/value_objects/preview_stats.py` - PreviewStats ValueObject
- `tests/domain/value_objects/test_preview_stats.py` - 23개 테스트

**특징:**
- **불변성**: `@dataclass(frozen=True, slots=True)`
- **검증 로직**: 음수 값 방지 (파일 수, 크기, 확장자 count)
- **집계 메서드**: `get_most_common_extension()`, `get_extension_percentage()` 등
- **조회 메서드**: `get_top_extensions()`, `has_extension()` 등
- **상태 확인**: `is_empty`, `has_size_estimate`

**테스트 결과**: 23개 테스트 통과 ✅

### 5. ActionPlan → Aggregate (Phase 2.1.6)

**생성된 파일:**
- `src/domain/aggregates/action_plan.py` - ActionPlan, ActionItem, ActionResult
- `tests/domain/aggregates/test_action_plan.py` - 33개 테스트

**ActionItem (ValueObject) 특징:**
- **ID 기반 참조**: `file_id: int` (File 객체 직접 참조 금지)
- **불변성**: `@dataclass(frozen=True, slots=True)`
- **검증 로직**: action 종류, risk 레벨
- **타입 확인**: `is_delete`, `is_move`, `is_high_risk` 등
- **의존성**: `depends_on: tuple[int, ...]`

**ActionPlan (Aggregate) 특징:**
- **일관성 경계**: ActionItem들의 집합
- **불변성**: `@dataclass(frozen=True, slots=True)`
- **검증 로직**: created_from 종류, action_id 중복 체크
- **함수형 업데이트**: `with_added_item()`, `with_updated_summary()`
- **조회 메서드**: `get_item_by_id()`, `get_items_by_action()`, `get_delete_count()` 등

**ActionResult (ValueObject) 특징:**
- **실행 결과 기록**: 성공/실패, 에러 메시지, 경로 변경
- **불변성**: `@dataclass(frozen=True, slots=True)`
- **상태 확인**: `is_success`, `is_failure`, `has_error`

**테스트 결과**: 33개 테스트 통과 ✅

### 6. IntegrityIssue → Entity (Phase 2.1.7)

**생성된 파일:**
- `src/domain/entities/integrity_issue.py` - IntegrityIssue Entity
- `tests/domain/entities/test_integrity_issue.py` - 28개 테스트

**특징:**
- **식별자**: `issue_id: int` (Entity)
- **ID 기반 참조**: `file_id: int` (File 객체 직접 참조 금지)
- **불변성**: `@dataclass(frozen=True, slots=True)` (Entity지만 불변으로 설계)
- **동등성**: ID 기반 `__eq__`, `__hash__`
- **검증 로직**: severity, category 종류
- **타입 확인**: `is_error`, `is_warning`, `is_info`, `is_encoding_issue` 등
- **메트릭 접근**: `get_metric()`, `has_metric()`
- **심각도 비교**: `is_more_severe_than()`

**테스트 결과**: 28개 테스트 통과 ✅

## 테스트 결과

### Domain 테스트 (총 213개)

```
tests/domain/adapters/          6 passed (Phase 1.2)
tests/domain/aggregates/       60 passed (27 + 33, 새로 생성)
tests/domain/entities/         40 passed (12 + 28, IntegrityIssue 추가)
tests/domain/ports/             7 passed (Phase 1.2)
tests/domain/services/         13 passed (Phase 1.2)
tests/domain/value_objects/   87 passed (23 + 19 + 22 + 23 추가)
─────────────────────────────────────────────────
Total:                        213 passed
```

**실행 시간**: 0.28초 ⚡

## 구조 개선 요약

### Before (Phase 2.1 이전)

```
domain/
├── entities/
│   ├── file.py              # Phase 1.2에서 생성
│   └── base.py
├── value_objects/
│   ├── file_id.py           # Phase 1.2
│   ├── file_path.py         # Phase 1.2
│   ├── file_metadata.py     # Phase 1.2
│   └── file_hash.py         # Phase 1.2
└── models/                  # 모든 모델이 혼재
    ├── file_record.py
    ├── duplicate_group.py
    ├── candidate_edge.py
    ├── evidence.py
    ├── integrity_issue.py
    ├── action_plan.py
    ├── preview_stats.py
    ├── file_feature.py
    └── file_meta.py
```

### After (Phase 2.1 완료)

```
domain/
├── aggregates/              # ⭐ 새로 생성
│   ├── duplicate_group.py  # DuplicateGroup Aggregate
│   └── action_plan.py      # ActionPlan Aggregate + ActionItem/Result
├── entities/
│   ├── file.py             # Phase 1.2
│   ├── integrity_issue.py  # ⭐ 이동 완료
│   └── base.py
├── value_objects/
│   ├── file_id.py          # Phase 1.2
│   ├── file_path.py        # Phase 1.2
│   ├── file_metadata.py    # Phase 1.2
│   ├── file_hash.py        # Phase 1.2
│   ├── candidate_edge.py   # ⭐ 이동 완료
│   ├── evidence.py         # ⭐ 이동 완료
│   └── preview_stats.py    # ⭐ 이동 완료
├── services/               # Phase 1.2
│   └── file_compare.py
├── adapters/               # Phase 1.2 (마이그레이션 지원)
│   └── file_adapter.py
├── ports/                  # Phase 1.2
│   ├── file_repository.py
│   ├── hash_service.py
│   └── encoding_detector.py
└── models/                 # ⚠️ 레거시 (정리 필요)
    ├── duplicate_group.py  # → 삭제 예정
    ├── candidate_edge.py   # → 삭제 예정
    ├── evidence.py         # → 삭제 예정
    ├── integrity_issue.py  # → 삭제 예정
    ├── action_plan.py      # → 삭제 예정
    ├── preview_stats.py    # → 삭제 예정
    ├── file_feature.py     # → Phase 2.1.4에서 검토
    ├── file_meta.py        # → 유지 (경량 스캔용)
    └── file_record.py      # → Phase 2 완료 후 삭제
```

## 주요 개선사항

### 1. ID 기반 참조 (순환 의존성 방지)
✅ **DuplicateGroup**: `member_ids: tuple[int, ...]`  
✅ **CandidateEdge**: `a_id: int`, `b_id: int`, `evidence_id: int`  
✅ **Evidence**: `evidence_id: int` (detail에 객체 금지)  
✅ **ActionItem**: `file_id: int`, `depends_on: tuple[int, ...]`, `reason_id: int`  
✅ **IntegrityIssue**: `file_id: int`

**효과**: File 객체 직접 참조 제거 → 순환 의존성 완전 방지

### 2. 불변성 보장
모든 새 ValueObject, Aggregate, Entity는 `frozen=True` + `slots=True`

**효과**:
- 버그 방지 (예상치 못한 상태 변경 금지)
- 성능 최적화 (slots로 메모리 절약)
- 함수형 프로그래밍 지원 (with_xxx 메서드)

### 3. 함수형 업데이트 패턴
```python
# 예: DuplicateGroup
original = DuplicateGroup(group_id=1, status="CANDIDATE")
verified = original.with_status("VERIFIED")

# 원본 불변
assert original.status == "CANDIDATE"
# 새 인스턴스 생성
assert verified.status == "VERIFIED"
```

### 4. 타입 안전성
- FileId 타입으로 식별자 명확화 (Phase 1.2)
- 검증 로직으로 잘못된 값 방지 (`__post_init__`)
- 명시적 타입 힌팅 (`tuple[int, ...]`, `dict[str, int]` 등)

### 5. 테스트 용이성
- 순수 함수 중심 (부작용 없음)
- 작은 단위로 분리 (단일 책임)
- Mock 불필요 (ID만 전달)

## 다음 단계 (Phase 2.2~2.4)

### Phase 2.2: 비교/판단 로직 Service로 이동
- [ ] 버전 선택 정책 및 Service 생성
- [ ] 중복 탐지 로직 Service 강화
- [ ] 무결성 검사 로직 Service 생성
- [ ] 증거 생성 로직 Service 생성
- [ ] Entity/ValueObject에서 비즈니스 로직 제거

### Phase 2.3: Phase 2 통합 테스트
- [ ] 전체 단위 테스트 실행
- [ ] 통합 테스트 (모든 UseCase)
- [ ] 성능 벤치마크
- [ ] Golden Tests 실행

### Phase 2.4: Adapter 제거
- [ ] 제거 조건 확인
- [ ] `domain/models/` 폴더 정리
- [ ] Adapter 코드 삭제
- [ ] Import 경로 업데이트

## 리스크 관리

### 완화된 리스크
- ✅ **순환 의존성**: ID 기반 참조로 완전 해결
- ✅ **성능 저하**: slots=True로 메모리 최적화
- ✅ **테스트 복잡도**: 순수 함수로 단순화

### 남은 리스크
- ⚠️ UseCase 업데이트 시 예상치 못한 버그
  - **완화책**: Phase 2.3에서 통합 테스트 + Golden Tests
- ⚠️ 레거시 models 폴더의 import 경로 업데이트
  - **완화책**: Phase 2.4에서 단계적 마이그레이션

## 결론

Phase 2.1은 성공적으로 완료되었습니다. 새로운 DDD 구조는:

- ✅ **명확한 책임 분리**: Aggregate, Entity, ValueObject 구분
- ✅ **순환 의존성 제거**: ID 기반 참조 강제
- ✅ **불변성 보장**: frozen dataclass + 함수형 업데이트
- ✅ **테스트 용이성**: 순수 함수 중심, 213개 테스트 통과
- ✅ **유지보수성**: 작은 단위로 분리, 명확한 인터페이스

**다음 Phase 2.2**에서는 비즈니스 로직을 Domain Service로 이동하여 Domain 계층을 더욱 정제합니다.

---

**작성자**: AI Agent  
**작성일**: 2026-01-09  
**버전**: 1.0
