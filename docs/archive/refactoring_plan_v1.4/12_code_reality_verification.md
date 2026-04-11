## 📌 코드 현실 기반 검증 결과 (v1.4)

### 실제 코드 분석 기준 검증 완료

#### P0 우선순위 재조정 완료
- ✅ **`gui/views/main_window.py`**: 실제 폭발 반경 확인 (2398줄, 60개 메서드)
  - GUI가 `domain/`, `infra/`, `common/logging` 직접 import 확인
  - orchestration + 서비스 생성 + 로직 혼재 확인
  - **11개 GUI 파일**에서 domain/infra 직접 import 확인
- ✅ **`app/main.py`**: 실제로 매우 단순 (36줄) → P0에서 제외, 정리 대상으로 재분류
  - sys.path hack 문제만 남아 있음
- ✅ **UseCase infra 직접 import**: **4개 파일**에서 확인
  - `scan_files.py`, `check_integrity.py`, `find_duplicates.py`, `build_action_plan.py`
  - Phase 1.15의 필요성 재확인

#### Phase 목적 재정의 완료
- ✅ **Phase 1.1**: "`app/main.py` 슬림화" → "`gui/views/main_window.py` orchestration 제거"로 변경
- ✅ **Phase 1.2**: "God Model 해소" → "Pydantic 제거 및 구조 정리"로 변경
  - 실제 `file_record.py`는 70줄로 작고 메서드도 거의 없음 (property 1개만)
  - "God Model" 표현 부적절 → Pydantic 의존성 제거가 주요 목표

#### 기술적 개선 완료
- ✅ **Workflow 구조 테스트**: 문자열 검사 → **AST 기반 검증**으로 변경
  - 주석/문자열/포맷팅에 의한 오탐 방지
  - `ast.If`, `ast.For`, `ast.While`, `ast.ListComp` 등 명시적 검사
- ✅ **Ports 테스트**: `@runtime_checkable` 데코레이터 명시 (필수!)
  - `isinstance(impl, IPort)` 검사가 동작하려면 반드시 필요
  - 모든 Port 정의에 추가 예시 포함
- ✅ **성능 게이트**: CI 환경 편차 고려사항 추가
  - CI 성능 측정은 "경향성 감지(경고)" 중심
  - hard gate는 전용 runner/고정 리소스 환경에서만 강하게 설정 옵션 추가

### 실제 코드 기반 체크리스트 (추가 확인 필요)

원하면, 현재 코드 기준으로 아래를 **정확한 리스트**로 뽑아드릴 수 있습니다:

- ✅ `gui/`에서 **domain/infra 직접 import**하는 파일 목록 (11개 파일 확인됨)
- ✅ `usecases/`에서 **infra 직접 import**하는 라인 목록 (4개 파일 확인됨 - Phase 1.15 전환 대상)
- ✅ `domain/models/`에서 **Pydantic 사용 모델 목록** (`file_record.py` 확인됨 - Phase 2에서 대량 마이그레이션 필요)
- ✅ 실제 코드 복잡도 분석 (메서드 수/라인 수/순환 의존 위험도 기반)

**참고**: 다른 Domain 모델들(`duplicate_group`, `candidate_edge`, `evidence`, `integrity_issue`)은 모두 dataclass 사용으로 확인됨. Pydantic 제거 대상은 `file_record.py`가 주요 대상이며, Phase 2에서 대량 마이그레이션과 함께 진행하는 것이 현실적입니다.

---

