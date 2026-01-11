"""Phase 완료 검증 스크립트.

Golden Tests 및 성능 벤치마크를 실행하여 Phase 완료 여부를 검증합니다.
"""

import sys
import subprocess
from pathlib import Path
from datetime import datetime


def run_command(cmd: list[str], description: str) -> bool:
    """명령 실행.
    
    Args:
        cmd: 실행할 명령
        description: 설명
    
    Returns:
        성공 여부
    """
    print(f"\n{'='*60}")
    print(f"{description}")
    print(f"{'='*60}\n")
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    
    return result.returncode == 0


def main() -> None:
    """메인 함수."""
    print(f"\nPhase 완료 검증 시작")
    print(f"시각: {datetime.now().isoformat()}")
    print(f"{'='*60}\n")
    
    project_root = Path(__file__).parent.parent
    
    # 1. Golden Tests 실행
    golden_tests_passed = run_command(
        [sys.executable, str(project_root / "tests" / "integration" / "run_golden_tests.py")],
        "1. Golden Tests 실행"
    )
    
    # 2. 성능 벤치마크 실행
    print(f"\n{'='*60}")
    print("2. 성능 벤치마크 실행")
    print(f"{'='*60}\n")
    
    benchmark_result = subprocess.run(
        [sys.executable, str(project_root / "tests" / "performance" / "benchmark_baseline.py")],
        capture_output=True,
        text=True
    )
    
    print(benchmark_result.stdout)
    if benchmark_result.stderr:
        print(benchmark_result.stderr, file=sys.stderr)
    
    benchmark_passed = benchmark_result.returncode == 0
    
    # 3. 성능 게이트 체크
    if benchmark_passed:
        gate_passed = run_command(
            [
                sys.executable,
                str(project_root / "tests" / "performance" / "benchmark_gate.py"),
                str(project_root / "tests" / "performance" / "benchmark_baseline.json"),
                "local"
            ],
            "3. 성능 게이트 체크"
        )
    else:
        print("\n성능 벤치마크 실패로 게이트 체크 스킵")
        gate_passed = False
    
    # 최종 결과
    print(f"\n{'='*60}")
    print("최종 결과")
    print(f"{'='*60}")
    print(f"Golden Tests: {'✓ 통과' if golden_tests_passed else '❌ 실패'}")
    print(f"성능 벤치마크: {'✓ 통과' if benchmark_passed else '❌ 실패'}")
    print(f"성능 게이트: {'✓ 통과' if gate_passed else '❌ 실패'}")
    print(f"{'='*60}\n")
    
    # 모두 통과 여부
    all_passed = golden_tests_passed and benchmark_passed and gate_passed
    
    if all_passed:
        print("✓ Phase 완료 검증 성공!")
        sys.exit(0)
    else:
        print("❌ Phase 완료 검증 실패!")
        sys.exit(1)


if __name__ == "__main__":
    main()
