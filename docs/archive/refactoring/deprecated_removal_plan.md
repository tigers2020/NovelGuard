# Deprecated 코드 제거 계획서

## 📋 개요

**목표**: `domain/models/` 폴더의 Deprecated 코드를 안전하게 제거  
**전략**: 점진적 마이그레이션 → 검증 → 제거  
**우선순위**: 선택적 (기능 동작에는 영향 없음)  
**예상 소요 시간**: 4-6시간

---

## 🔍 현재 상태 분석

### `domain/models/` 사용 현황

| 파일 | Deprecated → 새 위치 | 현재 사용처 | 우선순위 |
|------|---------------------|-----------|---------|
| `duplicate_group.py` | `aggregates/duplicate_group.py` | 5곳 | 높음 |
| `action_plan.py` | `aggregates/action_plan.py` | 5곳 | 높음 |
| `integrity_issue.py` | `entities/integrity_issue.py` | 4곳 | 높음 |
| `evidence.py` | `value_objects/evidence.py` | 1곳 | 중간 |
| `preview_stats.py` | `value_objects/preview_stats.py` | 3곳 | 중간 |
| `file_record.py` | `entities/file.py` | 8곳 | 매우 높음 |
| `candidate_edge.py` | `value_objects/candidate_edge.py` | 0곳 | 낮음 (즉시 삭제 가능) |
| `file_meta.py` | - (유지) | 4곳 | 유지 |
| `file_feature.py` | - (검토 필요) | 0곳 | 검토 후 결정 |

**총 사용처**: 30건 (중복 제거 후 실제 13개 파일)

---

## 📝 마이그레이션 계획

### Phase 1: 우선순위 높은 마이그레이션

#### Step 1.1: `domain.models.duplicate_group` → `domain.aggregates.duplicate_group`

**사용처** (5곳):
1. `app/workflows/analysis_flow.py:11`
2. `usecases/build_action_plan.py:14`
3. `usecases/find_duplicates.py:10`
4. `gui/models/result_index_manager.py:6`
5. `gui/stores/result_store.py:6`
6. `gui/signals/result_signals.py:7`

**작업**:
- [ ] 각 파일에서 import 경로 변경
- [ ] 타입 힌트 확인 (호환성 확인)
- [ ] 테스트 실행 및 검증

**예상 소요 시간**: 1시간

---

#### Step 1.2: `domain.models.action_plan` → `domain.aggregates.action_plan`

**사용처** (5곳):
1. `app/workflows/analysis_flow.py:13`
2. `usecases/build_action_plan.py:13`
3. `gui/stores/result_store.py:8`
4. `gui/signals/result_signals.py:9`
5. `gui/pipeline/result_event_router.py` (타입 힌트)

**작업**:
- [ ] 각 파일에서 import 경로 변경
- [ ] `ActionItem`, `ActionResult`도 함께 이동 확인
- [ ] 타입 힌트 확인 (호환성 확인)
- [ ] 테스트 실행 및 검증

**예상 소요 시간**: 1시간

---

#### Step 1.3: `domain.models.integrity_issue` → `domain.entities.integrity_issue`

**사용처** (4곳):
1. `app/workflows/analysis_flow.py:12`
2. `usecases/build_action_plan.py:15`
3. `usecases/check_integrity.py:11`
4. `gui/models/result_index_manager.py:7`
5. `gui/stores/result_store.py:7`
6. `gui/signals/result_signals.py:8`

**작업**:
- [ ] 각 파일에서 import 경로 변경
- [ ] 타입 힌트 확인 (호환성 확인)
- [ ] 테스트 실행 및 검증

**예상 소요 시간**: 30분

---

### Phase 2: 중간 우선순위 마이그레이션

#### Step 2.1: `domain.models.evidence` → `domain.value_objects.evidence`

**사용처** (1곳):
1. `usecases/find_duplicates.py:12`

**작업**:
- [ ] import 경로 변경
- [ ] 테스트 실행 및 검증

