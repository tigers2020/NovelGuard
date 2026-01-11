## 🔄 Phase 0: 기반 작업 (선수 작업)

> **목표**: 리팩토링 시작 전 안전망 구축 및 기준선 확립

### Phase 0.5: Golden Tests 및 벤치마크 기준선 고정

#### 목표
- 기존 동작을 보장하는 "Golden Tests" 생성
- 성능 벤치마크 기준선 측정 및 문서화
- 리팩토링 중 회귀 방지

#### 작업 체크리스트

##### Step 0.5.1: 테스트 데이터셋 고정
- [ ] `tests/fixtures/` 디렉토리 생성
- [ ] 샘플 데이터셋 생성 (소규모/중규모/엣지케이스)
  - [ ] 소규모: 10~50개 파일 (동일 해시 중복 포함)
  - [ ] 중규모: 100~500개 파일 (다양한 패턴)
  - [ ] 엣지케이스: 
    - [ ] 제목이 다르지만 내용 동일
    - [ ] 포함 관계 (1-114화 vs 1-158화)
    - [ ] 인코딩이 섞인 텍스트
    - [ ] 바이너리/텍스트 혼재
    - [ ] 빈 파일, 매우 큰 파일
- [ ] 데이터셋을 Git에 커밋 (`.gitignore` 제외)
- [ ] 데이터셋 문서화 (`tests/fixtures/README.md`)

##### Step 0.5.2: Golden Tests 생성 (스냅샷 테스트 + 정규화 규칙 필수!)
- [ ] `tests/integration/test_golden_scenarios.py` 생성
- [ ] **스냅샷 정규화 헬퍼 함수** 생성 (`tests/integration/snapshot_normalizer.py`)
  - [ ] `normalize_snapshot(data: dict) -> dict` 함수 구현
    - [ ] **순서 정규화**: 딕셔너리/집합/리스트를 stable sort 적용
    - [ ] **경로 정규화**: 절대 경로를 상대 경로로 변환, OS 경로 구분자 통일 (`/`)
    - [ ] **비결정 필드 제거**: 타임스탬프, 성능 정보, 임시 ID 등 제거
    - [ ] **숫자 반올림**: 실수 비교를 위한 반올림 (예: 소수점 6자리)
- [ ] 각 시나리오별로 기대 결과 JSON 스냅샷 생성
  - [ ] 스캔 결과 스냅샷 (`scan_results_*.json`) - **정규화 후 저장**
  - [ ] 중복 그룹 스냅샷 (`duplicate_groups_*.json`) - **정규화 후 저장**
  - [ ] 무결성 이슈 스냅샷 (`integrity_issues_*.json`) - **정규화 후 저장**
- [ ] 스냅샷 비교 테스트 작성 (정규화 규칙 적용)
  ```python
  def test_golden_exact_duplicates():
      """완전 동일 파일 중복 탐지 - 스냅샷 비교."""
      result = execute_scan(fixtures.SMALL_EXACT_DUPLICATES)
      normalized_result = normalize_snapshot(result)
      expected = load_snapshot("exact_duplicates.json")  # 이미 정규화된 상태
      assert normalized_result == expected
  ```
- [ ] 정규화 규칙 검증 테스트 작성
  - [ ] 순서 비결정 시나리오 테스트
  - [ ] OS 경로 차이 테스트 (Windows vs Linux)
  - [ ] 타임스탬프 포함 데이터 테스트
- [ ] 모든 시나리오에 대해 Golden Test 작성
- [ ] CI/CD에 Golden Tests 추가 (필수 통과)

#### 스냅샷 정규화 규칙 (필수)

스냅샷 테스트는 비결정적 요소 때문에 깨지기 쉽습니다. 다음 정규화 규칙을 **반드시** 적용해야 합니다:

1. **순서 정규화** (stable sort)
   - 리스트/튜플: ID 또는 경로 기준으로 정렬
   - 딕셔너리: 키 기준으로 정렬
   - 집합: 정렬된 리스트로 변환

