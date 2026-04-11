## 📋 Decision Log (중요한 설계 결정 기록)

리팩토링 진행 중 내린 중요한 설계 결정들을 기록합니다. 나중에 "왜 이렇게 했지?"를 방지하기 위한 것입니다.

### Decision 1: Domain에서 Pydantic 사용 금지
- **날짜**: 2025-01-09
- **결정**: Domain 계층에서 Pydantic 사용을 절대 금지하고 `dataclasses` 사용
- **이유**: 
  - Domain이 특정 라이브러리에 강하게 결합되는 것 방지
  - 순수 비즈니스 로직만 포함
  - 테스트 시 외부 의존성 최소화
- **대안 고려**: Pydantic 사용 허용 (거부 - 결합도 증가)
- **영향**: 모든 Domain Entity/ValueObject는 `@dataclass` 사용

### Decision 2: UseCases vs Workflows 역할 구분
- **날짜**: 2025-01-09
- **결정**: 
  - `usecases/`: 단일 유스케이스, 원자적 (로직 포함)
  - `app/workflows/`: UseCase 조합만, 로직 추가 금지
- **이유**: 
  - 책임 분리 명확화
  - 로직이 두 군데로 분산되는 것 방지
  - UseCase 재사용성 향상
- **대안 고려**: Workflows에 로직 포함 허용 (거부 - 혼란 증가)
- **영향**: 모든 Workflow는 UseCase 호출만 수행

### Decision 3: Policy vs Service 역할 구분
- **날짜**: 2025-01-09
- **결정**: 
  - `domain/policies/`: 순수 규칙 함수 (stateless)
  - `domain/services/`: Policy 조합 및 복잡한 로직 (stateful 가능)
- **이유**: 
  - 순수 함수로 테스트 용이성 향상
  - 규칙과 조합 로직 분리
- **대안 고려**: Policy 없이 Service만 사용 (거부 - 테스트 어려움)
- **영향**: 버전 선택 로직은 Policy + Service 구조로 분리

### Decision 4: ID 기반 참조 강제
- **날짜**: 2025-01-09
- **결정**: Domain 객체 간 참조는 반드시 ID만 사용, 객체 참조 금지
- **이유**: 
  - 순환 의존성 방지
  - 불변성 보장 (ValueObject가 Entity 참조 시 불변성 깨짐)
  - 테스트 용이성
- **대안 고려**: 객체 참조 허용 (거부 - 순환 의존성 위험)
- **영향**: 모든 ValueObject는 Entity ID만 포함

### Decision 5: Ports 정의 우선순위
- **날짜**: 2025-01-09
- **결정**: Phase 1.15에서 Ports 정의 및 Infrastructure 마스킹을 FileRecord 분해 전에 수행
- **이유**: 
  - FileRecord 분해 시 이미 의존성 역전이 완료되어 더 깔끔한 구조
  - Domain이 Infrastructure에 의존하지 않도록 보장
- **대안 고려**: FileRecord 분해 후 Ports 정의 (거부 - 의존성 문제 발생)
- **영향**: Phase 1.2에서 FileRecord 분해 시 이미 Ports 사용 가능

### Decision 6: Golden Tests 도입
- **날짜**: 2025-01-09
- **결정**: Phase 0.5에서 Golden Tests(스냅샷 테스트) 및 벤치마크 기준선 고정
- **이유**: 
  - 회귀 방지
  - 리팩토링 중 동작 동등성 보장
  - 성능 회귀 감지
- **대안 고려**: 일반 테스트만 사용 (거부 - 회귀 감지 어려움)
- **영향**: 모든 Phase에서 Golden Tests 통과 필수

### Decision 7: Domain Service 로깅 선택적 원칙
- **날짜**: 2025-01-09
- **결정**: Domain Service는 **상태/판정에 필수적인 경우에만 ILogger를 주입**. "의사결정/판정/규칙" Service에는 로깅 금지.
- **이유**: 
  - Domain이 "사실상 Application-aware"가 되는 것 방지
  - 테스트에서 불필요한 mock 확산 방지
  - 순수 비즈니스 로직에 집중
- **대안 고려**: 모든 Domain Service에 logger 주입 (거부 - 과도한 의존성)
- **영향**: 
  - 로깅이 필요한 Service만 생성자에서 ILogger 받음
  - 판정 Service(VersionSelectionService 등)는 logger 없음
  - I/O Service(FileComparisonService 등)만 logger 사용

### Decision 8: Port 변경 시 Decision Log 필수
- **날짜**: 2025-01-09
- **결정**: Port 변경 시 **반드시 Decision Log에 기록**. Port는 "Domain 필요" 기준으로만 확장.
- **이유**: 
  - Port 비대화 방지 (확장 압력에 대한 가드)
  - Port 변경 추적 가능
  - 일관성 유지
- **대안 고려**: Port 변경 자유 (거부 - 비대화 위험)
- **영향**: 
  - 모든 Port 변경은 Decision Log에 기록
  - Phase별 리뷰 시점에만 Port 변경 허용

### Decision 9: Phase 병렬 실행 금지
- **날짜**: 2025-01-09
- **결정**: 리팩토링 Phase는 **순차 실행 전제**. Phase 병렬 실행 절대 금지.
- **이유**: 
  - 의존성 체인 관리 (각 Phase가 이전 Phase 구조에 의존)
  - 회귀 감지 (Golden Tests가 각 Phase 완료 시점 기준)
  - 리스크 격리 (문제 발생 시 이전 Phase로 롤백 가능)
- **대안 고려**: Phase 병렬 실행 (거부 - 의존성 충돌 위험)
- **영향**: 
  - 각 Phase는 이전 Phase 완료를 필수 전제로 함
  - "Phase 1.2 하면서 Phase 3 조금..." 같은 시도 금지 

---

