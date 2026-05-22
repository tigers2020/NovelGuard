"""WorkTab section collapse defaults."""

from gui.views.work.work_tab import WorkTab


def test_work_tab_move_and_quality_collapsed_by_default(qapp) -> None:
    tab = WorkTab()
    assert not tab.section("move").is_expanded()
    assert not tab.section("quality").is_expanded()
    assert tab.section("library").is_expanded()


def test_work_tab_scroll_to_section_expands(qapp) -> None:
    tab = WorkTab()
    tab.scroll_to_section("move")
    assert tab.section("move").is_expanded()
