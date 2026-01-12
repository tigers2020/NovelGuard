"""SQLiteIndexRepository 테스트."""
import sys
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

# 프로젝트 루트를 sys.path에 추가
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from application.dto.run_summary import RunSummary
from application.dto.scan_request import ScanRequest
from application.dto.ext_stat import ExtStat
from domain.entities.file_entry import FileEntry
from infrastructure.db.sqlite_index_repository import SQLiteIndexRepository


@pytest.fixture
def temp_db() -> Path:
    """임시 DB 파일 경로 생성."""
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as f:
        db_path = Path(f.name)
    yield db_path
    # 테스트 후 정리
    if db_path.exists():
        db_path.unlink()


@pytest.fixture
def repository(temp_db: Path) -> SQLiteIndexRepository:
    """SQLiteIndexRepository 인스턴스 생성."""
    return SQLiteIndexRepository(db_path=temp_db)


@pytest.fixture
def scan_request() -> ScanRequest:
    """테스트용 ScanRequest 생성."""
    return ScanRequest(
        root_folder=Path("/test/root"),
        extensions=[".txt", ".md"],
        include_subdirs=True,
        include_hidden=False,
        include_symlinks=True,
        incremental=True,
    )


@pytest.fixture
def file_entries() -> list[FileEntry]:
    """테스트용 FileEntry 리스트 생성."""
    base_time = datetime.now()
    return [
        FileEntry(
            path=Path("/test/root/file1.txt"),
            size=100,
            mtime=base_time,
            extension=".txt",
            is_hidden=False,
            is_symlink=False,
        ),
        FileEntry(
            path=Path("/test/root/file2.txt"),
            size=200,
            mtime=base_time,
            extension=".txt",
            is_hidden=False,
            is_symlink=False,
        ),
        FileEntry(
            path=Path("/test/root/file3.md"),
            size=300,
            mtime=base_time,
            extension=".md",
            is_hidden=False,
            is_symlink=False,
        ),
        FileEntry(
            path=Path("/test/root/.hidden.txt"),
            size=50,
            mtime=base_time,
            extension=".txt",
            is_hidden=True,
            is_symlink=False,
        ),
    ]


def test_start_run(repository: SQLiteIndexRepository, scan_request: ScanRequest) -> None:
    """start_run 테스트."""
    run_id = repository.start_run(scan_request)
    
    assert run_id is not None
    assert run_id > 0
    
    # Run이 생성되었는지 확인
    summary = repository.get_run_summary(run_id)
    assert summary is not None
    assert summary.run_id == run_id
    assert summary.status == "running"
    assert summary.root_path == scan_request.root_folder


def test_upsert_files(repository: SQLiteIndexRepository, scan_request: ScanRequest, file_entries: list[FileEntry]) -> None:
    """upsert_files 테스트."""
    run_id = repository.start_run(scan_request)
    
    repository.upsert_files(run_id, file_entries)
    
    # 파일이 저장되었는지 확인
    files = repository.list_files(run_id)
    assert len(files) == len(file_entries)
    
    # 첫 번째 파일 확인
    file1 = next((f for f in files if f.path.name == "file1.txt"), None)
    assert file1 is not None
    assert file1.size == 100
    assert file1.extension == ".txt"


def test_upsert_files_duplicate_path(repository: SQLiteIndexRepository, scan_request: ScanRequest, file_entries: list[FileEntry]) -> None:
    """upsert_files 중복 경로 테스트 (ON CONFLICT DO UPDATE)."""
    run_id = repository.start_run(scan_request)
    
    # 첫 번째 삽입
    repository.upsert_files(run_id, file_entries)
    
    # 같은 경로를 다른 크기로 업데이트
    updated_entry = FileEntry(
        path=file_entries[0].path,
        size=999,  # 크기 변경
        mtime=file_entries[0].mtime,
        extension=file_entries[0].extension,
        is_hidden=file_entries[0].is_hidden,
        is_symlink=file_entries[0].is_symlink,
    )
    repository.upsert_files(run_id, [updated_entry])
    
    # 파일 수는 증가하지 않고 업데이트되어야 함
    files = repository.list_files(run_id)
    assert len(files) == len(file_entries)
    
    # 크기가 업데이트되었는지 확인
    file1 = next((f for f in files if f.path.name == "file1.txt"), None)
    assert file1 is not None
    assert file1.size == 999


def test_finalize_run(repository: SQLiteIndexRepository, scan_request: ScanRequest) -> None:
    """finalize_run 테스트."""
    run_id = repository.start_run(scan_request)
    
    summary = RunSummary(
        run_id=run_id,
        started_at=datetime.now(),
        finished_at=datetime.now(),
        root_path=scan_request.root_folder,
        options_json="{}",
        total_files=10,
        total_bytes=1000,
        elapsed_ms=5000,
        status="completed",
        error_message=None,
    )
    
    repository.finalize_run(run_id, summary)
    
    # Run이 완료되었는지 확인
    saved_summary = repository.get_run_summary(run_id)
    assert saved_summary is not None
    assert saved_summary.status == "completed"
    assert saved_summary.total_files == 10
    assert saved_summary.total_bytes == 1000
    assert saved_summary.elapsed_ms == 5000
    assert saved_summary.finished_at is not None


