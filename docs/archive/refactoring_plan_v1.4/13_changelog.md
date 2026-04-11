## 📌 v1.4 주요 변경사항 (코드 현실 반영 및 정확성 향상)

### 코드 기반 검증 반영
- ✅ **P0 우선순위 수정**: `app/main.py`는 실제로 36줄로 매우 단순 → P0에서 제외
  - **실제 폭발 반경**: `gui/views/main_window.py` (2398줄, 60개 메서드) → P0 타겟으로 변경
  - `gui/views/main_window.py`가 domain/infra 직접 import하는 문제 확인 (11개 GUI 파일에서 확인)
- ✅ **Phase 1.1 재정의**: `app/main.py` 슬림화 → `gui/views/main_window.py` orchestration 제거로 변경
  - Bootstrap에서 의존성 주입 (GUI 직접 생성 금지)
  - sys.path hack 제거
- ✅ **Phase 1.2 목적 재정의**: "God Model 해소" → "Pydantic 제거 및 구조 정리"로 변경
  - 실제 `file_record.py`는 70줄로 작고 메서드도 거의 없음 (property 1개만)
  - "God Model" 표현 부적절 → Pydantic 의존성 제거가 주요 목표
  - Phase 2에서 다른 Domain 모델들과 함께 대량 마이그레이션으로 재조정
- ✅ **Workflow 구조 테스트 개선**: 문자열 검사(`inspect.getsource()`) → **AST 기반 검증**으로 변경
  - 주석/문자열/포맷팅에 의한 오탐 방지
  - 파이썬 문법 변화에도 더 안정적
  - `ast.If`, `ast.For`, `ast.While`, `ast.ListComp` 등 금지 노드 명시적 검사
- ✅ **Ports 테스트 예시 수정**: `@runtime_checkable` 데코레이터 명시 (필수!)
  - `isinstance(impl, IPort)` 검사가 동작하려면 반드시 필요
  - 모든 Port 정의에 `@runtime_checkable` 추가 예시 포함
- ✅ **UseCase infra 직접 import 확인**: 4개 파일에서 확인 (`scan_files.py`, `check_integrity.py`, `find_duplicates.py`, `build_action_plan.py`)
  - Phase 1.15의 필요성 재확인 및 우선순위 강화

### 우선순위 매트릭스 재조정
- **P0 (즉시)**: `gui/views/main_window.py` (실제 폭발 반경)
- **P0 (즉시)**: 루트 `main.py` 엔트리포인트 정리 (sys.path hack 제거)
- **P0 (즉시)**: UseCase의 infra 직접 의존 제거 (Phase 1.15)
- **P1 (상)**: `domain/models/file_record.py` Pydantic 제거 (Phase 2에서 대량 마이그레이션과 함께)

---

## 📌 v1.3 주요 변경사항 (잔여 리스크 보정 및 최종 규칙 고정)

### R1-R7 잔여 리스크 보정
- ✅ **R1**: Domain Service 로깅 선택적 원칙 고정 (상태/판정에 필수적인 경우에만 주입)
- ✅ **R2**: Workflow 구조 테스트 강제 (자동화된 구조 검증 테스트 추가)
- ✅ **R3**: Port 변경 가드 규칙 추가 (Decision Log 필수, Domain 필요 기준)
- ✅ **R4**: Adapter 제거 기준 및 시점 명시 (Phase 2.3 완료 시점)
- ✅ **R5**: Entity 변경 가능성 규칙 명확화 (허용/금지 범위 구체화)
- ✅ **R6**: 성능 게이트 실패 후 액션 명시 (로컬/CI 환경별 차이, PR block 규칙)
- ✅ **R7**: Phase 병렬 실행 금지 규칙 추가 (순차 실행 전제 명문화)

### 최종 규칙 5개 고정
- ✅ **규칙 1**: Workflow 구조 테스트 강제 (**AST 기반 자동 검증**, v1.4 업데이트: 문자열 검사 → AST 검사)
- ✅ **규칙 2**: Domain Service 로깅 최소화 원칙 (의사결정 Service는 로깅 금지)
- ✅ **규칙 3**: Port 변경 시 Decision Log 필수 (Port 비대화 방지)
- ✅ **규칙 4**: Adapter 제거 Phase 명시 (Phase 2.3 완료 시점)
- ✅ **규칙 5**: Phase 병렬 실행 금지 (순차 실행 전제)

### Decision Log 추가
- ✅ Decision 7: Domain Service 로깅 선택적 원칙
- ✅ Decision 8: Port 변경 시 Decision Log 필수
- ✅ Decision 9: Phase 병렬 실행 금지

---

## 📌 v1.2 주요 변경사항 (구조적 충돌 해소)

### P0 이슈 해소 (즉시 수정)
- ✅ 타겟 아키텍처 트리에서 `app/` 중복 제거 (182-189줄 삭제)
- ✅ `ILogger` 인터페이스를 `domain/ports/logger.py`로 이동 (원칙 일치)
- ✅ `DuplicateGroup`에 `File` 엔티티 리스트 포함 → `file_ids: list[int]`만 포함으로 변경 (ID-only 원칙 일치)

### P1 이슈 해소
- ✅ Golden Snapshot 정규화 규칙 추가 (순서/경로/비결정 필드/숫자 반올림)
- ✅ 불변 Aggregate 운용 규칙 추가 (`with_*()` 함수형 업데이트 패턴)

### 소규모 정리
- ✅ Ports 위치 명확화: `domain/ports/`로 통일 (혼란 방지)
- ✅ Ports 정의 룰 추가: 기존 구현체 API를 스캔하여 추출 (확정값 박지 않음)
- ✅ Freeze Zone에 버그 수정 PR 분리 규칙 추가
- ✅ DoD에 성능 게이트 룰 구체화 (로컬/CI 환경별)
- ✅ Domain 계층의 logging import 금지 규칙 명확화 (Ports만 사용)

---

## 📌 v1.1 주요 변경사항 (리뷰 반영)

### 구조적 위험 해소
- ✅ Domain에서 Pydantic 사용 금지 명시 (핵심 설계 원칙 추가)
- ✅ 경계 규칙 명문화 (GUI ↔ UseCase ↔ Domain ↔ Infra)
- ✅ ID 기반 참조 원칙 강화 (순환 의존성 방지)
- ✅ Ports 정의 단계 추가 (Phase 1.15)

### 실행 가능성 향상
- ✅ Phase 0.5 추가 (Golden Tests 및 벤치마크 기준선)
- ✅ workflows vs usecases 역할 구분 명확화
- ✅ Policy vs Service 역할 정리
- ✅ 성능 측정 기준 구체화 (4개 항목)

### 통제 항목 추가
- ✅ Freeze Zone 섹션 추가 (변경 금지 구역 정의)
- ✅ Definition of Done (DoD) 구체화 (9개 항목)
- ✅ Decision Log 섹션 추가 (중요한 설계 결정 기록)
- ✅ 단일 엔트리포인트 원칙 명시

### 문서 품질 개선
- ✅ 문서 버전 관리 섹션 추가
- ✅ 타겟 아키텍처에 ports 추가
- ✅ 예시 코드에 경계 규칙 반영
