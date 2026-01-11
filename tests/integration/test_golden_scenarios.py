"""Golden Tests - 리팩토링 전 기준선 검증.

기존 동작을 보장하는 스냅샷 테스트를 수행합니다.
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, List

# 프로젝트 루트를 sys.path에 추가
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

# Infrastructure
from infra.db.file_repository import FileRepository
from infra.encoding.encoding_detector import EncodingDetector

# UseCases
from usecases.scan_files import ScanFilesUseCase
from usecases.find_duplicates import FindDuplicatesUseCase
from usecases.check_integrity import CheckIntegrityUseCase

# Domain Models
from domain.models.file_meta import FileMeta
from domain.models.file_record import FileRecord
from domain.aggregates.duplicate_group import DuplicateGroup
from domain.entities.integrity_issue import IntegrityIssue

# Test Fixtures
from tests.fixtures import FIXTURES_DIR
from tests.integration.snapshot_normalizer import normalize_snapshot


def execute_scan(fixture_path: Path) -> Dict[str, Any]:
    """전체 스캔 워크플로우 실행.
    
    UseCase들을 순차적으로 호출하여 전체 스캔 프로세스를 실행합니다.
    
    Args:
        fixture_path: 스캔할 픽스처 디렉토리 경로
    
    Returns:
        정규화된 결과 딕셔너리
    """
    # Infrastructure 초기화
    from infra.logging.std_logger import create_std_logger
    from infra.hashing.hash_service_adapter import HashServiceAdapter
    from infra.fs.file_scanner import FileScanner
    
    logger = create_std_logger(name="test_golden")
    repository = FileRepository()
    hash_service = HashServiceAdapter()  # IHashService 구현
    encoding_detector = EncodingDetector(logger=logger)
    scanner = FileScanner(logger=logger)  # IFileScanner 구현
    
    # Step 1: 파일 스캔 (ScanFilesUseCase)
    scan_usecase = ScanFilesUseCase(
        repository=repository,
        hash_service=hash_service,
        encoding_detector=encoding_detector,
        logger=logger,
        scanner=scanner
    )
    metas = scan_usecase.execute(fixture_path)
    
    # FileMeta를 FileRecord로 변환 (Enrich 단계 시뮬레이션)
    for meta in metas:
        record = repository.meta_to_record(meta)
        repository.save(record)
    
    # Step 2: 중복 탐지 (FindDuplicatesUseCase)
    find_duplicates_usecase = FindDuplicatesUseCase(
        repository=repository,
        logger=logger
    )
    duplicate_groups = find_duplicates_usecase.execute()
    
    # Step 3: 무결성 검사 (CheckIntegrityUseCase)
    check_integrity_usecase = CheckIntegrityUseCase(
        repository=repository,
        encoding_detector=encoding_detector,
        logger=logger
    )
    integrity_issues = check_integrity_usecase.execute()
    
    # 결과를 딕셔너리로 변환
    result = {
        "scan_results": _serialize_file_metas(metas, fixture_path),
        "duplicate_groups": _serialize_duplicate_groups(duplicate_groups),
        "integrity_issues": _serialize_integrity_issues(integrity_issues),
        "stats": {
            "total_files": len(metas),
            "duplicate_groups_count": len(duplicate_groups),
            "integrity_issues_count": len(integrity_issues),
        }
    }
    
    return result


def _serialize_file_metas(metas: List[FileMeta], base_path: Path) -> List[Dict[str, Any]]:
    """FileMeta 리스트를 딕셔너리 리스트로 변환."""
    result = []
    for meta in metas:
        # 경로를 상대 경로로 변환
        rel_path = str(Path(meta.path_str).relative_to(base_path)).replace('\\', '/')
        
        result.append({
            "file_id": meta.file_id,
            "path": rel_path,
            "name": meta.name,
            "ext": meta.ext,
            "size": meta.size,
            # mtime은 정규화 시 제거됨
            "is_text_guess": meta.is_text_guess,
            "encoding_detected": meta.encoding_detected,
            "encoding_confidence": round(meta.encoding_confidence, 6) if meta.encoding_confidence is not None else None,
            "fingerprint_fast": meta.fingerprint_fast,
        })
    return result


def _serialize_duplicate_groups(groups: List[DuplicateGroup]) -> List[Dict[str, Any]]:
    """DuplicateGroup 리스트를 딕셔너리 리스트로 변환."""
    result = []
    for group in groups:
        result.append({
            "group_id": group.group_id,
            "group_type": group.group_type,
            "member_ids": sorted(group.member_ids),  # 정렬하여 순서 보장
            "canonical_id": group.canonical_id,
            "confidence": round(group.confidence, 6),
            "bytes_savable": group.bytes_savable,
            "status": group.status,
            "reasons": sorted(group.reasons) if group.reasons else [],
        })
    return result


def _serialize_integrity_issues(issues: List[IntegrityIssue]) -> List[Dict[str, Any]]:
    """IntegrityIssue 리스트를 딕셔너리 리스트로 변환."""
    result = []
    for issue in issues:
        # metrics의 실수 값 반올림
        normalized_metrics = {}
        for key, value in issue.metrics.items():
            if isinstance(value, float):
                normalized_metrics[key] = round(value, 6)
            else:
                normalized_metrics[key] = value
        
        result.append({
            "issue_id": issue.issue_id,
            "file_id": issue.file_id,
            "severity": issue.severity,
            "category": issue.category,
            "message": issue.message,
            "metrics": normalized_metrics,
            "fixable": issue.fixable,
            "suggested_fix": issue.suggested_fix,
        })
    return result


def load_snapshot(snapshot_path: Path) -> Dict[str, Any]:
    """스냅샷 파일 로드.
    
    Args:
        snapshot_path: 스냅샷 파일 경로
    
    Returns:
        스냅샷 딕셔너리
    """
    with open(snapshot_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_snapshot(data: Dict[str, Any], snapshot_path: Path) -> None:
    """스냅샷 파일 저장.
    
    Args:
        data: 저장할 데이터 (이미 정규화된 상태)
        snapshot_path: 저장할 파일 경로
    """
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    with open(snapshot_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False, sort_keys=True)


# 테스트 함수들

def test_golden_exact_duplicates():
    """완전 동일 파일 중복 탐지 - 스냅샷 비교."""
    fixture_path = FIXTURES_DIR / "small"
    snapshot_path = PROJECT_ROOT / "tests" / "snapshots" / "scan_results_small_exact.json"
    
    # 스캔 실행
    result = execute_scan(fixture_path)
    
    # 정규화
    normalized_result = normalize_snapshot(result, base_path=fixture_path)
    
    # 스냅샷 파일이 없으면 생성 (최초 실행 시)
    if not snapshot_path.exists():
        save_snapshot(normalized_result, snapshot_path)
        print(f"스냅샷 파일 생성: {snapshot_path}")
        return
    
    # 스냅샷 비교
    expected = load_snapshot(snapshot_path)
    assert normalized_result == expected, "스냅샷 불일치!"
    print("✓ 완전 동일 파일 중복 탐지 테스트 통과")


def test_golden_normalized_duplicates():
    """정규화 후 동일 파일 탐지 - 스냅샷 비교."""
    fixture_path = FIXTURES_DIR / "small"
    snapshot_path = PROJECT_ROOT / "tests" / "snapshots" / "scan_results_small_normalized.json"
    
    result = execute_scan(fixture_path)
    normalized_result = normalize_snapshot(result, base_path=fixture_path)
    
    if not snapshot_path.exists():
        save_snapshot(normalized_result, snapshot_path)
        print(f"스냅샷 파일 생성: {snapshot_path}")
        return
    
    expected = load_snapshot(snapshot_path)
    assert normalized_result == expected, "스냅샷 불일치!"
    print("✓ 정규화 후 동일 파일 탐지 테스트 통과")


def test_golden_medium_dataset():
    """중규모 데이터셋 통합 테스트 - 스냅샷 비교."""
    fixture_path = FIXTURES_DIR / "medium"
    snapshot_path = PROJECT_ROOT / "tests" / "snapshots" / "scan_results_medium.json"
    
    result = execute_scan(fixture_path)
    normalized_result = normalize_snapshot(result, base_path=fixture_path)
    
    if not snapshot_path.exists():
        save_snapshot(normalized_result, snapshot_path)
        print(f"스냅샷 파일 생성: {snapshot_path}")
        return
    
    expected = load_snapshot(snapshot_path)
    assert normalized_result == expected, "스냅샷 불일치!"
    print("✓ 중규모 데이터셋 테스트 통과")


def test_golden_edge_cases():
    """엣지 케이스 통합 테스트 - 스냅샷 비교."""
    fixture_path = FIXTURES_DIR / "edge_cases"
    snapshot_path = PROJECT_ROOT / "tests" / "snapshots" / "scan_results_edge_cases.json"
    
    result = execute_scan(fixture_path)
    normalized_result = normalize_snapshot(result, base_path=fixture_path)
    
    if not snapshot_path.exists():
        save_snapshot(normalized_result, snapshot_path)
        print(f"스냅샷 파일 생성: {snapshot_path}")
        return
    
    expected = load_snapshot(snapshot_path)
    assert normalized_result == expected, "스냅샷 불일치!"
    print("✓ 엣지 케이스 테스트 통과")


if __name__ == "__main__":
    # 직접 실행 시 모든 테스트 실행
    print("Golden Tests 실행 중...")
    test_golden_exact_duplicates()
    test_golden_normalized_duplicates()
    test_golden_medium_dataset()
    test_golden_edge_cases()
    print("\n모든 Golden Tests 통과!")
