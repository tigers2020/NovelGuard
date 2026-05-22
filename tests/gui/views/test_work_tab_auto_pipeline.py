"""Rev. 3.9 regression: auto pipeline only, slim sections retained."""

from pathlib import Path

from PySide6.QtWidgets import QPushButton

from gui.models.app_state import AppState
from gui.views.work.sections.library_section import LibrarySection
from gui.views.work.wizard_footer import WizardFooter
from gui.views.work.work_tab import WorkTab


def _button_texts(widget) -> list[str]:
    return [b.text() for b in widget.findChildren(QPushButton)]


def test_work_tab_has_run_all_primary(qapp) -> None:
    tab = WorkTab(app_state=AppState())
    assert "전체 작업 실행" in _button_texts(tab)
    assert "현재 단계 실행" not in _button_texts(tab)


def test_work_tab_wires_auto_pipeline(qapp) -> None:
    import gui.views.work.work_tab as work_tab_module

    source = Path(work_tab_module.__file__).read_text(encoding="utf-8")
    assert "WorkPipelineRunner" in source
    assert "PipelineRunConfirmSheet" in source
    assert "compute_pipeline_run_preview" in source
    assert "execute_step_requested" not in source
    assert "_on_execute_step" not in source


def test_library_section_has_no_folder_or_scan_buttons(qapp) -> None:
    section = LibrarySection()
    texts = _button_texts(section)
    assert "폴더 선택" not in texts
    assert "전체 스캔" not in texts


def test_footer_prev_next_enabled_while_pipeline_running(qapp) -> None:
    footer = WizardFooter()
    footer.show()
    footer.set_prev_enabled(True)
    footer.set_next_enabled(True)
    footer.set_pipeline_running(True)
    assert footer._prev_btn.isEnabled()
    assert footer._next_btn.isEnabled()
    assert footer._run_btn.isHidden()
    assert not footer._cancel_btn.isHidden()


def test_work_tab_has_confirm_stack(qapp) -> None:
    tab = WorkTab(app_state=AppState())
    assert hasattr(tab, "_wizard_column")
    assert hasattr(tab, "_confirm_sheet")
    assert tab._wizard_column.count() == 2


def test_sync_folder_state_enables_run_after_app_state_folder(qapp, tmp_path) -> None:
    folder = tmp_path / "novels"
    folder.mkdir()
    state = AppState(scan_folder=str(folder))
    tab = WorkTab(app_state=state)
    assert tab._footer._run_btn.isEnabled()
    assert tab._library_section_widget.get_scan_folder() == folder
