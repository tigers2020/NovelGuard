# 리팩토링 보고서: file_data_store.py

> **우선순위**: P0-4 (최우선)  
> **파일**: `src/gui/models/file_data_store.py`  
> **작성일**: 2025-01-11  
> **상태**: 분석 완료, 리팩토링 대기

---

## 1. 파일 개요 및 현황

### 1.1 기본 정보
- **LOC**: 474 lines
- **클래스 수**: 2개 (`FileData`, `FileDataStore`)
- **최대 메서드 길이**: 약 80+ lines
- **의존성**: Qt, FileEntry

### 1.2 현재 구조
```python
@dataclass
class FileData:
    # 데이터 클래스 (변경 없음)

class FileDataStore(QObject):
    - clear()
    - remove_files()
    - add_file()                    # 단일 파일 추가
    - add_files()                   # 배치 파일 추가
    - update_file()
    - set_duplicate_groups_batch()  # 배치 업데이트
    - add_integrity_issue()
    # ... 기타 메서드
```

---

## 2. 문제점 분석

### 2.1 데이터 저장소 + 이벤트 허브 + 배치 정책 혼재
**현재 문제**:
- `FileDataStore`가 **데이터 저장 + Signal emit + 배치 정책**을 모두 담당
- 단일 변경과 배치 변경 API가 혼재
- 배치 업데이트 정책이 Store 내부에 하드코딩

**영향**:
- 단일 책임 위반: Store가 너무 많은 책임을 가짐
- 테스트 어려움: 배치 정책을 독립적으로 테스트 불가
- 확장성 부족: 다른 배치 정책 적용 시 Store 수정 필요

### 2.2 print() 디버그 코드 존재
**현재 문제**:
- line 363: `print(f"[DEBUG] FileDataStore.set_duplicate_groups_batch...")`
- line 365: `print(f"[DEBUG] FileDataStore.set_duplicate_groups_batch...")`
- 디버그 코드가 제품 코드에 남아있음

### 2.3 배치 업데이트 정책 불명확
**현재 문제**:
- `set_duplicate_groups_batch()`는 배치 시그널만 emit
- 하지만 다른 배치 메서드들은 개별 시그널 emit
- 배치 정책이 일관되지 않음

---

## 3. 리팩토링 목표

### 3.1 핵심 목표
1. **API 명확화**: 단일 변경과 배치 변경 API를 명확히 분리
2. **배치 정책 일관성**: 모든 배치 메서드가 배치 시그널만 emit
3. **디버그 코드 제거**: print() 제거
4. **단일 책임**: Store는 데이터 저장 + Signal emit만 담당 (배치 정책은 UI 레이어에서)

### 3.2 원칙
- **단일 책임**: Store는 데이터 저장만
- **일관성**: 배치 메서드는 배치 시그널만 emit
- **명확성**: API 이름으로 단일/배치 구분

---

## 4. 구체적인 리팩토링 계획

### 4.1 API 명확화

#### 4.1.1 단일 변경 API (기존 유지)
```python
def add_file(self, entry: FileEntry) -> FileData:
    """파일 추가 (단일).
    
    단일 파일 추가 시 file_added 시그널 emit.
    """
    # ... 기존 코드 ...
    self.file_added.emit(file_data)
    return file_data

def update_file(self, file_id: int, **kwargs) -> None:
    """파일 업데이트 (단일).
    
    단일 파일 업데이트 시 file_updated 시그널 emit.
    """
    # ... 기존 코드 ...
    self.file_updated.emit(file_data)
```

#### 4.1.2 배치 변경 API (배치 시그널만 emit)
```python
def add_files(self, entries: list[FileEntry]) -> list[FileData]:
    """여러 파일 추가 (배치).
    
    배치 파일 추가 시 files_added_batch 시그널만 emit.
    개별 file_added 시그널은 emit하지 않음.
    """
    # ... 기존 코드 ...
    # 배치 시그널만 emit (개별 시그널은 emit하지 않음)
    self.files_added_batch.emit(file_data_list)
    return file_data_list

def set_duplicate_groups_batch(
    self,
    updates: list[tuple[int, Optional[int], bool, Optional[float]]]
) -> None:
    """중복 그룹 정보 배치 설정.
    
    배치 업데이트 시 files_updated_batch 시그널만 emit.
    개별 file_updated 시그널은 emit하지 않음.
    """
    # ... 기존 코드 ...
    # 배치 시그널만 emit (기존 방식 유지)
    if changed_ids:
        self.files_updated_batch.emit(changed_ids)
    
    # print() 제거
    # logger.debug() 사용
```

### 4.2 디버그 코드 제거

```python
# 기존 코드 (제거)
print(f"[DEBUG] FileDataStore.set_duplicate_groups_batch: emitting files_updated_batch signal with {len(changed_ids)} file_ids")
self.files_updated_batch.emit(changed_ids)
print(f"[DEBUG] FileDataStore.set_duplicate_groups_batch: files_updated_batch signal emitted")

# 개선된 코드
if self._log_sink:
    from application.utils.debug_logger import debug_step
    debug_step(
        self._log_sink,
        "file_data_store_files_updated_batch_emit",
        {"changed_ids_count": len(changed_ids), "sample_ids": changed_ids[:10]}
    )
self.files_updated_batch.emit(changed_ids)
```

---

## 5. 단계별 작업 계획

### Phase 1: 디버그 코드 제거
- [ ] `print()` 제거
- [ ] `logger.debug()` 또는 `debug_step()` 사용으로 통일

### Phase 2: API 문서화
- [ ] 각 메서드 docstring에 단일/배치 구분 명시
- [ ] 배치 메서드가 배치 시그널만 emit한다는 점 명시

### Phase 3: 통합 테스트
- [ ] 기존 통합 테스트 실행하여 동작 확인
- [ ] 배치 시그널 동작 확인

### Phase 4: 코드 리뷰
- [ ] 코드 리뷰 및 정리
- [ ] 문서 업데이트

---

## 6. 예상 효과

### 6.1 코드 품질
- **명확성**: API 이름으로 단일/배치 구분이 명확
- **일관성**: 배치 메서드가 배치 시그널만 emit
- **디버깅**: print() 제거로 디버깅 용이

### 6.2 유지보수성
- **가독성**: 디버그 코드 제거로 가독성 향상
- **일관성**: 배치 정책 일관성 확보

---

## 7. 체크리스트

### 7.1 코드 작성
- [ ] `print()` 제거
- [ ] API docstring 명확화

### 7.2 테스트
- [ ] 기존 통합 테스트 통과 확인
- [ ] 배치 시그널 동작 확인

### 7.3 문서화
- [ ] 메서드 docstring 업데이트

---

**작성자**: NovelGuard 개발팀  
**검토 상태**: 대기 중  
**다음 단계**: Phase 1 시작
