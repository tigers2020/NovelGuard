## 🏗️ Phase 2: 도메인 정제 (P1 - 구조 안정화)

> **목표**: Domain 계층의 모델들을 의미 단위로 재분류하고, 비교/판단 로직을 Service로 이동

### Phase 2.1: Domain Models 재분류

#### 목표
- `domain/models/` 폴더의 모든 모델을 Entity, ValueObject, Aggregate로 분류
- 모델 간 암묵적 의존성 제거
- 명확한 계층 구조 확립

#### 작업 체크리스트

##### Step 2.1.1: 모델 분석 및 분류 계획
- [ ] `domain/models/` 폴더의 모든 파일 목록 작성
  - [ ] `action_plan.py`
  - [ ] `candidate_edge.py`
  - [ ] `duplicate_group.py`
  - [ ] `evidence.py`
  - [ ] `file_feature.py`
  - [ ] `file_meta.py`
  - [ ] `preview_stats.py`
  - [ ] `integrity_issue.py`
- [ ] 각 모델의 책임 분석
  - [ ] 상태만 가지고 있는가? → Entity/ValueObject 후보
  - [ ] 비즈니스 로직을 가지고 있는가? → Service로 이동 필요
  - [ ] 다른 모델을 참조하는가? → Aggregate 후보
- [ ] 분류 계획 문서 작성 (`docs/refactoring/model_classification.md`)
- [ ] 팀 리뷰 (필요시)

##### Step 2.1.2: DuplicateGroup → Aggregate 분리 (ID 기반 참조 강제!)
- [ ] `domain/aggregates/` 디렉토리 생성
- [ ] `domain/aggregates/duplicate_group.py` 생성
  - [ ] `DuplicateGroup` Aggregate 정의 (**dataclass, 불변**)
  - [ ] **`File` 엔티티 리스트 포함 금지!** `file_ids: list[int]`만 포함 (ID 기반 참조)
  - [ ] `CandidateEdge` ValueObject 포함 (이미 ID 기반 참조)
  - [ ] `Evidence` ValueObject 포함 (이미 ID 기반 참조)
  - [ ] 불변성 보장 (`@dataclass(frozen=True)`)
  - [ ] **함수형 업데이트 패턴** 구현:
    ```python
    @dataclass(frozen=True)
    class DuplicateGroup:
        file_ids: tuple[int, ...]  # 불변 튜플
        edges: tuple[CandidateEdge, ...]
        evidence: tuple[Evidence, ...]
        
        def with_added_edge(self, edge: CandidateEdge) -> "DuplicateGroup":
            """새 엣지를 추가한 새 인스턴스 반환 (불변성 유지)."""
            return DuplicateGroup(
                file_ids=self.file_ids,
                edges=self.edges + (edge,),
                evidence=self.evidence
            )
    ```
  - [ ] 필요한 File 객체는 Service/Repo lookup으로 가져오기:
    ```python
    class DuplicateGroupService:
        def get_files(self, group: DuplicateGroup, repo: IFileRepository) -> list[File]:
            """File 객체를 필요 시에만 lookup."""
            return [repo.find_by_id(file_id) for file_id in group.file_ids]
    ```
- [ ] 기존 `duplicate_group.py`에서 마이그레이션
- [ ] 관련 UseCase 업데이트 (Service lookup 사용)
- [ ] File 객체 직접 참조가 아닌 ID만 사용하는지 검증 (`grep -r "files: list\[File\]" domain/aggregates/`)
- [ ] 단위 테스트 작성 (`tests/domain/aggregates/test_duplicate_group.py`)
- [ ] 통합 테스트로 동작 확인

##### Step 2.1.3: CandidateEdge, Evidence → ValueObject 분리 (ID 기반 참조 강제!)
- [ ] `domain/value_objects/candidate_edge.py` 생성
  - [ ] `CandidateEdge` ValueObject 정의 (**dataclass, 불변**)
  - [ ] **두 `File` 엔티티 참조 금지!** `file_id_1: int`, `file_id_2: int`만 저장 (ID 기반)
  - [ ] 비교 결과 값 포함 (`similarity: float` 등)
  - [ ] `@dataclass(frozen=True)` 데코레이터 사용
- [ ] `domain/value_objects/evidence.py` 생성
  - [ ] `Evidence` ValueObject 정의 (**dataclass, 불변**)
  - [ ] 증거 타입, 신뢰도, 데이터 포함
  - [ ] `@dataclass(frozen=True)` 데코레이터 사용
  - [ ] **File 객체 참조 금지!** 필요 시 `file_id: int`만 저장
- [ ] 기존 모델에서 마이그레이션
- [ ] 객체 참조가 아닌 ID만 사용하는지 검증 (`grep -r "file: File" domain/value_objects/`)
- [ ] 단위 테스트 작성
- [ ] 통합 테스트로 동작 확인

