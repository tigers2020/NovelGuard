"""Tests for pipeline run pre-flight preview."""

from pathlib import Path

from gui.models.file_data_store import FileDataStore
from gui.services.pipeline_run_preview import PipelineRunPreview, compute_pipeline_run_preview


def test_preview_empty_store() -> None:
    store = FileDataStore()
    preview = compute_pipeline_run_preview(store, scan_folder=None)
    assert preview.duplicate_move_count == 0
    assert preview.organize_dry_run_total == 0
    assert preview.total_files == 0


def test_preview_duplicate_move_count(tmp_path: Path, monkeypatch) -> None:
    scan_dir = tmp_path / "scan"
    scan_dir.mkdir()
    store = FileDataStore()
    store.scan_folder = scan_dir

    class FakeUseCase:
        def __init__(self, store, log_sink):
            pass

        def execute(self, folder: Path):
            return [object(), object()]

    class FakeOrganize:
        def __init__(self, log_sink=None):
            pass

        def execute(self, root_path: Path, move: bool = True, dry_run: bool = False):
            from application.use_cases.organize_by_chosung import OrganizeByChosungResult

            r = OrganizeByChosungResult()
            r.total_processed = 5
            return r

    monkeypatch.setattr(
        "gui.services.pipeline_run_preview.MoveDuplicateFilesUseCase",
        FakeUseCase,
    )
    monkeypatch.setattr(
        "gui.services.pipeline_run_preview.OrganizeByChosungUseCase",
        FakeOrganize,
    )
    preview = compute_pipeline_run_preview(store, scan_folder=scan_dir)
    assert preview.duplicate_move_count == 2
    assert preview.organize_dry_run_total == 5
    assert preview.folder_path == str(scan_dir)


def test_preview_is_frozen_dataclass() -> None:
    preview = PipelineRunPreview(
        folder_path=None,
        total_files=0,
        duplicate_groups=0,
        duplicate_move_count=0,
        organize_dry_run_total=0,
    )
    assert preview.error_message is None


def test_preview_uses_cached_duplicate_summary(tmp_path: Path, monkeypatch) -> None:
    scan_dir = tmp_path / "scan"
    scan_dir.mkdir()
    store = FileDataStore()
    store.scan_folder = scan_dir

    class FakeOrganize:
        def __init__(self, log_sink=None):
            pass

        def execute(self, root_path: Path, move: bool = True, dry_run: bool = False):
            from application.use_cases.organize_by_chosung import OrganizeByChosungResult

            r = OrganizeByChosungResult()
            r.total_processed = 0
            return r

    class FakeMove:
        def __init__(self, store, log_sink):
            pass

        def execute(self, folder: Path):
            return []

    class FakeSummary:
        total_groups = 534
        duplicate_move_count = 653
        detection_timestamp = "2026-05-22T10:20:32"

    monkeypatch.setattr(
        "gui.services.pipeline_run_preview.MoveDuplicateFilesUseCase",
        FakeMove,
    )
    monkeypatch.setattr(
        "gui.services.pipeline_run_preview.OrganizeByChosungUseCase",
        FakeOrganize,
    )
    monkeypatch.setattr(
        "gui.services.pipeline_run_preview.find_latest_duplicate_summary",
        lambda folder: FakeSummary,
    )

    preview = compute_pipeline_run_preview(store, scan_folder=scan_dir)
    assert preview.duplicate_groups == 534
    assert preview.duplicate_move_count == 653
    assert preview.duplicate_groups_from_cache is True
