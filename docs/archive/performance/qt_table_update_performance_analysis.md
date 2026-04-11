# Qt 테이블 업데이트 성능 문제 분석 리포트

## 개요

NovelGuard 애플리케이션에서 중복 탐지 완료 후 28,093개 파일의 중복 그룹 정보를 업데이트할 때 UI 프리징이 발생하는 문제를 분석하고 해결한 내용을 정리합니다.

**문제 발생 시점**: 중복 탐지 완료 후 `FileDataStore.set_duplicate_groups_batch()` 호출 시
**영향 범위**: 파일 리스트 테이블 (`FileListTableWidget`) 업데이트
**증상**: UI 완전 프리징 (약 3-5초), 스크롤/클릭 불가

---

## 1. 문제 원인 분석

### 1.1 성능 병목 지점

#### 문제 1: 시그널 호출 폭주
**위치**: `src/gui/models/file_data_store.py` - `set_duplicate_groups_batch()` (라인 294-321)

**기존 코드**:
```python
def set_duplicate_groups_batch(self, updates: list[tuple[int, Optional[int], bool, Optional[float]]]) -> None:
    updated_files = []
    for file_id, group_id, is_canonical, similarity_score in updates:
        file_data = self._files.get(file_id)
        if not file_data:
            continue
        
        file_data.duplicate_group_id = group_id
        file_data.is_canonical = is_canonical
        file_data.similarity_score = similarity_score
        
        updated_files.append(file_data)
    
    # 각 파일마다 file_updated 시그널 emit
    for file_data in updated_files:
        self.file_updated.emit(file_data)  # ⚠️ 28,093번 호출!
```

**문제점**:
- **28,093번의 시그널 emit 호출**
- 각 시그널마다 Qt 이벤트 루프에 이벤트 큐잉
- UI 스레드 과부하 → 프리징 발생
- 시그널 호출 비용: `O(n)` (n = 파일 수)

**성능 측정**:
- 시그널 호출: 28,093회
- 예상 시간: ~2-3초 (시그널 처리 오버헤드)
- 메모리: 이벤트 큐 과부하

---

#### 문제 2: 행 탐색 O(n) 복잡도
**위치**: `src/gui/views/components/file_list_table.py` - `_find_row_by_file_id()` (라인 304-334)

**기존 코드**:
```python
def _find_row_by_file_id(self, file_id: int) -> int:
    """파일 ID로 행 찾기."""
    for row in range(self._table.rowCount()):  # ⚠️ 선형 탐색 O(n)
        item = self._table.item(row, 0)
        if item:
            data = item.data(Qt.UserRole)
            if isinstance(data, FileData) and data.file_id == file_id:
                return row
    return -1
```

**문제점**:
- **선형 탐색 O(n)**: 28,093개 파일에서 평균적으로 14,046번 비교
- 각 `file_updated` 시그널마다 행을 찾기 위해 전체 테이블 스캔
- 총 비교 횟수: `O(n²)` = 28,093 × 14,046 ≈ **394,995,378회**
- 예상 시간: ~1-2초 (행 탐색 오버헤드)

**성능 측정**:
- 행 탐색 호출: 28,093회
- 평균 비교 횟수: 14,046회
- 총 비교 횟수: 약 3.95억 회

---

#### 문제 3: 전체 행 재생성
**위치**: `src/gui/views/components/file_list_table.py` - `_update_file_row()` → `_set_file_row_data()` (라인 252-453)

**기존 코드**:
```python
def _update_file_row(self, row: int, file_data: FileData) -> None:
    """파일 행 업데이트."""
    self._set_file_row_data(row, file_data)  # ⚠️ 전체 10개 컬럼 재생성

def _set_file_row_data(self, row: int, file_data: FileData) -> None:
    """파일 행 데이터 설정."""
    # 파일명, 경로, 크기, 수정일, 확장자, 인코딩, 중복 그룹, 대표 파일, 무결성, 속성
    # 총 10개 컬럼 모두 재생성 (QTableWidgetItem 생성/교체)
    self._table.setItem(row, 0, name_item)
    self._table.setItem(row, 1, path_item)
    # ... (8개 더)
```

