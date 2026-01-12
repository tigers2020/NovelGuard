# NovelGuard 프로젝트 TODO 리스트

> 생성일: 2026-01-11
> 업데이트: 2026-01-11 (레거시/만료 항목 정리)
> **실제 TODO 항목**: 8개 (레거시 제외)

---

## ⚠️ 레거시/만료 항목 (제거됨)

다음 항목들은 코드베이스 분석 결과 **실제로 사용되지 않는 Stub ViewModels**에 포함되어 있어 제거되었습니다:

- `src/gui/view_models/_stubs/logs_view_model.py` - **레거시** (LogsTab은 InMemoryLogSink를 직접 사용)
- `src/gui/view_models/_stubs/settings_view_model.py` - **레거시** (SettingsTab은 ViewModel 없이 직접 구현)
- `src/gui/view_models/_stubs/small_file_view_model.py` - **레거시** (SmallFileTab에서 미사용)
- `src/gui/view_models/_stubs/undo_view_model.py` - **레거시** (UndoTab에서 미사용)
- `src/gui/view_models/_stubs/integrity_view_model.py` - **레거시** (IntegrityTab에서 미사용)
- `src/gui/view_models/_stubs/encoding_view_model.py` - **레거시** (EncodingTab에서 미사용)
- `src/gui/view_models/scan_view_model.py` Line 68 - **불필요** (load_data() 메서드는 실제로 사용되지 않음)

**참고**: `_stubs` 폴더의 ViewModel들은 현재 어떤 View에서도 사용되지 않습니다. 이들은 향후 리팩토링 시 참고용으로 남아있지만, 실제 구현 우선순위에서는 제외됩니다.

---

## 1. GUI 기능 구현

### 1.1 Logs Tab (로그 탭)
- **파일**: `src/gui/views/tabs/logs_tab.py`
  - [ ] Line 243: 실제 로그 내보내기 구현 (파일 다이얼로그)

**우선순위**: 중간  
**설명**: LogsTab은 InMemoryLogSink를 직접 사용하며 로그 표시 기능은 구현되어 있습니다. 다만 로그를 파일로 내보내는 기능이 미구현 상태입니다.

---

### 1.2 Settings Tab (설정 탭)
- **파일**: `src/gui/views/tabs/settings_tab.py`
  - [ ] Line 231: 실제 설정 저장 로직 구현 (QSettings 사용)

**우선순위**: 높음  
**설명**: SettingsTab은 ViewModel 없이 직접 구현되어 있습니다. 설정 UI는 완성되었으나, 실제 저장/로드 로직이 미구현입니다. QSettings를 사용하여 구현할 예정입니다.

---

### 1.3 Small File Tab (작은 파일 탭)
- **파일**: `src/gui/views/tabs/small_file_tab.py`
  - [ ] Line 140: 결과 카드 그리드 구현

**우선순위**: 낮음 (v1.5 기능 예정)

---

### 1.4 Undo Tab (실행 취소 탭)
- **파일**: `src/gui/views/tabs/undo_tab.py`
  - [ ] Line 101: 실행 기록 카드 그리드 구현

**우선순위**: 높음 (안전성 기능 - v1.5)

---

## 2. 에러 처리 및 사용자 피드백

### 2.1 에러 메시지 표시
- **파일**: `src/gui/views/main_window.py`
  - [ ] Line 329: 오류 메시지를 사용자에게 표시 (로그 탭 등)

- **파일**: `src/gui/views/tabs/scan_tab.py`
  - [ ] Line 342: 오류 메시지 표시 (로그 탭 등)
  - [ ] Line 360: 에러 메시지 표시 (폴더 선택 안 됨 시)

**우선순위**: 높음 (사용자 경험 개선)  
**설명**: 현재는 `print()` 또는 UI 텍스트로만 표시하고 있습니다. 사용자에게 명확한 에러 메시지 다이얼로그나 로그 탭으로 전환하는 기능이 필요합니다.

---

## 3. Phase 2 / v2 기능 (미래 구현)

### 3.1 스캐너 개선
- **파일**: `src/infrastructure/fs/scanner.py`
  - [ ] Line 113: 순환 링크 방지 (Phase 2에서 추가)

**우선순위**: 낮음 (Phase 2)

---

### 3.2 스캔 결과 개선
- **파일**: `src/application/use_cases/scan_folder.py`
  - [ ] Line 126: warnings_count 구현 (Phase 2에서 구현)

**우선순위**: 낮음 (Phase 2)

---

### 3.3 중복 탐지 고급 기능 (v2)
- **파일**: `src/gui/workers/duplicate_detection_worker.py`
  - [ ] Line 471: enable_exact/enable_near 플래그 처리 (IHashService 필요)
  - [ ] Line 486: ExactDuplicateDetector/NearDuplicateDetector 구현

**우선순위**: 낮음 (v2 기능)

---

## 우선순위별 요약

### 🔴 높음 (즉시 구현 권장) - 4개
1. Settings Tab - 설정 저장 로직 (1개)
2. Undo Tab - 실행 기록 카드 그리드 (1개)
3. 에러 메시지 표시 개선 (3개)

### 🟡 중간 (단기간 내 구현) - 1개
1. Logs Tab - 로그 내보내기 (1개)

### 🟢 낮음 (Phase 2 / v2 기능) - 7개
1. Small File Tab (1개)
2. Phase 2 기능 (2개)
3. v2 기능 (2개)

**총 실제 TODO 항목: 8개**

---

## 참고 사항

1. **Stub ViewModels**: `_stubs` 폴더의 ViewModel들은 현재 어떤 View에서도 사용되지 않습니다. 레거시 코드로 간주되며, 향후 필요 시 참고용으로만 활용됩니다.

2. **Phase 2 기능**: 개발 프로토콜에 따르면 v1.5 이후에 구현 예정입니다.

3. **v2 기능**: SimHash 기반 유사본 탐지 등 고급 기능은 v2에서 구현 예정입니다.

---

## 다음 단계 제안

1. **즉시 작업**: Settings Tab 설정 저장 로직 (QSettings 활용)
2. **단기 작업**: 에러 메시지 표시 개선 (사용자 피드백 개선)
3. **중기 작업**: Undo Tab 실행 기록 카드 그리드 (안전성 기능)
4. **장기 작업**: Logs Tab 내보내기 및 Phase 2/v2 기능
