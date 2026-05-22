"""Tests for WorkFileDock."""

from gui.models.file_data_store import FileDataStore
from gui.views.components.file_list_table import FileListTableWidget
from gui.views.work.work_file_dock import WorkFileDock


def test_dock_collapsed_by_default(qapp) -> None:
    table = FileListTableWidget(FileDataStore())
    dock = WorkFileDock(table)
    assert dock.is_collapsed()
    assert not table.isVisible()
