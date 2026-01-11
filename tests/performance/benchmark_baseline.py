"""성능 벤치마크 기준선 측정 스크립트.

리팩토링 전 성능 기준선을 측정하고 문서화합니다.
"""

import json
import sys
import time
import psutil
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Callable

# 프로젝트 루트를 sys.path에 추가
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from infra.db.file_repository import FileRepository
from infra.logging.std_logger import create_std_logger
from infra.encoding.encoding_detector import EncodingDetector
from infra.hashing.hash_service_adapter import HashServiceAdapter
from infra.fs.file_scanner import FileScanner
from usecases.scan_files import ScanFilesUseCase
from usecases.find_duplicates import FindDuplicatesUseCase
from tests.fixtures import FIXTURES_DIR


def measure_scan_throughput(root_path: Path, num_runs: int = 3) -> Dict[str, Any]:
    """스캔 처리량 측정 (files/sec).
    
    Args:
        root_path: 스캔할 디렉토리
        num_runs: 측정 반복 횟수
    
    Returns:
        측정 결과 딕셔너리
    """
    results = []
    
    for i in range(num_runs):
        logger = create_std_logger(name="benchmark")
        repository = FileRepository()
        hash_service = HashServiceAdapter()
        encoding_detector = EncodingDetector(logger=logger)
        scanner = FileScanner(logger=logger)
        usecase = ScanFilesUseCase(
            repository=repository,
            hash_service=hash_service,
            encoding_detector=encoding_detector,
            logger=logger,
            scanner=scanner
        )
        
        start_time = time.time()
        metas = usecase.execute(root_path)
        end_time = time.time()
        
        elapsed = end_time - start_time
        num_files = len(metas)
        throughput = num_files / elapsed if elapsed > 0 else 0
        
        results.append({
            "num_files": num_files,
            "elapsed": elapsed,
            "throughput": throughput
        })
    
    # 평균 계산
    avg_throughput = sum(r["throughput"] for r in results) / len(results)
    avg_elapsed = sum(r["elapsed"] for r in results) / len(results)
    num_files = results[0]["num_files"]
    
    return {
        "files_per_sec": round(avg_throughput, 2),
        "num_files": num_files,
        "avg_elapsed_sec": round(avg_elapsed, 3),
        "tolerance": 0.05,
        "runs": results
    }


def measure_duplicate_detection(root_path: Path, num_runs: int = 3) -> Dict[str, Any]:
    """중복 탐지 처리량 측정 (groups/sec).
    
    Args:
        root_path: 스캔할 디렉토리
        num_runs: 측정 반복 횟수
    
    Returns:
        측정 결과 딕셔너리
    """
    results = []
    
    for i in range(num_runs):
        logger = create_std_logger(name="benchmark")
        repository = FileRepository()
        hash_service = HashServiceAdapter()
        encoding_detector = EncodingDetector(logger=logger)
        scanner = FileScanner(logger=logger)
        scan_usecase = ScanFilesUseCase(
            repository=repository,
            hash_service=hash_service,
            encoding_detector=encoding_detector,
            logger=logger,
            scanner=scanner
        )
        
        # 스캔 먼저 수행
        metas = scan_usecase.execute(root_path)
        for meta in metas:
            record = repository.meta_to_record(meta)
            repository.save(record)
        
        # 중복 탐지 측정
        find_dup_usecase = FindDuplicatesUseCase(repository)
        start_time = time.time()
        groups = find_dup_usecase.execute()
        end_time = time.time()
        
        elapsed = end_time - start_time
        num_groups = len(groups)
        num_records = repository.count()
        throughput = num_groups / elapsed if elapsed > 0 else 0
        comparisons = num_records * (num_records - 1) / 2  # 대략적 비교 횟수
        comparisons_per_sec = comparisons / elapsed if elapsed > 0 else 0
        
        results.append({
            "num_groups": num_groups,
            "num_records": num_records,
            "elapsed": elapsed,
            "throughput": throughput,
            "comparisons_per_sec": comparisons_per_sec
        })
    
    # 평균 계산
    avg_throughput = sum(r["throughput"] for r in results) / len(results)
    avg_comparisons_per_sec = sum(r["comparisons_per_sec"] for r in results) / len(results)
    avg_elapsed = sum(r["elapsed"] for r in results) / len(results)
    num_groups = results[0]["num_groups"]
    num_records = results[0]["num_records"]
    
    return {
        "groups_per_sec": round(avg_throughput, 2),
        "comparisons_per_sec": round(avg_comparisons_per_sec, 2),
        "num_groups": num_groups,
        "num_records": num_records,
        "avg_elapsed_sec": round(avg_elapsed, 3),
        "tolerance": 0.05,
        "runs": results
    }