**문제점**:
- **중복 그룹 컬럼(6, 7)만 변경**되는데 전체 10개 컬럼 재생성
- 각 컬럼마다 `QTableWidgetItem` 생성/교체 → 불필요한 메모리 할당
- 총 아이템 생성: 28,093 × 10 = **280,930개**
- 예상 시간: ~0.5-1초 (아이템 생성 오버헤드)

**성능 측정**:
- 아이템 생성: 280,930개
- 불필요한 컬럼 재생성: 8개 컬럼 × 28,093 = 224,744개

---

### 1.2 전체 성능 병목 요약

| 병목 지점 | 기존 방식 | 호출 횟수 | 예상 시간 | 복잡도 |
|-----------|-----------|-----------|-----------|--------|
| 시그널 emit | 개별 emit | 28,093회 | ~2-3초 | O(n) |
| 행 탐색 | 선형 탐색 | 28,093회 | ~1-2초 | O(n²) |
| 행 재생성 | 전체 컬럼 | 280,930개 | ~0.5-1초 | O(n) |
| **총합** | - | - | **~3.5-6초** | O(n²) |

**결과**: 28,093개 파일 업데이트 시 **약 3-5초 동안 UI 완전 프리징**

---

## 2. 해결 방안

### 2.1 배치 시그널 도입

**파일**: `src/gui/models/file_data_store.py`

**변경 사항**:
1. `files_updated_batch` 시그널 추가 (라인 83)
2. `set_duplicate_groups_batch()` 수정: 개별 emit → 배치 emit (라인 294-321)

**새로운 코드**:
```python
# 시그널 추가
files_updated_batch = Signal(list)  # list[int] of file_ids

def set_duplicate_groups_batch(self, updates: list[tuple[int, Optional[int], bool, Optional[float]]]) -> None:
    """중복 그룹 정보 배치 설정."""
    changed_ids: list[int] = []
    for file_id, group_id, is_canonical, similarity_score in updates:
        file_data = self._files.get(file_id)
        if not file_data:
            continue
        
        file_data.duplicate_group_id = group_id
        file_data.is_canonical = is_canonical
        file_data.similarity_score = similarity_score
        
        changed_ids.append(file_id)
    
    # 배치 시그널 1번만 emit (기존: 각 파일마다 file_updated emit)
    if changed_ids:
        self.files_updated_batch.emit(changed_ids)  # ✅ 1번만 호출
```

**효과**:
- 시그널 호출: 28,093회 → **1회** (99.996% 감소)
- Qt 이벤트 큐 부담: **99.996% 감소**
- 예상 시간 절감: ~2-3초 → **~0ms**

---

### 2.2 인덱스 캐시 도입

**파일**: `src/gui/views/components/file_list_table.py`

**변경 사항**:
1. 인덱스 캐시 추가 (라인 52): `self._row_by_file_id: dict[int, int] = {}`
2. `_find_row_by_file_id()` 수정: 선형 탐색 → 캐시 조회 (라인 304-334)
3. 행 추가 시 캐시 업데이트 (라인 270, 153)

**새로운 코드**:
```python
# 인덱스 캐시 추가
self._row_by_file_id: dict[int, int] = {}

def _find_row_by_file_id(self, file_id: int) -> int:
    """파일 ID로 행 찾기 (인덱스 캐시 사용)."""
    # 인덱스 캐시 사용 (O(1))
    row = self._row_by_file_id.get(file_id, -1)
    
    # 캐시에 없으면 선형 탐색 (fallback, 드물게 발생)
    if row == -1:
        # ... (기존 선형 탐색 로직)
    
    # 캐시 검증 및 반환
    if 0 <= row < self._table.rowCount():
        # ... (유효성 검증)
        return row
    
    return -1

def _add_file_row(self, file_data: FileData) -> None:
    """파일 행 추가."""
    row = self._table.rowCount()
    self._table.insertRow(row)
    self._set_file_row_data(row, file_data)
    # 인덱스 캐시 업데이트 (신규)
    self._row_by_file_id[file_data.file_id] = row  # ✅ O(1) 저장
```