def test_get_latest_run_id(repository: SQLiteIndexRepository, scan_request: ScanRequest) -> None:
    """get_latest_run_id 테스트."""
    # 초기에는 None
    assert repository.get_latest_run_id() is None
    
    # Run 생성
    run_id1 = repository.start_run(scan_request)
    assert repository.get_latest_run_id() == run_id1
    
    # 두 번째 Run 생성
    run_id2 = repository.start_run(scan_request)
    assert repository.get_latest_run_id() == run_id2
    assert run_id2 > run_id1


def test_get_run_summary(repository: SQLiteIndexRepository, scan_request: ScanRequest) -> None:
    """get_run_summary 테스트."""
    run_id = repository.start_run(scan_request)
    
    summary = repository.get_run_summary(run_id)
    assert summary is not None
    assert summary.run_id == run_id
    assert summary.status == "running"
    assert summary.root_path == scan_request.root_folder
    
    # 존재하지 않는 run_id
    assert repository.get_run_summary(99999) is None


def test_get_ext_distribution(repository: SQLiteIndexRepository, scan_request: ScanRequest, file_entries: list[FileEntry]) -> None:
    """get_ext_distribution 테스트."""
    run_id = repository.start_run(scan_request)
    repository.upsert_files(run_id, file_entries)
    
    distribution = repository.get_ext_distribution(run_id)
    
    # .txt: 3개 (file1, file2, .hidden)
    # .md: 1개 (file3)
    txt_stat = next((s for s in distribution if s.ext == ".txt"), None)
    md_stat = next((s for s in distribution if s.ext == ".md"), None)
    
    assert txt_stat is not None
    assert txt_stat.count == 3
    assert txt_stat.total_bytes == 100 + 200 + 50  # 350
    
    assert md_stat is not None
    assert md_stat.count == 1
    assert md_stat.total_bytes == 300


def test_list_files(repository: SQLiteIndexRepository, scan_request: ScanRequest, file_entries: list[FileEntry]) -> None:
    """list_files 기본 테스트."""
    run_id = repository.start_run(scan_request)
    repository.upsert_files(run_id, file_entries)
    
    files = repository.list_files(run_id)
    
    assert len(files) == len(file_entries)
    assert all(isinstance(f, FileEntry) for f in files)


def test_list_files_pagination(repository: SQLiteIndexRepository, scan_request: ScanRequest, file_entries: list[FileEntry]) -> None:
    """list_files 페이지네이션 테스트."""
    run_id = repository.start_run(scan_request)
    repository.upsert_files(run_id, file_entries)
    
    # 첫 페이지 (limit=2)
    page1 = repository.list_files(run_id, offset=0, limit=2)
    assert len(page1) == 2
    
    # 두 번째 페이지
    page2 = repository.list_files(run_id, offset=2, limit=2)
    assert len(page2) == 2
    
    # 세 번째 페이지 (빈 페이지)
    page3 = repository.list_files(run_id, offset=4, limit=2)
    assert len(page3) == 0


def test_list_files_with_filters(repository: SQLiteIndexRepository, scan_request: ScanRequest, file_entries: list[FileEntry]) -> None:
    """list_files 필터 테스트."""
    run_id = repository.start_run(scan_request)
    repository.upsert_files(run_id, file_entries)
    
    # 확장자 필터
    txt_files = repository.list_files(run_id, ext=".txt")
    assert len(txt_files) == 3  # file1, file2, .hidden
    assert all(f.extension == ".txt" for f in txt_files)
    
    # 크기 필터
    large_files = repository.list_files(run_id, min_size=200)
    assert len(large_files) == 2  # file2 (200), file3 (300)
    
    small_files = repository.list_files(run_id, max_size=100)
    assert len(small_files) == 2  # file1 (100), .hidden (50)
    
    # 복합 필터
    filtered = repository.list_files(run_id, ext=".txt", min_size=100)
    assert len(filtered) == 2  # file1, file2 (100 이상)


def test_list_files_order_by(repository: SQLiteIndexRepository, scan_request: ScanRequest, file_entries: list[FileEntry]) -> None:
    """list_files 정렬 테스트."""
    run_id = repository.start_run(scan_request)
    repository.upsert_files(run_id, file_entries)
    
    # 크기 내림차순
    files_by_size = repository.list_files(run_id, order_by="size_desc")
    assert len(files_by_size) > 0
    sizes = [f.size for f in files_by_size]
    assert sizes == sorted(sizes, reverse=True)
    
    # 유효하지 않은 order_by
    with pytest.raises(ValueError, match="Invalid order_by"):
        repository.list_files(run_id, order_by="invalid")


def test_close(repository: SQLiteIndexRepository) -> None:
    """close 테스트 (리소스 정리)."""
    # close는 아무 동작도 하지 않지만 호출 시 에러가 없어야 함
    repository.close()  # 정상 종료되어야 함
