"""Golden Tests 자동 실행 스크립트.

pytest를 사용하여 Golden Tests를 실행하고 결과를 리포트합니다.
"""

import sys
import subprocess
from pathlib import Path


def run_golden_tests() -> bool:
    """Golden Tests 실행.
    
    Returns:
        성공 여부
    """
    print("Golden Tests 실행 중...")
    print()
    
    # pytest 실행
    test_file = Path(__file__).parent / "test_golden_scenarios.py"
    
    result = subprocess.run(
        [sys.executable, "-m", "pytest", str(test_file), "-v", "--tb=short"],
        capture_output=True,
        text=True
    )
    
    # 출력
    print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    
    # 결과
    if result.returncode == 0:
        print()
        print("=" * 60)
        print("✓ Golden Tests 모두 통과!")
        print("=" * 60)
        return True
    else:
        print()
        print("=" * 60)
        print("❌ Golden Tests 실패!")
        print("=" * 60)
        return False


def main() -> None:
    """메인 함수."""
    passed = run_golden_tests()
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
