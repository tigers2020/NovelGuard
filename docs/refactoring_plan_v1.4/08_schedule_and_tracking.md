## 📊 전체 일정 요약

| Phase | 내용 | 예상 소요 시간 | 우선순위 |
|-------|------|--------------|---------|
| **Phase 0** | 기반 작업 | 11시간 | P0 (선수 작업) |
| Phase 0.5 | Golden Tests 및 벤치마크 | 11시간 | |
| **Phase 1** | 폭발 반경 제거 | 40시간 | P0 (즉시) |
| Phase 1.1 | GUI Orchestration 제거 및 Bootstrap 분리 | 8시간 | **v1.4: 목적 변경 (main.py → main_window.py)** |
| Phase 1.15 | Ports 정의 및 Infrastructure 마스킹 | 11시간 | **신규 추가** |
| Phase 1.2 | FileRecord Pydantic 제거 및 구조 정리 | 18시간 | **v1.4: 목적 변경 (God Model → Pydantic 제거)** |
| Phase 1.3 | Phase 1 검증 | 3시간 | |
| **Phase 2** | 도메인 정제 | 38시간 | P1 (상) |
| Phase 2.1 | Domain Models 재분류 | 17시간 | |
| Phase 2.2 | 로직 Service 이동 | 18시간 | |
| Phase 2.3 | Phase 2 검증 | 3시간 | |
| **Phase 3** | 인프라 정리 | 31시간 | P1-P2 (상-중) |
| Phase 3.1 | Logging 계층화 | 9시간 | |
| Phase 3.2 | Error 계층화 | 9시간 | |
| Phase 3.3 | Settings 분리 | 10시간 | |
| Phase 3.4 | Phase 3 검증 | 3시간 | |
| **Phase 4** | 정리 및 최적화 | 12시간 | P3 (하) |
| Phase 4.1 | Types 정리 | 3시간 | |
| Phase 4.2 | 아키텍처 검증 | 4시간 | |
| Phase 4.3 | 최종 검증 | 5시간 | |
| **총계** | | **132시간** | (+22시간) |

> **참고**: 예상 소요 시간은 개발자 1명 기준이며, 실제로는 리뷰, 테스트, 버그 수정 시간을 고려하여 1.5~2배 여유를 두는 것을 권장합니다.

---

## 🚀 실행 전 체크리스트

리팩토링을 시작하기 전에 다음 사항을 확인하세요:

### 환경 준비
- [ ] Git 저장소 백업 (원격 저장소에 푸시)
- [ ] 현재 코드베이스에 모든 테스트 통과 확인
- [ ] 성능 벤치마크 기준선 측정 및 기록
- [ ] 코드 커버리지 기준선 측정 및 기록

### 브랜치 전략
- [ ] `refactor/phase1-bootstrap` 브랜치 생성
- [ ] 각 Phase별로 별도 브랜치 사용 계획 수립
- [ ] 메인 브랜치와의 병합 전략 수립

### 테스트 전략
- [ ] 각 Phase 완료 시점에 통합 테스트 실행 계획
- [ ] 수동 테스트 시나리오 문서화
- [ ] 회귀 테스트 계획 수립

### 문서화
- [ ] 리팩토링 진행 상황 추적 방법 (이슈 트래커, 프로젝트 보드 등)
- [ ] 변경 사항 문서화 템플릿 준비
- [ ] 팀 공유 일정 수립

---

## 📝 진행 상황 추적

각 Phase의 진행 상황을 추적하기 위해 다음 템플릿을 사용하세요:

```markdown
## Phase X.X: [제목]

**시작일**: YYYY-MM-DD  
**완료일**: (진행 중)  
**상태**: 🟡 진행 중 / 🟢 완료 / 🔴 블로킹

### 완료된 작업
- [x] 작업 1
- [x] 작업 2

### 진행 중인 작업
- [ ] 작업 3 (진행률: 50%)
- [ ] 작업 4 (진행률: 20%)

### 블로킹 이슈
- 이슈 1: 설명 및 해결 방안

### 다음 단계
- 작업 5
- 작업 6
```

---

## 🎓 학습 자료 및 참고 문서

### 내부 문서
- `protocols/development_protocol.md`: 개발 프로토콜
- `persona/novelguard_developer.md`: 개발자 페르소나
- `NovelGuard_실행_리포트.md`: 현재 구조 분석

### 외부 참고 자료
- Clean Architecture (Robert C. Martin)
- Domain-Driven Design (Eric Evans)
- Refactoring (Martin Fowler)
- Python 타입 힌팅 가이드

---

