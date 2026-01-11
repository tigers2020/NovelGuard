# NovelGuard 리팩토링 계획서 (분할본 v1.4)

이 폴더는 루트의 `리팩토링_계획서.md`를 **실행 순서대로 따라가기 쉽도록** 섹션/Phase 단위로 분리한 문서 모음입니다.

> **프로토콜/페르소나 준수**
> - 개발 절차/품질 기준: `../../protocols/development_protocol.md`
> - 작업 태도/안전 원칙: `../../persona/novelguard_developer.md`

---

## 빠른 시작 (권장 진행 순서)

1) **개요/우선순위/Freeze Zone**
- `01_overview.md`

2) **아키텍처 원칙/경계 규칙/타겟 구조**
- `02_architecture_and_principles.md`

3) **Phase 0 (Golden Tests/벤치 기준선)**
- `03_phase0_foundation.md`

4) **Phase 1 (P0: 폭발 반경 제거)**
- `04_phase1_p0_blast_radius.md`

5) **Phase 2 (Domain 정제)**
- `05_phase2_domain_refinement.md`

6) **Phase 3 (Infra 정리)**
- `06_phase3_infra_stabilization.md`

7) **Phase 4 (정리/최적화)**
- `07_phase4_cleanup.md`

8) **일정/진행 템플릿/사전 체크**
- `08_schedule_and_tracking.md`

9) **Definition of Done (DoD)**
- `09_definition_of_done.md`

10) **Decision Log**
- `10_decision_log.md`

11) **반복/개선, 팁**
- `11_repeat_and_tips.md`

12) **코드 현실 기반 검증 결과 (v1.4)**
- `12_code_reality_verification.md`

13) **변경 이력 (v1.4~v1.1)**
- `13_changelog.md`

---

## “오늘 할 일” 체크리스트 (Phase 단위)

- [ ] Phase 0.5 완료 전까지는 **구조 변경/이동 최소화** (Golden Tests가 안전망)
- [ ] Phase 1은 **GUI 의존성 절단 + UseCase의 infra 직접 의존 제거(Ports)** 를 최우선으로 진행
- [ ] 각 Phase 종료 시 `09_definition_of_done.md` 기준으로 통과 여부 체크

---

## 원본과의 관계

- 이 분할본은 **원본 `리팩토링_계획서.md` 내용을 기준으로 생성**되었습니다.
- 내용 충돌/최신화가 필요하면 **원본을 먼저 수정**한 뒤, 분할본도 동일 기준으로 갱신하는 것을 권장합니다.

