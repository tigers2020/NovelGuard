"""WorkTab rev. 3.2 wizard layout smoke tests."""

from gui.models.app_state import AppState
from gui.views.work.work_tab import WorkTab


def test_work_tab_has_footer_not_context_run(qapp) -> None:
    tab = WorkTab(app_state=AppState())
    assert hasattr(tab, "_footer")
    assert hasattr(tab, "_compact_bar")
    assert not hasattr(tab, "_context_bar")


def test_work_tab_splitter_and_dock_after_table(qapp) -> None:
    from gui.models.file_data_store import FileDataStore
    from gui.views.components.file_list_table import FileListTableWidget

    tab = WorkTab(app_state=AppState())
    table = FileListTableWidget(FileDataStore(), tab)
    tab.set_file_list_table(table)
    assert tab._file_dock is not None
    assert tab._file_dock.is_collapsed()
    assert tab._main_splitter.count() == 2
