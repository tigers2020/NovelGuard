"""성능 게이트 체크 스크립트.

기준선 대비 성능 회귀를 감지하고 경고/실패 처리합니다.
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any


def check_performance_gate(
    measured: Dict[str, Any],
    baseline: Dict[str, Any],
    env: str = "local"
) -> bool:
    """성능 게이트 체크.
    
    Args:
        measured: 측정된 성능 데이터
        baseline: 기준선 성능 데이터
        env: 환경 ("local" | "ci")
    
    Returns:
        통과 여부 (True: 통과, False: 실패)
    """
    print(f"성능 게이트 체크 시작 (환경: {env})...")
    print()
    
    passed = True
    warnings = []
    errors = []
    
    # 1. 스캔 처리량 체크
    if "scan_throughput" in measured and "scan_throughput" in baseline:
        metric_name = "스캔 처리량 (files/sec)"
        measured_value = measured["scan_throughput"].get("files_per_sec", 0)
        baseline_value = baseline["scan_throughput"].get("files_per_sec", 0)
        tolerance = baseline["scan_throughput"].get("tolerance", 0.05)
        
        result = _check_metric(metric_name, measured_value, baseline_value, tolerance, env)
        if result == "error":
            errors.append(metric_name)
            passed = False
        elif result == "warning":
            warnings.append(metric_name)
    
    # 2. 중복 탐지 처리량 체크 (비교 속도 기준)
    if "duplicate_detection" in measured and "duplicate_detection" in baseline:
        metric_name = "중복 탐지 (comparisons/sec)"
        measured_value = measured["duplicate_detection"].get("comparisons_per_sec", 0)
        baseline_value = baseline["duplicate_detection"].get("comparisons_per_sec", 0)
        tolerance = baseline["duplicate_detection"].get("tolerance", 0.05)
        
        result = _check_metric(metric_name, measured_value, baseline_value, tolerance, env)
        if result == "error":
            errors.append(metric_name)
            passed = False
        elif result == "warning":
            warnings.append(metric_name)
    
    # 3. 메모리 사용량 체크 (증가만 체크)
    if "memory_usage" in measured and "memory_usage" in baseline:
        metric_name = "메모리 사용량 (delta_rss_mb)"
        measured_value = measured["memory_usage"].get("delta_rss_mb", 0)
        baseline_value = baseline["memory_usage"].get("delta_rss_mb", 0)
        
        # 메모리는 증가만 체크 (감소는 좋은 것)
        if measured_value > baseline_value:
            diff_percent = abs(measured_value - baseline_value) / baseline_value * 100 if baseline_value > 0 else 0
            
            if diff_percent > 10:  # hard gate
                if env == "ci":
                    errors.append(metric_name)
                    passed = False
                    print(f"❌ {metric_name}: {measured_value:.2f} MB (기준선: {baseline_value:.2f} MB)")
                    print(f"   → 증가율 {diff_percent:.1f}% (기준선 +10% 초과)")
                else:
                    warnings.append(metric_name)
                    print(f"⚠️  {metric_name}: {measured_value:.2f} MB (기준선: {baseline_value:.2f} MB)")
                    print(f"   → 증가율 {diff_percent:.1f}% (기준선 +10% 초과)")
            elif diff_percent > 5:  # soft gate
                warnings.append(metric_name)
                print(f"⚠️  {metric_name}: {measured_value:.2f} MB (기준선: {baseline_value:.2f} MB)")
                print(f"   → 증가율 {diff_percent:.1f}% (기준선 +5% 초과)")
            else:
                print(f"✓ {metric_name}: {measured_value:.2f} MB (기준선: {baseline_value:.2f} MB)")
        else:
            print(f"✓ {metric_name}: {measured_value:.2f} MB (기준선: {baseline_value:.2f} MB, 개선됨)")
    
    # 4. CPU 시간 체크
    if "cpu_time" in measured and "cpu_time" in baseline:
        metric_name = "CPU 시간 (seconds)"
        measured_value = measured["cpu_time"].get("cpu_time_seconds", 0)
        baseline_value = baseline["cpu_time"].get("cpu_time_seconds", 0)
        
        # CPU 시간도 증가만 체크
        if measured_value > baseline_value and baseline_value > 0:
            diff_percent = abs(measured_value - baseline_value) / baseline_value * 100
            
            if diff_percent > 10:  # hard gate
                if env == "ci":
                    errors.append(metric_name)
                    passed = False
                    print(f"❌ {metric_name}: {measured_value:.3f} sec (기준선: {baseline_value:.3f} sec)")
                    print(f"   → 증가율 {diff_percent:.1f}% (기준선 +10% 초과)")
                else:
                    warnings.append(metric_name)
                    print(f"⚠️  {metric_name}: {measured_value:.3f} sec (기준선: {baseline_value:.3f} sec)")
                    print(f"   → 증가율 {diff_percent:.1f}% (기준선 +10% 초과)")
            elif diff_percent > 5:  # soft gate
                warnings.append(metric_name)
                print(f"⚠️  {metric_name}: {measured_value:.3f} sec (기준선: {baseline_value:.3f} sec)")
                print(f"   → 증가율 {diff_percent:.1f}% (기준선 +5% 초과)")
        else:
            print(f"✓ {metric_name}: 통과")
    
    # 요약
    print()
    print("=" * 60)
    if passed:
        print("✓ 성능 게이트 통과!")
        if warnings:
            print(f"  경고 {len(warnings)}개: {', '.join(warnings)}")
    else:
        print("❌ 성능 게이트 실패!")
        print(f"  오류 {len(errors)}개: {', '.join(errors)}")
        if warnings:
            print(f"  경고 {len(warnings)}개: {', '.join(warnings)}")
        
        if env == "ci":
            print()
            print("PR BLOCKED: 성능 기준 미달")
    print("=" * 60)
    
    return passed


def _check_metric(
    name: str,
    measured: float,
    baseline: float,
    tolerance: float,
    env: str
) -> str:
    """단일 메트릭 체크.
    
    Returns:
        "ok" | "warning" | "error"
    """
    if baseline == 0:
        print(f"⚠️  {name}: 기준선이 0이므로 체크 불가")
        return "warning"
    
    diff_percent = abs(measured - baseline) / baseline * 100
    
    if diff_percent > 10:  # hard gate
        if env == "ci":
            print(f"❌ {name}: {measured:.2f} (기준선: {baseline:.2f})")
            print(f"   → 차이 {diff_percent:.1f}% (기준선 ±10% 초과)")
            return "error"
        else:
            print(f"⚠️  {name}: {measured:.2f} (기준선: {baseline:.2f})")
            print(f"   → 차이 {diff_percent:.1f}% (기준선 ±10% 초과)")
            return "warning"
    elif diff_percent > 5:  # soft gate
        print(f"⚠️  {name}: {measured:.2f} (기준선: {baseline:.2f})")
        print(f"   → 차이 {diff_percent:.1f}% (기준선 ±5% 초과)")
        return "warning"
    else:
        print(f"✓ {name}: {measured:.2f} (기준선: {baseline:.2f})")
        return "ok"


def main() -> None:
    """메인 함수."""
    if len(sys.argv) < 2:
        print("사용법: python benchmark_gate.py <측정_결과.json> [환경]")
        print("  환경: local (기본) | ci")
        sys.exit(1)
    
    measured_path = Path(sys.argv[1])
    env = sys.argv[2] if len(sys.argv) > 2 else "local"
    
    if not measured_path.exists():
        print(f"오류: 측정 결과 파일을 찾을 수 없습니다: {measured_path}")
        sys.exit(1)
    
    # 기준선 로드
    baseline_path = Path(__file__).parent / "benchmark_baseline.json"
    if not baseline_path.exists():
        print(f"오류: 기준선 파일을 찾을 수 없습니다: {baseline_path}")
        sys.exit(1)
    
    with open(measured_path, 'r', encoding='utf-8') as f:
        measured = json.load(f)
    
    with open(baseline_path, 'r', encoding='utf-8') as f:
        baseline = json.load(f)
    
    # 게이트 체크
    passed = check_performance_gate(measured, baseline, env)
    
    # 종료 코드
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