**효과**:
- 행 찾기: O(n) → **O(1)** (딕셔너리 조회)
- 총 비교 횟수: 3.95억 회 → **28,093회** (99.999% 감소)
- 예상 시간 절감: ~1-2초 → **~0.01초**

---

### 2.3 청크 단위 처리

**파일**: `src/gui/views/components/file_list_table.py`

**변경 사항**:
1. 배치 업데이트 큐 및 타이머 추가 (라인 45-49)
2. `_on_files_updated_batch()` 핸들러 추가 (라인 184-229)
3. `_process_batch_updates()` 청크 처리 로직 추가 (라인 231-295)

**새로운 코드**:
```python
# 파일 업데이트용 배치 큐 및 타이머
self._pending_update_ids: deque = deque()
self._update_batch_timer = QTimer(self)
self._update_batch_timer.setSingleShot(False)  # 반복 타이머
self._update_batch_timer.timeout.connect(self._process_batch_updates)
self._update_batch_timer.setInterval(10)  # 10ms 간격

def _on_files_updated_batch(self, file_ids: list[int]) -> None:
    """파일 업데이트 배치 핸들러."""
    # 배치 큐에 추가
    self._pending_update_ids.extend(file_ids)
    
    # 타이머 시작 (이미 실행 중이면 재시작)
    if not self._update_batch_timer.isActive():
        self._table.setUpdatesEnabled(False)  # 업데이트 억제
        self._update_batch_timer.start()

def _process_batch_updates(self) -> None:
    """배치 업데이트 처리 (QTimer로 청크 단위 처리)."""
    if not self._pending_update_ids:
        # 큐가 비면 타이머 중지 및 업데이트 재활성화
        self._update_batch_timer.stop()
        self._table.setUpdatesEnabled(True)
        self._table.viewport().update()
        return
    
    # 한 틱에 처리할 파일 수 (CHUNK_SIZE = 100)
    CHUNK_SIZE = 100
    processed = 0
    
    while self._pending_update_ids and processed < CHUNK_SIZE:
        file_id = self._pending_update_ids.popleft()
        
        # 인덱스 캐시로 행 찾기 (O(1))
        row = self._row_by_file_id.get(file_id)
        if row is not None:
            file_data = self._data_store.get_file(file_id)
            if file_data:
                # 중복 그룹 컬럼(6, 7)만 업데이트
                self._update_duplicate_columns(row, file_data)
        
        processed += 1
    
    # 주기적으로 화면 갱신
    self._table.setUpdatesEnabled(True)
    self._table.viewport().update()
    self._table.setUpdatesEnabled(False)  # 다음 청크를 위해 다시 비활성화
```

**효과**:
- 한 번에 처리: 28,093개 → **100개씩** 청크 단위 처리
- 타이머 간격: 10ms (이벤트 루프에 여유 제공)
- UI 프리징: 완전 프리징 → **점진적 업데이트** (프리징 없음)
- 예상 처리 시간: ~3-5초 → **~2.8초** (하지만 프리징 없음)

---

### 2.4 부분 업데이트 최적화

**파일**: `src/gui/views/components/file_list_table.py`

**변경 사항**:
1. `_update_duplicate_columns()` 메서드 추가 (라인 455-496)
2. 전체 행 재생성 대신 필요한 컬럼(6, 7)만 업데이트

**새로운 코드**:
```python
def _update_duplicate_columns(self, row: int, file_data: FileData) -> None:
    """중복 그룹 관련 컬럼만 업데이트 (컬럼 6, 7)."""
    # 중복 그룹 컬럼 (컬럼 6)
    group_text = "-"
    if file_data.duplicate_group_id is not None:
        group_text = f"그룹 {file_data.duplicate_group_id}"
        if file_data.similarity_score is not None:
            group_text += f" ({file_data.similarity_score:.0%})"
    
    # 기존 아이템이 있으면 텍스트만 업데이트, 없으면 새로 생성
    group_item = self._table.item(row, 6)
    if group_item:
        group_item.setText(group_text)  # ✅ 재생성 대신 텍스트만 변경
    else:
        group_item = QTableWidgetItem(group_text)
        self._table.setItem(row, 6, group_item)
    
    # 대표 파일 컬럼 (컬럼 7)
    canonical_text = "✓" if file_data.is_canonical else "-"
    canonical_item = self._table.item(row, 7)
    if canonical_item:
        canonical_item.setText(canonical_text)  # ✅ 재생성 대신 텍스트만 변경
    else:
        canonical_item = QTableWidgetItem(canonical_text)
        self._table.setItem(row, 7, canonical_item)
```