**예상 소요 시간**: 15분

---

#### Step 2.2: `domain.models.preview_stats` → `domain.value_objects.preview_stats`

**사용처** (3곳):
1. `gui/views/main_window.py:33` (TYPE_CHECKING)
2. `gui/workers/preview_worker.py:10`
3. `gui/signals/result_signals.py:10`

**작업**:
- [ ] 각 파일에서 import 경로 변경
- [ ] 테스트 실행 및 검증

**예상 소요 시간**: 30분

---

### Phase 3: FileRecord 마이그레이션 (복잡, 별도 계획 필요)

#### Step 3.1: `domain.models.file_record` → `domain.entities.file` 마이그레이션

**사용처** (8곳):
1. `infra/db/file_repository.py` (핵심 - Repository가 FileRecord 사용)
2. `usecases/scan_files.py:19`
3. `usecases/build_action_plan.py:16`
4. `usecases/find_duplicates.py:11`
5. `domain/adapters/file_adapter.py:12`
6. `domain/entities/file.py:159,196` (from_file_record 메서드)
7. `domain/ports/file_repository.py:8` (Protocol 정의)
8. `domain/services/canonical_selector.py:4`

**문제점**:
- `FileRepository`가 `FileRecord`를 반환 타입으로 사용 중
- `IFileRepository` Protocol이 `FileRecord`를 사용 중
- 많은 UseCase에서 `FileRecord`를 사용 중

**전략**:
- **Option A**: FileRepository를 `File` Entity로 변경 (대규모 변경)
- **Option B**: FileRecord를 "경량 스캔용 레거시 모델"로 유지, File Entity는 "Enrich 후 사용"

**권장**: Option B (현재 구조 유지, FileRecord는 경량 스캔용으로 유지)

**작업** (Option B 선택 시):
- [ ] `FileRecord`를 `file_meta.py`와 함께 유지
- [ ] Deprecation 경고는 유지하되, "경량 스캔용" 용도 명시
- [ ] `File` Entity는 Enrich/분석 단계에서 사용
- [ ] `IFileRepository` Protocol 수정 고려 (선택적)

**예상 소요 시간**: 2-3시간 (Option B) 또는 6-8시간 (Option A)

---

### Phase 4: 즉시 삭제 가능

#### Step 4.1: `domain.models.candidate_edge` 삭제

**사용처**: 0곳

**작업**:
- [ ] 삭제 전 최종 확인
- [ ] `domain/models/__init__.py`에서 제거
- [ ] 파일 삭제
- [ ] 테스트 실행 및 검증

**예상 소요 시간**: 15분

---

### Phase 5: Deprecated 코드 완전 제거

#### Step 5.1: `domain/models/` 폴더 정리

**조건**:
- [ ] 모든 import 경로 변경 완료
- [ ] 모든 테스트 통과 확인
- [ ] Deprecation 경고 없음 확인

**작업**:
- [ ] `domain/models/__init__.py` 삭제 또는 빈 파일로 변경
- [ ] Deprecated 파일 삭제:
  - `duplicate_group.py` 삭제
  - `action_plan.py` 삭제
  - `integrity_issue.py` 삭제
  - `evidence.py` 삭제
  - `preview_stats.py` 삭제
  - `candidate_edge.py` 삭제
- [ ] 유지 파일:
  - `file_meta.py` (경량 스캔용)
  - `file_record.py` (Option B 선택 시 유지, 또는 File Entity로 마이그레이션)
  - `file_feature.py` (검토 후 결정)

**예상 소요 시간**: 30분

---

## ⚠️ 주의사항

### 1. FileRecord 마이그레이션은 복잡함

**현재 구조**:
- FileRepository는 `FileRecord`를 반환
- FileRecord는 경량 스캔용 (메타데이터만)
- File Entity는 Enrich/분석용 (완전한 정보)

**권장 전략**: FileRecord는 "경량 스캔용 레거시 모델"로 유지
- Deprecation 경고는 유지
- 용도 명시 ("경량 스캔용")
- File Entity는 분석 단계에서 사용