##### Step 2.1.4: FileFeature, FileMeta → ValueObject 통합
- [ ] `FileFeature`와 `FileMetadata` 통합 검토
  - [ ] 중복 필드 제거
  - [ ] 단일 `FileMetadata` ValueObject로 통합
- [ ] `domain/value_objects/file_metadata.py` 업데이트
  - [ ] 모든 메타데이터 포함
  - [ ] 검증 로직 추가
- [ ] 기존 코드 마이그레이션
- [ ] 단위 테스트 작성
- [ ] 통합 테스트로 동작 확인

##### Step 2.1.5: PreviewStats → ValueObject 분리
- [ ] `domain/value_objects/preview_stats.py` 생성
  - [ ] `PreviewStats` ValueObject 정의 (불변)
  - [ ] 집계 결과만 포함 (계산 로직 제외)
- [ ] 계산 로직은 UseCase나 Service로 이동
- [ ] 기존 코드 마이그레이션
- [ ] 단위 테스트 작성
- [ ] 통합 테스트로 동작 확인

##### Step 2.1.6: ActionPlan → Aggregate 또는 Service 검토
- [ ] `ActionPlan`의 책임 분석
  - [ ] 상태만 있는가? → Aggregate
  - [ ] 생성 로직이 복잡한가? → Service
- [ ] 결정에 따라 적절한 위치로 이동
- [ ] 기존 코드 마이그레이션
- [ ] 단위 테스트 작성
- [ ] 통합 테스트로 동작 확인

##### Step 2.1.7: IntegrityIssue → Entity 분리 (ID 기반 참조 강제!)
- [ ] `domain/entities/integrity_issue.py` 생성
  - [ ] `IntegrityIssue` Entity 정의 (**dataclass, Pydantic 금지!**)
  - [ ] 식별자(`issue_id: int`) 포함
  - [ ] **`File` 엔티티 참조 금지!** `file_id: int`만 저장 (ID 기반 참조)
  - [ ] 이슈 타입, 심각도, 메시지 포함
  - [ ] 필요 시 `@dataclass` 사용 (불변성은 선택적, Entity는 변경 가능할 수 있음)
- [ ] 기존 모델에서 마이그레이션
- [ ] File 객체 직접 참조가 아닌 ID만 사용하는지 검증
- [ ] 단위 테스트 작성
- [ ] 통합 테스트로 동작 확인

##### Step 2.1.8: 레거시 models 폴더 정리
- [ ] 모든 모델이 새 위치로 이동되었는지 확인
- [ ] `domain/models/` 폴더의 파일 검토
  - [ ] 사용되지 않는 파일 삭제
  - [ ] 어댑터만 남은 파일 정리
- [ ] `domain/models/__init__.py` 업데이트
  - [ ] Deprecation 경고 추가
  - [ ] 새 위치로의 리다이렉트 (호환성)
- [ ] 전체 코드베이스에서 `domain.models` import 검색
- [ ] 점진적으로 새 import로 변경
- [ ] Deprecation 경고 제거 시점 계획 수립

#### 리스크 관리
- **리스크**: 모델 간 순환 의존성 발생
  - **완화책**: ID 기반 참조 사용, 의존성 방향 명확히 정의
- **리스크**: 기존 UseCase 대량 변경
  - **완화책**: 어댑터 패턴, 점진적 마이그레이션

#### 예상 소요 시간
- Step 2.1.1: 2시간
- Step 2.1.2: 3시간
- Step 2.1.3: 2시간
- Step 2.1.4: 2시간
- Step 2.1.5: 1시간
- Step 2.1.6: 2시간
- Step 2.1.7: 2시간
- Step 2.1.8: 3시간
- **총계**: 17시간

---

### Phase 2.2: 비교/판단 로직 Service로 이동

#### 목표
- Domain Model에 남아있는 비즈니스 로직을 Domain Service로 이동
- 순수 함수로 변환하여 테스트 용이성 향상
- 판정 규칙을 명시적으로 분리

#### 작업 체크리스트

##### Step 2.2.1: 판정 로직 식별
- [ ] `domain/models/` 및 `domain/entities/` 폴더 전체 스캔
- [ ] `is_xxx()`, `has_xxx()`, `compute_xxx()`, `compare_xxx()` 메서드 목록 작성
- [ ] 각 메서드의 책임 분석
  - [ ] 단순 상태 체크? → Property로 유지 가능
  - [ ] 계산/판정 로직? → Service로 이동
- [ ] 이동 계획 문서 작성

##### Step 2.2.2: 버전 선택 정책 및 Service 생성 (Policy vs Service 구분!)
- [ ] `domain/policies/version_selection.py` 생성 (먼저)
  - [ ] 순수 함수로 버전 선택 규칙 정의
  - [ ] `select_by_filename(files: list[File]) -> Optional[File]` (순수 함수)
  - [ ] `select_by_mtime(files: list[File]) -> Optional[File]` (순수 함수)
  - [ ] `select_by_size(files: list[File]) -> Optional[File]` (순수 함수)
  - [ ] 각 함수는 부작용 없음 (순수 함수)