2. **경로 정규화**
   - 절대 경로 → 상대 경로 변환
   - OS 경로 구분자 통일 (`\` → `/`)
   - 경로 대소문자 통일 (필요 시)

3. **비결정 필드 제거**
   - 타임스탬프 (`mtime`, `created_at` 등)
   - 성능 정보 (`duration`, `memory_usage` 등)
   - 임시 ID (UUID, 랜덤 ID 등)
   - 프로세스 ID, 스레드 ID

4. **숫자 반올림**
   - 실수 비교를 위한 반올림 (소수점 6자리 권장)
   - 부동소수점 오차 보정

##### Step 0.5.3: 성능 벤치마크 기준선 측정
- [ ] `tests/performance/` 디렉토리 생성
- [ ] 성능 측정 스크립트 작성 (`benchmark_baseline.py`)
- [ ] 측정 항목 정의 및 구현:
  - [ ] **스캔 처리량**: `files/sec` (1000개 파일 기준)
  - [ ] **중복 탐지 처리량**: `comparisons/sec` 또는 `groups/sec`
  - [ ] **메모리 사용량**: peak RSS (MB)
  - [ ] **CPU 시간**: process time (초)
- [ ] 기준선 측정 실행 (3회 평균)
- [ ] 결과를 JSON 파일로 저장 (`benchmark_baseline.json`)
  ```json
  {
    "scan_throughput": {"files_per_sec": 35.2, "tolerance": 0.05},
    "duplicate_detection": {"groups_per_sec": 120.5, "tolerance": 0.05},
    "memory_peak_rss_mb": 245.8,
    "cpu_time_seconds": 28.4
  }
  ```
- [ ] 벤치마크 문서화 (`docs/performance/benchmark_baseline.md`)

##### Step 0.5.4: 회귀 테스트 자동화 (실패 후 액션 포함!)
- [ ] 각 Phase 완료 시 Golden Tests 자동 실행 스크립트 작성
- [ ] 성능 벤치마크 자동 실행 및 비교 스크립트 작성
  - [ ] 기준선 대비 ±5% 이내 확인
  - [ ] 벗어나면 경고 (soft gate)
  - [ ] ±10% 초과 시 실패 (hard gate)
  - [ ] **실패 후 액션 (v1.3 규칙)**:
    ```python
    # benchmark_gate.py
    def check_performance_gate(measured: dict, baseline: dict, env: str = "local") -> bool:
        """성능 게이트 체크."""
        for metric, value in measured.items():
            baseline_value = baseline[metric]
            diff_percent = abs(value - baseline_value) / baseline_value * 100
            
            if diff_percent > 10:  # hard gate
                if env == "ci":
                    print(f"ERROR: {metric} 성능 회귀 {diff_percent:.1f}% (기준선 ±10% 초과)")
                    print("PR block: 성능 기준 미달")
                    return False  # CI에서 PR block
                else:
                    print(f"WARNING: {metric} 성능 회귀 {diff_percent:.1f}% (기준선 ±10% 초과)")
                    # 로컬에서는 경고만
            elif diff_percent > 5:  # soft gate
                print(f"WARNING: {metric} 성능 변화 {diff_percent:.1f}% (기준선 ±5% 초과)")
        return True
    ```
- [ ] CI/CD에 통합
  - [ ] **CI 환경 편차 고려사항 (v1.4 반영)**:
    - [ ] CI 성능 측정은 "경향성 감지(경고)" 중심으로 두고, hard gate는 **전용 runner/고정 리소스 환경**에서만 강하게 거는 옵션 추가
    - [ ] CI 환경의 시스템 부하/리소스 편차를 고려하여 더 넓은 허용 범위 적용 (예: ±10% → ±15%)
    - [ ] 로컬 환경: ±5% 초과 시 경고 (soft gate), ±10% 초과 시 경고만 (hard gate 없음)
    - [ ] CI 환경: ±5% 초과 시 경고만 (soft gate, 성능 편차 고려), ±10% 초과 시 **PR block** (hard gate, 전용 runner에서만)
  - [ ] CI에서 hard gate 실패 시 **PR block** 설정
  - [ ] 로컬에서는 경고만 출력 (작업 계속 가능)
- [ ] 테스트 실패 시 자동 롤백 옵션 검토 (선택적)
  - [ ] Git tag 기반 롤백 스크립트 작성 (필요 시)

#### 성능 측정 기준 (구체화)

각 Phase 완료 시 다음 항목을 측정하고 기준선 대비 ±5% 이내 유지:

1. **스캔 처리량** (`files/sec`)
   - 측정 방법: 1000개 파일 스캔 시간 측정
   - 기준선: (Phase 0.5에서 측정)
   - 허용 범위: 기준선 ±5%

2. **중복 탐지 처리량** (`groups/sec` 또는 `comparisons/sec`)
   - 측정 방법: 100개 중복 그룹 탐지 시간 측정
   - 기준선: (Phase 0.5에서 측정)
   - 허용 범위: 기준선 ±5%

3. **메모리 사용량** (peak RSS, MB)
   - 측정 방법: `memory_profiler` 또는 `psutil` 사용
   - 기준선: (Phase 0.5에서 측정)
   - 허용 범위: 기준선 ±5% (단, 증가는 우려 대상)

4. **CPU 시간** (process time, 초)
   - 측정 방법: `time.process_time()` 사용
   - 기준선: (Phase 0.5에서 측정)
   - 허용 범위: 기준선 ±5%

#### 예상 소요 시간
- Step 0.5.1: 2시간
- Step 0.5.2: 4시간
- Step 0.5.3: 3시간
- Step 0.5.4: 2시간
- **총계**: 11시간

---

