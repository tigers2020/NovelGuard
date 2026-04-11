"""현행 저장소 검증 스크립트.

기본 `pytest` 기준선(`pyproject.toml`의 testpaths)만 실행한다.

과거에는 Golden Tests와 `tests/_archive/performance/` 벤치마크까지 묶었으나,
해당 하네스는 삭제된 `infra.*` / `usecases.*` 트리에 의존해 현재는 신뢰할 수 없다.
아카이브 하네스는 [tests/_archive/README.md](../tests/_archive/README.md)를 참고한다.
"""

import subprocess
import sys
from datetime import datetime
from pathlib import Path


def run_command(cmd: list[str], description: str, *, cwd: str | None = None) -> bool:
    """명령 실행."""
    print(f"\n{'=' * 60}")
    print(description)
    print(f"{'=' * 60}\n")

    result = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)

    print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)

    return result.returncode == 0


def main() -> None:
    """기본 pytest 기준선만 검증."""
    print("\n현행 검증 시작 (pytest 기본 수집)")
    print(f"시각: {datetime.now().isoformat()}")
    print(f"{'=' * 60}\n")

    project_root = Path(__file__).resolve().parent.parent

    # 회귀용 스모크 (문서에 기록된 Phase 0 subset; 주석으로 유지)
    # python -m pytest tests/app/settings/test_constants.py \
    #   tests/application/use_cases/duplicate_detection/test_pipeline_basic.py \
    #   tests/gui/workers/test_duplicate_detection_worker.py \
    #   tests/infrastructure/db/test_sqlite_index_repository.py \
    #   tests/integration/test_scan_with_index_repository.py -q

    passed = run_command(
        [sys.executable, "-m", "pytest"],
        "python -m pytest (프로젝트 루트, 기본 testpaths)",
        cwd=str(project_root),
    )

    print(f"\n{'=' * 60}")
    print("최종 결과")
    print(f"{'=' * 60}")
    print(f"pytest: {'통과' if passed else '실패'}")
    print(f"{'=' * 60}\n")

    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
