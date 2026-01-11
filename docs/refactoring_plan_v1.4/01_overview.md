# NovelGuard 리팩토링 계획서

> **프로젝트**: NovelGuard  
> **목적**: 코드 품질 개선 및 유지보수성 향상  
> **기준**: Clean Architecture + DDD 원칙  
> **프로토콜**: `protocols/development_protocol.md` 준수  
> **페르소나**: `persona/novelguard_developer.md` 적용


---

## 📝 문서 버전 관리

| 버전 | 날짜 | 변경 내용 | 작성자 | 검토자 |
|------|------|----------|--------|--------|
| 1.0 | 2025-01-09 | 초안 작성 | AI Assistant | - |
| 1.1 | 2025-01-09 | 리뷰 반영: Domain Pydantic 금지, 경계 규칙 명시, Phase 0.5/1.15 추가, Ports 정의, DoD/Freeze Zone/Decision Log 추가 | AI Assistant | 소프트웨어 아키텍트 |
| 1.2 | 2025-01-09 | 구조적 충돌 해소: app/ 중복 제거, ILogger domain/ports로 이동, DuplicateGroup ID-only 원칙, 스냅샷 정규화 규칙, 불변 Aggregate 운용 규칙, Ports 정의 룰 추가 | AI Assistant | 소프트웨어 아키텍트 |
| 1.3 | 2025-01-09 | 잔여 리스크 보정: Domain Service 로깅 선택적, Workflow 구조 테스트 강제, Port 변경 가드, Adapter 제거 기준, Entity 변경 규칙, 성능 게이트 실패 액션, Phase 병렬 실행 금지 | AI Assistant | 소프트웨어 아키텍트 |
| 1.4 | 2025-01-09 | 코드 현실 반영: P0 우선순위 수정 (gui/views/main_window.py가 실제 폭발 반경), file_record.py "God Model" 표현 제거, Workflow 구조 테스트 AST 기반으로 변경, Ports 테스트에 @runtime_checkable 명시 | AI Assistant | 소프트웨어 아키텍트 |

---

## 📋 Executive Summary

이 계획서는 프로젝트 전체 구조 분석을 기반으로 한 단계별 리팩토링 로드맵입니다.

### 우선순위 매트릭스

| 우선순위 | 대상 파일/모듈 | 리스크 | 리팩토링 필요도 | 핵심 사유 |
|---------|--------------|--------|---------------|----------|
| **P0 (즉시)** | `gui/views/main_window.py` | 🔴 매우 높음 | 🔴 매우 높음 | GUI가 domain/infra 직접 import, orchestration + 서비스 생성 + 로직 혼재 (2398줄, 60개 메서드) |
| **P0 (즉시)** | 루트 `main.py` 엔트리포인트 정리 | 🔴 매우 높음 | 🔴 매우 높음 | sys.path hack + gui 직접 호출 |
| **P0 (즉시)** | UseCase의 infra 직접 의존 제거 (Phase 1.15) | 🔴 매우 높음 | 🔴 매우 높음 | Ports 도입으로 의존성 역전 필요 |
| **P1 (상)** | `domain/models/file_record.py` (Pydantic 제거) | 🟠 높음 | 🟠 높음 | Domain Pydantic 금지 원칙에 따라 dataclass 전환 필요 (Phase 2에서 대량 마이그레이션과 함께) |
| **P1 (상)** | `domain/models/*` (집합) | 🟠 높음 | 🟠 높음 | 모델 간 순환 의존 가능성 |
| **P1 (상)** | `common/logging.py` | 🟠 높음 | 🟠 높음 | 전역 접근 + 정책 혼재 |
| **P2 (중)** | `common/errors.py` | 🟡 중간 | 🟡 중간 | 에러 분류 체계 미정형 |
| **P2 (중)** | `app/settings.py` | 🟡 중간 | 🟡 중간 | 런타임 설정 vs 상수 혼합 |
| **P3 (하)** | `common/types.py` | 🟢 낮음 | 🟢 낮음 | 안정적이나 확장 대비 정리 필요 |

---

## 🎯 리팩토링 목표

1. **테스트 가능성 향상**: 모든 비즈니스 로직을 순수 함수/클래스로 분리
2. **책임 분리**: Single Responsibility Principle 적용
3. **의존성 역전**: Domain 계층이 Infrastructure에 의존하지 않도록
4. **확장성 확보**: 새로운 기능 추가 시 기존 코드 영향 최소화
5. **유지보수성**: 코드 이해도 향상, 변경 범위 명확화

---

## 🚫 변경 금지 구역 (Freeze Zone)

리팩토링 중 **절대 변경하지 않을 영역**을 명확히 정의합니다. 이는 scope creep 방지와 기존 동작 보장을 위한 것입니다.

### 탐지 알고리즘 변경 금지
- 중복 탐지 알고리즘 로직 변경 금지 (정확도 변경 금지)
- 해시 계산 방식 변경 금지
- SimHash 파라미터 변경 금지
- **이유**: 리팩토링 목적은 구조 개선이며, 알고리즘 변경은 별도 이슈

### UI 기능 변경 금지
- 새로운 UI 기능 추가 금지
- 기존 UI 동작 변경 금지 (버그 수정 제외)
- **이유**: UI 변경은 기능 개발이며 리팩토링 범위 밖

### 출력 포맷 변경 금지
- 리포트 포맷 변경 금지
- API 응답 형식 변경 금지
- 데이터베이스 스키마 변경 금지 (마이그레이션 필요 시 별도 Phase)
- **이유**: 외부 인터페이스 변경은 호환성 문제 유발

### 예외 사항
- 버그 수정은 허용 (단, **버그 수정 PR은 리팩토링 PR과 분리** 필수)
- 성능 개선은 허용 (단, 동작 동등성 유지 필수)
- 필요한 경우 별도 브랜치/이슈로 분리

### Phase 병렬 실행 금지 (필수!)

**중요**: 이 리팩토링 계획은 **순차 실행 전제**입니다.

- ❌ **Phase 병렬 실행 절대 금지**
  - 예: "Phase 1.2 하면서 Phase 3 조금..." 같은 시도 금지
  - 각 Phase는 이전 Phase의 완료를 필수 전제로 함
- ✅ **순차 실행 원칙**:
  - Phase 0.5 완료 → Phase 1 시작
  - Phase 1 완료 → Phase 2 시작
  - Phase 2 완료 → Phase 3 시작
  - Phase 3 완료 → Phase 4 시작
- **이유**: 
  - 의존성 체인 관리 (각 Phase가 이전 Phase 구조에 의존)
  - 회귀 감지 (Golden Tests가 각 Phase 완료 시점 기준)
  - 리스크 격리 (문제 발생 시 이전 Phase로 롤백 가능)

---

