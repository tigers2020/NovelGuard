# FileRecord 마이그레이션 가이드

## 개요

이 문서는 레거시 `FileRecord`에서 새로운 `File` 엔티티로의 마이그레이션 가이드입니다.

## 새로운 구조

### Value Objects (불변)
- `FileId`: 파일 식별자
- `FilePath`: 파일 경로 정보 (path, name, ext, size, mtime)
- `FileMetadata`: 파일 메타데이터 (is_text, encoding, newline)
- `FileHashInfo`: 해시 정보 (hash_strong, fingerprint_fast, fingerprint_norm, simhash64)

### Entity
- `File`: 파일 엔티티 (식별자 + 상태)
  - ValueObject들을 조합
  - 상태 관리 메서드 제공 (add_flag, add_error 등)

### Domain Services
- `FileComparisonService`: 파일 간 비교 로직
  - 동일성 확인 (`are_identical`)
  - 유사성 확인 (`are_similar`)
  - 상세 비교 (`compare`)

## 마이그레이션 방법

### 1. FileRecord → File 변환

```python
# 방법 1: FileRecord.to_file_entity() (deprecated)
file_record = FileRecord(...)
file_entity = file_record.to_file_entity()  # DeprecationWarning 발생

# 방법 2: File.from_file_record() (권장)
file_record = FileRecord(...)
file_entity = File.from_file_record(file_record)
```

### 2. FileMeta → File 변환

```python
from domain.adapters import file_meta_to_file_entity

file_meta = FileMeta(...)
file_entity = file_meta_to_file_entity(file_meta)
```

### 3. File → FileRecord 변환 (역방향 호환성)

```python
# 방법 1: file_entity_to_file_record() (deprecated)
from domain.adapters import file_entity_to_file_record

file_entity = File(...)
file_record = file_entity_to_file_record(file_entity)  # DeprecationWarning 발생

# 방법 2: file_entity.to_file_record() (권장)
file_entity = File(...)
file_record = file_entity.to_file_record()
```

## Adapter 제거 기준

### 제거 조건

다음 조건이 **모두** 충족되면 Adapter를 제거합니다:

1. **모든 UseCase가 새 `File` 엔티티 사용**
   - `scan_files.py`: File 엔티티 사용 ✅ / ❌
   - `find_duplicates.py`: File 엔티티 사용 ✅ / ❌
   - `check_integrity.py`: File 엔티티 사용 ✅ / ❌
   - `build_action_plan.py`: File 엔티티 사용 ✅ / ❌

2. **`FileRecordAdapter` 사용 코드가 0개**
   ```bash
   grep -r "FileRecord" src/ --exclude-dir=domain/models
   # 결과가 없어야 함 (단, domain/models/file_record.py 제외)
   ```

3. **모든 테스트가 새 구조 사용**
   - 통합 테스트: File 엔티티 사용 ✅ / ❌
   - 단위 테스트: File 엔티티 사용 ✅ / ❌

4. **Golden Tests 통과 (새 구조 기준)**
   ```bash
   pytest tests/integration/test_golden_scenarios.py -v
   # 모든 테스트 통과 필요
   ```

### 제거 시점

**Phase 2.3 (Phase 2 통합 테스트) 완료 시점**

Phase 2.3 완료 후:
1. 위 "제거 조건" 4가지 모두 확인
2. `domain/models/file_record.py` 삭제 검토
3. Deprecation 경고 제거
4. 어댑터 관련 코드 제거:
   - `domain/adapters/file_adapter.py`
   - `domain/adapters/__init__.py`
5. 관련 문서 업데이트

## 제거 전 체크리스트

- [ ] 모든 UseCase가 File 엔티티 사용 확인
- [ ] `grep -r "FileRecord" src/` 결과 확인 (domain/models 제외)
- [ ] 모든 테스트가 File 엔티티 사용 확인
- [ ] Golden Tests 통과 확인
- [ ] Phase 2.3 완료 확인
- [ ] 백업 생성 (git tag)
- [ ] `domain/models/file_record.py` 삭제
- [ ] 어댑터 코드 삭제
- [ ] 전체 테스트 재실행 및 통과 확인
- [ ] 문서 업데이트

## 주의사항

1. **점진적 마이그레이션**: 한 번에 하나씩, 테스트하면서 진행
2. **Deprecation 경고 모니터링**: 경고 발생 시 즉시 수정
3. **성능 영향 측정**: 변경 후 벤치마크 실행
4. **롤백 계획**: 각 단계마다 git commit, 필요 시 롤백 가능

## 현재 상태 (Phase 1.2 완료 시점)

### 완료된 작업
- ✅ Value Objects 분리 (FileHashInfo, FilePath, FileMetadata)
- ✅ Entity 분리 (File)
- ✅ Domain Services 분리 (FileComparisonService)
- ✅ 마이그레이션 어댑터 생성
- ✅ Deprecation 경고 추가

### 다음 단계 (Phase 2)
- ⏳ UseCase에서 File 엔티티 사용 (점진적 전환)
- ⏳ Repository에서 File 엔티티 지원
- ⏳ 통합 테스트 업데이트

## 참고

- 계획서: `docs/refactoring_plan_v1.4/04_phase1_p0_blast_radius.md` (Phase 1.2)
- 테스트: `tests/domain/adapters/test_file_adapter.py`
- 어댑터: `src/domain/adapters/file_adapter.py`