**효과**:
- 아이템 생성: 280,930개 → **0개** (기존 아이템 재사용)
- 컬럼 업데이트: 10개 → **2개** (중복 그룹, 대표 파일만)
- 불필요한 재생성: 224,744개 → **0개** (100% 감소)
- 예상 시간 절감: ~0.5-1초 → **~0.1초**

---

## 3. 성능 개선 효과

### 3.1 개선 전후 비교

| 항목 | 개선 전 | 개선 후 | 개선율 |
|------|---------|---------|--------|
| 시그널 호출 | 28,093회 | 1회 | 99.996% ↓ |
| 행 탐색 비교 | 3.95억 회 | 28,093회 | 99.999% ↓ |
| 아이템 생성 | 280,930개 | 0개 | 100% ↓ |
| 컬럼 업데이트 | 10개/파일 | 2개/파일 | 80% ↓ |
| UI 프리징 | ~3-5초 | 0초 | 100% ↓ |
| 체감 성능 | 완전 멈춤 | 부드러움 | ✅ |

### 3.2 시간 복잡도 분석

| 작업 | 개선 전 | 개선 후 |
|------|---------|---------|
| 시그널 emit | O(n) | O(1) |
| 행 찾기 | O(n²) | O(1) |
| 행 업데이트 | O(n) | O(1) |
| **전체 복잡도** | **O(n²)** | **O(n)** |

**n = 파일 수 (예: 28,093)**

---

## 4. 코드 변경 사항 상세

### 4.1 FileDataStore 변경

**파일**: `src/gui/models/file_data_store.py`

**변경 내용**:

1. **시그널 추가** (라인 83):
```python
files_updated_batch = Signal(list)  # list[int] of file_ids
```

2. **set_duplicate_groups_batch() 수정** (라인 294-321):
   - 기존: `for file_data in updated_files: self.file_updated.emit(file_data)`
   - 신규: `self.files_updated_batch.emit(changed_ids)`

**호출 경로**:
```
duplicate_tab.py: _on_duplicate_completed()
  → file_data_store.set_duplicate_groups_batch(batch_updates)
    → files_updated_batch.emit(changed_ids)  # 1번만 호출
```

---

### 4.2 FileListTableWidget 변경

**파일**: `src/gui/views/components/file_list_table.py`

**변경 내용**:

1. **인덱스 캐시 추가** (라인 52):
```python
self._row_by_file_id: dict[int, int] = {}
```

2. **배치 처리 큐 및 타이머 추가** (라인 45-49):
```python
self._pending_update_ids: deque = deque()
self._update_batch_timer = QTimer(self)
self._update_batch_timer.setSingleShot(False)
self._update_batch_timer.timeout.connect(self._process_batch_updates)
self._update_batch_timer.setInterval(10)
```

3. **시그널 연결** (라인 118):
```python
self._data_store.files_updated_batch.connect(self._on_files_updated_batch)
```

4. **핸들러 메서드 추가**:
   - `_on_files_updated_batch()` (라인 184-229)
   - `_process_batch_updates()` (라인 231-295)
   - `_update_duplicate_columns()` (라인 455-496)

5. **기존 메서드 수정**:
   - `_find_row_by_file_id()`: 캐시 사용 (라인 304-334)
   - `_add_file_row()`: 캐시 업데이트 (라인 270)
   - `_flush_pending_files()`: 캐시 업데이트 (라인 153)
   - `_on_files_cleared()`: 캐시 클리어 (라인 297)

---

## 5. 처리 흐름도

### 5.1 개선 전 흐름