### 2. FileMeta는 유지

**이유**:
- 경량 스캔용으로 계속 사용 중
- FileRecord보다 더 가벼운 모델
- Deprecated가 아님

### 3. FileFeature는 검토 필요

**현재 상태**: 사용처 0곳  
**검토 사항**: 실제로 필요한지 확인 후 결정

---

## ✅ 검증 기준

### 마이그레이션 완료 기준

1. **Import 경로 변경 확인**:
   ```bash
   grep -r "from domain.models" src/ | grep -v "file_meta\|file_record\|file_feature"
   # 결과: 없음 (또는 file_meta, file_record, file_feature만)
   ```

2. **Deprecation 경고 확인**:
   ```bash
   python -m pytest tests/ --tb=no -q | grep -i "deprecation"
   # 결과: file_meta, file_record, file_feature 관련만 (선택적)
   ```

3. **테스트 통과 확인**:
   ```bash
   python -m pytest tests/ --tb=no -q
   # 결과: 모든 테스트 통과 (326 passed)
   ```

---

## 📊 마이그레이션 우선순위 매트릭스

| 작업 | 우선순위 | 복잡도 | 예상 시간 | 위험도 |
|------|---------|--------|----------|--------|
| candidate_edge 삭제 | 낮음 | 낮음 | 15분 | 낮음 |
| preview_stats 마이그레이션 | 중간 | 낮음 | 30분 | 낮음 |
| evidence 마이그레이션 | 중간 | 낮음 | 15분 | 낮음 |
| integrity_issue 마이그레이션 | 높음 | 낮음 | 30분 | 낮음 |
| duplicate_group 마이그레이션 | 높음 | 낮음 | 1시간 | 낮음 |
| action_plan 마이그레이션 | 높음 | 낮음 | 1시간 | 낮음 |
| file_record 마이그레이션 | 매우 높음 | 높음 | 2-8시간 | 중간 |

**총 예상 시간**: 4-6시간 (file_record Option B 선택 시)

---

## 🎯 실행 순서 권장안

### 최소 리스크 경로

1. **Step 1**: candidate_edge 삭제 (즉시, 리스크 없음)
2. **Step 2**: preview_stats, evidence 마이그레이션 (낮은 리스크)
3. **Step 3**: integrity_issue, duplicate_group, action_plan 마이그레이션 (낮은 리스크)
4. **Step 4**: file_record 검토 및 결정 (중간 리스크)

### 빠른 완료 경로

모든 단계를 한 번에 수행:
- 예상 시간: 4-6시간
- 리스크: 중간 (충분한 테스트 필요)

---

## ✅ 체크리스트

### Phase 1: 우선순위 높은 마이그레이션
- [ ] duplicate_group 마이그레이션 (5곳)
- [ ] action_plan 마이그레이션 (5곳)
- [ ] integrity_issue 마이그레이션 (4곳)
- [ ] 테스트 실행 및 검증

### Phase 2: 중간 우선순위
- [ ] evidence 마이그레이션 (1곳)
- [ ] preview_stats 마이그레이션 (3곳)
- [ ] 테스트 실행 및 검증

### Phase 3: FileRecord 검토
- [ ] FileRecord 사용 현황 재분석
- [ ] 마이그레이션 전략 결정 (Option A vs B)
- [ ] 결정에 따른 작업 수행
- [ ] 테스트 실행 및 검증

### Phase 4: 즉시 삭제
- [ ] candidate_edge 삭제 (0곳 사용)
- [ ] 테스트 실행 및 검증

### Phase 5: 최종 정리
- [ ] 모든 Deprecated 파일 삭제
- [ ] `domain/models/__init__.py` 정리
- [ ] 최종 테스트 실행
- [ ] 문서 업데이트

---

**작성일**: 2025-01-09  
**다음 단계**: Phase 1부터 순차적으로 진행