- [ ] `domain/services/version_selector.py` 생성 (그 다음)
  - [ ] `VersionSelectionService` 클래스 정의
  - [ ] `select_best_version(files: list[File]) -> File` 메서드
  - [ ] **Policy 함수들을 순차적으로 호출하여 조합**
  - [ ] 복잡한 판정 로직 포함
- [ ] 기존 코드에서 판정 로직 추출
- [ ] 단위 테스트 작성
  - [ ] Policy 함수들 테스트 (`tests/domain/policies/test_version_selection.py`)
  - [ ] Service 클래스 테스트 (`tests/domain/services/test_version_selector.py`)
  - [ ] 다양한 시나리오 테스트
  - [ ] Edge case 테스트
- [ ] 통합 테스트로 동작 확인

##### Step 2.2.3: 중복 탐지 로직 Service 강화
- [ ] `domain/services/duplicate_detector.py` 확장 (Phase 1.2.3에서 생성됨)
  - [ ] 단계적 탐지 로직 상세 구현
    - [ ] Raw hash 비교
    - [ ] Normalized hash 비교
    - [ ] SimHash 유사도 비교
  - [ ] 임계값 기반 판정
  - [ ] 신뢰도 계산
- [ ] 기존 UseCase에서 로직 이동
- [ ] 단위 테스트 작성
- [ ] 통합 테스트로 동작 확인

##### Step 2.2.4: 무결성 검사 로직 Service 생성
- [ ] `domain/services/integrity_checker.py` 생성
  - [ ] `IntegrityCheckService` 클래스 정의
  - [ ] `check_file(file: File) -> list[IntegrityIssue]` 메서드
  - [ ] 인코딩 검증 로직
  - [ ] 빈 파일 검증 로직
  - [ ] 줄바꿈 일관성 검증 로직
- [ ] 기존 UseCase에서 로직 이동
- [ ] 단위 테스트 작성 (`tests/domain/services/test_integrity_checker.py`)
- [ ] 통합 테스트로 동작 확인

##### Step 2.2.5: 증거 생성 로직 Service 생성
- [ ] `domain/services/evidence_builder.py` 생성
  - [ ] `EvidenceBuilderService` 클래스 정의
  - [ ] `build_evidence(file1: File, file2: File, comparison_result: ComparisonResult) -> Evidence` 메서드
  - [ ] 증거 타입 결정 로직
  - [ ] 신뢰도 계산 로직
- [ ] 기존 코드에서 로직 이동
- [ ] 단위 테스트 작성
- [ ] 통합 테스트로 동작 확인

##### Step 2.2.6: Entity/ValueObject에서 비즈니스 로직 제거
- [ ] Entity 클래스에서 `is_xxx()`, `has_xxx()` 메서드 제거
  - [ ] Property로 변환 가능한 것은 Property로
  - [ ] 계산 로직은 Service로 이동 완료 확인
- [ ] ValueObject에서 계산 로직 제거
  - [ ] 불변성만 유지
  - [ ] 검증 로직은 유지 (생성 시점)
- [ ] 전체 코드베이스에서 사용처 업데이트
- [ ] 단위 테스트 업데이트
- [ ] 통합 테스트로 동작 확인

##### Step 2.2.7: 정리 및 문서화
- [ ] Domain Service 목록 문서화
- [ ] 각 Service의 책임 명시
- [ ] 사용 예시 코드 작성
- [ ] `protocols/development_protocol.md` 업데이트

#### 리스크 관리
- **리스크**: 성능 저하 (Service 호출 오버헤드)
  - **완화책**: 프로파일링으로 측정, 필요한 경우 캐싱

#### 예상 소요 시간
- Step 2.2.1: 2시간
- Step 2.2.2: 3시간
- Step 2.2.3: 3시간
- Step 2.2.4: 3시간
- Step 2.2.5: 2시간
- Step 2.2.6: 4시간
- Step 2.2.7: 1시간
- **총계**: 18시간

---

### Phase 2.3: Phase 2 통합 테스트 및 검증

#### 작업 체크리스트

- [ ] 전체 단위 테스트 실행 및 통과 확인
- [ ] 통합 테스트 실행 (모든 UseCase)
- [ ] 수동 테스트 수행
  - [ ] 중복 탐지 정확도 확인
  - [ ] 버전 선택 정확도 확인
  - [ ] 무결성 검사 정확도 확인
- [ ] 성능 벤치마크 실행
  - [ ] 기존 대비 성능 유지 확인
- [ ] 코드 커버리지 확인
- [ ] 린터/포매터 실행
- [ ] 타입 체크 실행
- [ ] 문서 리뷰
- [ ] Git 커밋 및 태그 생성 (`refactor/phase2-complete`)

#### 예상 소요 시간
- **총계**: 3시간

---

