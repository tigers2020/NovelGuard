## ✅ Definition of Done (DoD) - 코드 구조 관점

각 Phase는 다음 **구조적 기준**을 모두 만족해야 완료로 간주됩니다:

### 1. 아키텍처 규칙 준수

- [ ] **Domain 계층**: 외부 프레임워크 import 금지 확인
  - [ ] `grep -r "from pydantic" domain/` 결과 없음
  - [ ] `grep -r "from PySide6" domain/` 결과 없음
  - [ ] `grep -r "import logging" domain/` 결과 없음 (표준 logging 모듈 직접 사용 금지)
  - [ ] `grep -r "from logging import" domain/` 결과 없음 (Ports만 사용: `from domain.ports.logger import ILogger`)
- [ ] **UseCase 계층**: gui/infra 직접 import 금지 확인
  - [ ] `grep -r "from gui" usecases/` 결과 없음
  - [ ] `grep -r "from infra" usecases/` 결과 없음 (Ports만 import)
- [ ] **Infra 계층**: domain/usecases의 Port만 구현 확인
  - [ ] 각 Infra 클래스가 Domain Port를 구현하는지 확인
- [ ] **GUI 계층**: usecase 인터페이스만 호출 확인
  - [ ] GUI가 `infra/`를 직접 import하지 않는지 확인
  - [ ] Bootstrap에서만 wiring 확인

### 2. 의존성 방향 검증

- [ ] 의존성 그래프 생성 및 검증
  - [ ] `pydeps src/ --show-deps --max-bacon=2` 실행
  - [ ] 순환 의존성 없음 확인
  - [ ] 의존성 방향이 올바른지 확인 (외부 → 내부)

### 3. ID 기반 참조 준수

- [ ] Domain ValueObject에서 Entity 객체 직접 참조 없음 확인
  - [ ] `grep -r "file: File" domain/value_objects/` 결과 없음
  - [ ] ID만 사용 (`file_id: int`) 확인

### 4. 기능 동등성

- [ ] Golden Tests 통과 (Phase 0.5에서 생성한 스냅샷 테스트)
- [ ] 기존 기능과 동일하게 동작 확인
- [ ] 통합 테스트 통과

### 5. 성능 기준 (구체화)

성능 벤치마크 기준선 대비 다음 항목을 모두 ±5% 이내 유지:

- [ ] **스캔 처리량**: `files/sec` (1000개 파일 기준)
  - 측정: `benchmark_scan_throughput.py` 실행
  - 기준: `benchmark_baseline.json`의 `scan_throughput.files_per_sec`
  - 허용: 기준 ±5%
- [ ] **중복 탐지 처리량**: `groups/sec` (100개 그룹 기준)
  - 측정: `benchmark_duplicate_detection.py` 실행
  - 기준: `benchmark_baseline.json`의 `duplicate_detection.groups_per_sec`
  - 허용: 기준 ±5%
- [ ] **메모리 사용량**: peak RSS (MB)
  - 측정: `psutil` 또는 `memory_profiler` 사용
  - 기준: `benchmark_baseline.json`의 `memory_peak_rss_mb`
  - 허용: 기준 ±5% (단, 증가는 우려 대상)
  - **게이트 룰**: ±5% 초과 시 경고 (soft gate), ±10% 초과 시 실패 (hard gate)
  - [ ] **실패 후 액션 (v1.3 규칙)**:
    - **로컬 환경**: ±10% 초과 시 경고만 (개발자에게 알림, 작업 계속 가능)
    - **CI 환경**: ±10% 초과 시 **PR block** (자동 병합 차단)
    - **실패 시 조치**:
      1. 성능 회귀 원인 분석 (프로파일링 실행)
      2. 이슈 생성 (자동 또는 수동)
      3. 이전 Phase로 롤백 검토 (필요 시)
      4. 성능 최적화 또는 Phase 재진행
- [ ] **CPU 시간**: process time (초)
  - 측정: `time.process_time()` 사용
  - 기준: `benchmark_baseline.json`의 `cpu_time_seconds`
  - 허용: 기준 ±5%
  - **게이트 룰**: 
    - **로컬 환경**: ±5% 초과 시 경고 (soft gate), ±10% 초과 시 경고만 (hard gate 없음)
    - **CI 환경**: ±5% 초과 시 경고만 (soft gate, 성능 편차 고려), ±10% 초과 시 **PR block** (hard gate)
    - **이유**: CI 환경의 시스템 부하/리소스 편차를 고려하여 더 넓은 허용 범위 적용
  - [ ] **실패 후 액션 (v1.3 규칙)**:
    - **로컬 환경**: ±10% 초과 시 경고만 (개발자에게 알림, 작업 계속 가능)
    - **CI 환경**: ±10% 초과 시 **PR block** (자동 병합 차단)
    - **실패 시 조치**:
      1. 성능 회귀 원인 분석 (프로파일링 실행)
      2. 이슈 생성 (자동 또는 수동)
      3. 이전 Phase로 롤백 검토 (필요 시)
      4. 성능 최적화 또는 Phase 재진행

### 6. 테스트 기준

- [ ] 모든 단위/통합 테스트 통과
- [ ] 코드 커버리지: 80% 이상 유지 또는 향상
- [ ] Golden Tests 통과 (회귀 없음)
- [ ] 성능 벤치마크 통과 (±5% 이내)

### 7. 코드 품질

- [ ] 린터 통과: `ruff check src/` (경고 없음)
- [ ] 포매터 적용: `ruff format src/`
- [ ] 타입 체크 통과: `mypy src/` (에러 없음)
- [ ] Docstring 작성 (모든 공개 함수/클래스)

### 8. 문서 업데이트

- [ ] 관련 문서 업데이트 완료
  - [ ] README.md
  - [ ] 프로토콜 문서 (`protocols/development_protocol.md`)
  - [ ] 아키텍처 다이어그램 (필요 시)
- [ ] Decision Log 업데이트 (중요한 설계 결정 기록)

### 9. 리뷰 완료

- [ ] (팀이 있는 경우) 코드 리뷰 완료
- [ ] 모든 피드백 반영

---