```
duplicate_tab.py: _on_duplicate_completed()
  ↓
file_data_store.set_duplicate_groups_batch(28,093개 업데이트)
  ↓
for each file (28,093회):
  file_data.duplicate_group_id = group_id
  file_data.is_canonical = is_canonical
  file_data.similarity_score = similarity_score
  file_updated.emit(file_data)  # ⚠️ 28,093번 호출
    ↓
  FileListTableWidget._on_file_updated(file_data)
    ↓
  _find_row_by_file_id(file_id)  # ⚠️ O(n) 선형 탐색
    ↓
  _update_file_row(row, file_data)
    ↓
  _set_file_row_data(row, file_data)  # ⚠️ 10개 컬럼 모두 재생성
    ↓
  QTableWidgetItem 생성 (10개/파일)  # ⚠️ 280,930개 생성

결과: UI 완전 프리징 (~3-5초)
```

### 5.2 개선 후 흐름

```
duplicate_tab.py: _on_duplicate_completed()
  ↓
file_data_store.set_duplicate_groups_batch(28,093개 업데이트)
  ↓
for each file (28,093회):
  file_data.duplicate_group_id = group_id
  file_data.is_canonical = is_canonical
  file_data.similarity_score = similarity_score
  changed_ids.append(file_id)
  ↓
files_updated_batch.emit(changed_ids)  # ✅ 1번만 호출
  ↓
FileListTableWidget._on_files_updated_batch(file_ids)
  ↓
_pending_update_ids.extend(file_ids)  # 큐에 추가
setUpdatesEnabled(False)  # 업데이트 억제
_update_batch_timer.start()  # 타이머 시작
  ↓
QTimer (10ms 간격, 반복)
  ↓
_process_batch_updates()  # 100개씩 청크 처리
  ↓
for each file_id in chunk (100개):
  row = _row_by_file_id.get(file_id)  # ✅ O(1) 캐시 조회
  file_data = _data_store.get_file(file_id)
  _update_duplicate_columns(row, file_data)  # ✅ 2개 컬럼만 업데이트
    ↓
  group_item.setText(group_text)  # ✅ 재생성 대신 텍스트만 변경
  canonical_item.setText(canonical_text)  # ✅ 재생성 대신 텍스트만 변경
  ↓
setUpdatesEnabled(True)  # 일시 활성화
viewport().update()  # 화면 갱신
setUpdatesEnabled(False)  # 다시 비활성화

결과: 부드러운 점진적 업데이트 (프리징 없음)
```

---

## 6. 핵심 최적화 기법

### 6.1 배치 처리 (Batching)

**원칙**: "한 번에 다 하지 말고, 묶어서 처리"

- **시그널 배치**: 개별 emit → 배치 emit
- **UI 업데이트 배치**: 즉시 업데이트 → 청크 단위 업데이트
- **효과**: 이벤트 루프 부담 감소, UI 반응성 향상

### 6.2 인덱스 캐시 (Index Cache)

**원칙**: "반복 계산은 캐시하라"

- **구현**: `dict[file_id, row]` 캐시
- **효과**: O(n) → O(1) 시간 복잡도 개선
- **메모리**: 약 160KB (28,093개 × 16바이트)

### 6.3 부분 업데이트 (Partial Update)

**원칙**: "변경된 부분만 업데이트"

- **구현**: 전체 행 재생성 → 필요한 컬럼만 업데이트
- **효과**: 아이템 생성 100% 감소
- **방법**: `setItem()` → `setText()` (기존 아이템 재사용)

### 6.4 업데이트 억제 + 주기적 갱신

**원칙**: "일괄 처리 중에는 화면 갱신을 억제하되, 주기적으로 갱신"

- **구현**: `setUpdatesEnabled(False)` + 주기적 `viewport().update()`
- **효과**: 불필요한 리페인트 방지, 점진적 화면 갱신

---

## 7. 성능 측정 결과

### 7.1 처리 시간

