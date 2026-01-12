# 리팩토링 보고서 인덱스

이 디렉토리에는 NovelGuard 프로젝트의 각 파일별 리팩토링 보고서가 포함되어 있습니다.

## 우선순위별 파일 목록

### P0 (최우선) - UI 프리징 및 구조적 문제

1. [P0-1: duplicate_detection_worker.py](P0-1_duplicate_detection_worker.md)
   - God Function: `run()` 메서드 455 lines
   - 파이프라인 분리 필요

2. [P0-2: qt_job_manager.py](P0-2_qt_job_manager.md)
   - Job 오케스트레이션 결합도 높음
   - Worker Factory 분리 필요

3. [P0-3: file_list_table.py](P0-3_file_list_table.md)
   - Delegate에서 문자열 생성/정규식 처리 혼재
   - 테이블 업데이트 정책 섞임

4. [P0-4: file_data_store.py](P0-4_file_data_store.md)
   - 데이터 + 이벤트 허브 + 배치 정책 혼재
   - print() 디버그 코드 존재

5. [P0-5: sqlite_index_repository.py](P0-5_sqlite_index_repository.md)
   - 인프라 레이어 비대 (500+ lines)
   - Query/Mapper/Repository 분리 필요

6. [P0-6: 순환 의존 제거](P0-6_circular_dependency.md)
   - main_window ↔ scan_tab ↔ base_tab 순환 의존

### P1 (높음) - 중복 코드 및 기능 중복

1. [P1-1: Tabs 중복 코드](P1-1_tabs_duplication.md)
   - duplicate_tab, scan_tab, encoding_tab, integrity_tab, small_file_tab 간 중복

2. [P1-2: filename_parser.py](P1-2_filename_parser.md)
   - 클래스/규칙/정책/정규식이 한 덩어리

3. [P1-3: containment_detector.py](P1-3_containment_detector.md)
   - 비교 전략/증거 수집/판정 혼재

### P2 (중간) - 기술부채 및 미완성

1. [P2-1: _stubs ViewModels](P2-1_stubs_viewmodels.md)
   - TODO/pass 스텁 코드

2. [P2-2: dark_theme.py](P2-2_dark_theme.md)
   - 함수 330 lines: 외부화/토큰화 필요

## 보고서 구조

각 보고서는 다음 섹션으로 구성됩니다:

1. **파일 개요 및 현황**: LOC, 클래스 수, 현재 구조
2. **문제점 분석**: 구체적인 문제점과 영향
3. **리팩토링 목표**: 핵심 목표와 원칙
4. **구체적인 리팩토링 계획**: 새로운 파일 구조, 클래스 설계
5. **단계별 작업 계획**: Phase별 작업 내용
6. **예상 효과**: 코드 품질, 아키텍처 개선, 성능
7. **체크리스트**: 코드 작성, 테스트, 문서화

## 사용 방법

1. 우선순위별로 보고서를 순서대로 검토
2. 각 보고서의 "구체적인 리팩토링 계획" 섹션을 확인
3. "단계별 작업 계획"에 따라 순차적으로 리팩토링 수행
4. "체크리스트"를 확인하여 완료 여부 검증

---

**작성일**: 2025-01-11  
**작성자**: NovelGuard 개발팀