def measure_memory_usage(func: Callable[[], Any]) -> Dict[str, Any]:
    """메모리 사용량 측정 (peak RSS, MB).
    
    Args:
        func: 측정할 함수
    
    Returns:
        측정 결과 딕셔너리
    """
    process = psutil.Process()
    
    # 초기 메모리 측정
    process.memory_info()  # 캐시 워밍업
    initial_rss = process.memory_info().rss / (1024 * 1024)  # MB
    
    # 함수 실행
    func()
    
    # 최종 메모리 측정
    final_rss = process.memory_info().rss / (1024 * 1024)  # MB
    
    return {
        "initial_rss_mb": round(initial_rss, 2),
        "final_rss_mb": round(final_rss, 2),
        "delta_rss_mb": round(final_rss - initial_rss, 2),
        "peak_rss_mb": round(final_rss, 2)  # psutil은 peak를 직접 제공하지 않음
    }


def measure_cpu_time(func: Callable[[], Any]) -> Dict[str, Any]:
    """CPU 시간 측정 (process time, 초).
    
    Args:
        func: 측정할 함수
    
    Returns:
        측정 결과 딕셔너리
    """
    start_time = time.process_time()
    func()
    end_time = time.process_time()
    
    elapsed = end_time - start_time
    
    return {
        "cpu_time_seconds": round(elapsed, 3)
    }


def run_full_workflow(root_path: Path) -> None:
    """전체 워크플로우 실행 (메모리/CPU 측정용)."""
    logger = create_std_logger(name="benchmark")
    repository = FileRepository()
    hash_service = HashServiceAdapter()
    encoding_detector = EncodingDetector(logger=logger)
    scanner = FileScanner(logger=logger)
    scan_usecase = ScanFilesUseCase(
        repository=repository,
        hash_service=hash_service,
        encoding_detector=encoding_detector,
        logger=logger,
        scanner=scanner
    )
    
    # 스캔
    metas = scan_usecase.execute(root_path)
    for meta in metas:
        record = repository.meta_to_record(meta)
        repository.save(record)
    
    # 중복 탐지
    find_dup_usecase = FindDuplicatesUseCase(repository)
    groups = find_dup_usecase.execute()


def main() -> None:
    """메인 함수."""
    print("성능 벤치마크 기준선 측정 시작...")
    print(f"측정 시각: {datetime.now().isoformat()}")
    print(f"플랫폼: {sys.platform}")
    print(f"Python 버전: {sys.version}")
    print()
    
    # 측정 대상 데이터셋
    medium_fixture = FIXTURES_DIR / "medium"
    
    # 1. 스캔 처리량 측정
    print("1. 스캔 처리량 측정 중...")
    scan_result = measure_scan_throughput(medium_fixture, num_runs=3)
    print(f"   - 파일 수: {scan_result['num_files']}")
    print(f"   - 평균 처리량: {scan_result['files_per_sec']} files/sec")
    print(f"   - 평균 소요 시간: {scan_result['avg_elapsed_sec']} sec")
    print()
    
    # 2. 중복 탐지 처리량 측정
    print("2. 중복 탐지 처리량 측정 중...")
    dup_result = measure_duplicate_detection(medium_fixture, num_runs=3)
    print(f"   - 레코드 수: {dup_result['num_records']}")
    print(f"   - 그룹 수: {dup_result['num_groups']}")
    print(f"   - 평균 처리량: {dup_result['groups_per_sec']} groups/sec")
    print(f"   - 평균 비교 속도: {dup_result['comparisons_per_sec']} comparisons/sec")
    print(f"   - 평균 소요 시간: {dup_result['avg_elapsed_sec']} sec")
    print()
    
    # 3. 메모리 사용량 측정
    print("3. 메모리 사용량 측정 중...")
    memory_result = measure_memory_usage(lambda: run_full_workflow(medium_fixture))
    print(f"   - 초기 RSS: {memory_result['initial_rss_mb']} MB")
    print(f"   - 최종 RSS: {memory_result['final_rss_mb']} MB")
    print(f"   - 델타 RSS: {memory_result['delta_rss_mb']} MB")
    print()
    
    # 4. CPU 시간 측정
    print("4. CPU 시간 측정 중...")
    cpu_result = measure_cpu_time(lambda: run_full_workflow(medium_fixture))
    print(f"   - CPU 시간: {cpu_result['cpu_time_seconds']} sec")
    print()
    
    # 결과 통합
    baseline = {
        "measured_at": datetime.now().isoformat(),
        "environment": {
            "os": sys.platform,
            "python_version": sys.version.split()[0]
        },
        "scan_throughput": scan_result,
        "duplicate_detection": dup_result,
        "memory_usage": memory_result,
        "cpu_time": cpu_result
    }
    
    # JSON 파일로 저장
    output_path = Path(__file__).parent / "benchmark_baseline.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(baseline, f, indent=2, ensure_ascii=False)
    
    print(f"기준선 저장 완료: {output_path}")
    print("\n측정 완료!")


if __name__ == "__main__":
    main()