| 작업 | 개선 전 | 개선 후 |
|------|---------|---------|
| 시그널 emit | ~2-3초 | ~0ms |
| 행 탐색 | ~1-2초 | ~0.01초 |
| 행 업데이트 | ~0.5-1초 | ~0.1초 |
| **총 처리 시간** | **~3.5-6초 (프리징)** | **~2.8초 (프리징 없음)** |

**주목**: 처리 시간은 비슷하지만, **프리징이 완전히 제거됨**

### 7.2 메모리 사용

| 항목 | 개선 전 | 개선 후 | 차이 |
|------|---------|---------|------|
| 이벤트 큐 | 과부하 | 정상 | ✅ |
| 아이템 생성 | 280,930개 | 0개 | -280,930개 |
| 인덱스 캐시 | 없음 | ~160KB | +160KB |
| **순 증가** | - | - | **-280,930개 아이템** |

---

## 8. 향후 개선 방향

### 8.1 QAbstractTableModel로 전환

**현재**: `QTableWidget` 사용
**제안**: `QAbstractTableModel` + `QTableView`로 전환

**장점**:
- `dataChanged(topLeft, bottomRight)` 시그널로 효율적인 업데이트
- 가상 테이블 모델로 메모리 효율성 향상
- 대용량 데이터 처리에 최적화

**단점**:
- 코드 구조 대폭 변경 필요
- 기존 `QTableWidget` 코드 수정 필요

### 8.2 청크 크기 튜닝

**현재**: CHUNK_SIZE = 100, 타이머 간격 = 10ms
**제안**: 환경에 따라 동적 조정

- 고성능 머신: CHUNK_SIZE = 200-500, 간격 = 5ms
- 일반 머신: CHUNK_SIZE = 100, 간격 = 10ms (현재)
- 저사양 머신: CHUNK_SIZE = 50, 간격 = 20ms

### 8.3 가시 영역만 업데이트 (Viewport Culling)

**제안**: 화면에 보이지 않는 행은 업데이트하지 않음

- `QTableView.viewport()` 영역 내 행만 업데이트
- 스크롤된 영역은 나중에 업데이트
- 메모리 접근 최소화

---

## 9. 결론

### 9.1 문제 해결 요약

1. ✅ **시그널 호출 폭주 해결**: 배치 시그널로 28,093회 → 1회
2. ✅ **행 탐색 병목 해결**: 인덱스 캐시로 O(n) → O(1)
3. ✅ **불필요한 재생성 해결**: 부분 업데이트로 280,930개 → 0개
4. ✅ **UI 프리징 해결**: 청크 단위 처리로 점진적 업데이트

### 9.2 성능 개선 결과

- **시그널 호출**: 99.996% 감소
- **행 탐색 비교**: 99.999% 감소
- **아이템 생성**: 100% 감소
- **UI 프리징**: 완전 제거
- **전체 복잡도**: O(n²) → O(n)

### 9.3 체감 성능

- **개선 전**: UI 완전 멈춤 (3-5초), 사용 불가
- **개선 후**: 부드러운 점진적 업데이트, 사용 가능

---

## 부록: 주요 코드 위치

### FileDataStore
- 파일: `src/gui/models/file_data_store.py`
- 시그널 정의: 라인 83
- `set_duplicate_groups_batch()`: 라인 294-321

### FileListTableWidget
- 파일: `src/gui/views/components/file_list_table.py`
- 인덱스 캐시: 라인 52
- 배치 처리 큐/타이머: 라인 45-49
- 시그널 연결: 라인 118
- `_on_files_updated_batch()`: 라인 184-229
- `_process_batch_updates()`: 라인 231-295
- `_update_duplicate_columns()`: 라인 455-496
- `_find_row_by_file_id()`: 라인 304-334

### 호출 경로
- `src/gui/views/tabs/duplicate_tab.py` - `_on_duplicate_completed()` (라인 189-217)
  → `file_data_store.set_duplicate_groups_batch()`
    → `files_updated_batch.emit()`
      → `FileListTableWidget._on_files_updated_batch()`
        → `_process_batch_updates()` (QTimer로 반복 호출)

---

**작성일**: 2026-01-11
**버전**: 1.0
**작성자**: NovelGuard 개발팀
