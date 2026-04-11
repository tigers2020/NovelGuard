"""지정 폴더에 대해 스캔 후 중복 탐지를 실행하고 결과를 출력하는 CLI.

사용법 (프로젝트 루트에서):
  python -m scripts.run_duplicate_check_cli "F:\\kiwi\\text\\소설\\정리"

또는 src를 PYTHONPATH에 넣고:
  cd src && python -c "from pathlib import Path; exec(open('../scripts/run_duplicate_check_cli.py').read()); run(Path(r'F:\\kiwi\\text\\소설\\정리'))"
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

# 프로젝트 루트 기준: scripts/ -> 상위가 루트, src 추가
_project_root = Path(__file__).resolve().parent.parent
_src = _project_root / "src"
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))


def run(target_dir: Path) -> None:
    """대상 디렉터리를 스캔하고 중복 탐지를 실행한 뒤 결과를 출력합니다."""
    # PySide6 QObject 사용을 위해 QApplication 필요 (FileDataStore)
    from PySide6.QtWidgets import QApplication

    from application.dto.duplicate_detection_request import DuplicateDetectionRequest
    from application.dto.scan_request import ScanRequest
    from application.use_cases.duplicate_detection.duplicate_detection_pipeline import (
        DuplicateDetectionPipeline,
    )
    from application.use_cases.scan_folder import ScanFolderUseCase
    from domain.services.blocking_service import BlockingService
    from domain.services.containment_detector import ContainmentDetector
    from domain.services.exact_duplicate_detector import ExactDuplicateDetector
    from domain.services.filename_parser import FilenameParser
    from infrastructure.db.sqlite_index_repository import SQLiteIndexRepository
    from infrastructure.fs.scanner import FileSystemScanner
    from infrastructure.hashing.hash_service_adapter import HashServiceAdapter
    from infrastructure.logging.in_memory_log_sink import InMemoryLogSink

    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    log_sink = InMemoryLogSink(log_dir=_project_root / "logs")
    scanner = FileSystemScanner(log_sink=log_sink)

    # 임시 DB로 스캔/중복 탐지 (기존 앱 DB와 분리)
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)
    try:
        index_repo = SQLiteIndexRepository(db_path=db_path, log_sink=log_sink)
    except Exception:
        db_path.unlink(missing_ok=True)
        raise

    # 스캔 실행
    scan_request = ScanRequest(
        root_folder=target_dir,
        extensions=[],  # 빈 리스트 → 앱 기본 텍스트 확장자 사용
        include_subdirs=True,
        include_hidden=False,
        include_symlinks=True,
    )
    use_case = ScanFolderUseCase(scanner, index_repository=index_repo, log_sink=log_sink)
    result = use_case.execute(scan_request)

    run_id = index_repo.get_latest_run_id()
    if run_id is None:
        print("스캔 완료했으나 run_id를 찾을 수 없습니다.")
        db_path.unlink(missing_ok=True)
        return

    # FileDataStore에 동일 엔트리 추가 (경로 매핑용)
    from gui.models.file_data_store import FileDataStore

    store = FileDataStore(log_sink=log_sink)
    store.scan_folder = target_dir
    store.add_files(result.entries)

    # 파이프라인 의존성
    filename_parser = FilenameParser(log_sink=log_sink)
    blocking_service = BlockingService(filename_parser=filename_parser, log_sink=log_sink)
    containment_detector = ContainmentDetector(log_sink=log_sink)
    hash_service = HashServiceAdapter()
    exact_detector = ExactDuplicateDetector(hash_service=hash_service, log_sink=log_sink)

    pipeline = DuplicateDetectionPipeline(
        filename_parser=filename_parser,
        blocking_service=blocking_service,
        containment_detector=containment_detector,
        index_repository=index_repo,
        file_data_store=store,
        log_sink=log_sink,
        exact_detector=exact_detector,
    )

    dup_request = DuplicateDetectionRequest(
        run_id=run_id,
        enable_exact=True,
        enable_version=True,
        enable_containment=True,
        enable_near=False,
    )

    print(f"스캔 완료: {result.total_files}개 파일, run_id={run_id}")
    print("중복 탐지 실행 중...")
    try:
        results = pipeline.execute(dup_request)
    finally:
        try:
            index_repo.close()
        except Exception:
            pass
        db_path.unlink(missing_ok=True)

    # 결과 출력
    if not results:
        print("\n결과: 중복 파일 그룹이 없습니다. (중복 없음)")
        return

    print(f"\n중복 그룹 {len(results)}개 발견:\n")
    for g in results:
        paths = []
        for fid in g.file_ids:
            fd = store.get_file(fid)
            paths.append(fd.entry.path if fd else f"<file_id={fid}>")
        keeper_id = g.recommended_keeper_id
        keeper_path = None
        if keeper_id is not None:
            kf = store.get_file(keeper_id)
            keeper_path = kf.entry.path if kf else None
        print(f"  [타입: {g.duplicate_type}] confidence={g.confidence:.2f}")
        for p in paths:
            mark = " (추천 유지)" if keeper_path and p == keeper_path else ""
            print(f"    - {p}{mark}")
        print()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("사용법: python -m scripts.run_duplicate_check_cli <폴더경로>")
        print('예: python -m scripts.run_duplicate_check_cli "F:\\kiwi\\text\\소설\\정리"')
        sys.exit(1)
    target = Path(sys.argv[1])
    if not target.is_dir():
        print(f"오류: 폴더가 없습니다: {target}")
        sys.exit(2)
    run(target)
