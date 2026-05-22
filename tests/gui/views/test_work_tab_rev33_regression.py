"""Rev. 3.3 regression: step-only execution, no duplicate CTAs."""

from pathlib import Path

from PySide6.QtWidgets import QPushButton

from gui.models.app_state import AppState
from gui.view_models.work_pipeline_dto import StepId
from gui.views.work.sections.library_section import LibrarySection
from gui.views.work.wizard_footer import WizardFooter
from gui.views.work.work_tab import WorkTab


def _button_texts(widget) -> list[str]:
    return [b.text() for b in widget.findChildren(QPushButton)]


def test_work_tab_has_no_run_all_pipeline_cta(qapp) -> None:
    tab = WorkTab(app_state=AppState())
    texts = _button_texts(tab)
    assert "전체 작업 실행" not in texts


def test_library_section_has_no_folder_or_scan_buttons(qapp) -> None:
    section = LibrarySection()
    texts = _button_texts(section)
    assert "폴더 선택" not in texts
    assert "전체 스캔" not in texts
    assert "중지" not in texts


def test_footer_primary_label_follows_step(qapp, tmp_path) -> None:
    tab = WorkTab(app_state=AppState())
    tab.library_section.set_scan_folder(tmp_path)
    tab.set_active_step(StepId.SCAN.value)
    tab._refresh_footer()
    assert tab.footer._execute_btn.text() == "스캔 실행"

    tab._completion_flags["scan_done"] = True
    tab.set_active_step(StepId.DUPLICATE.value)
    tab._refresh_footer()
    assert tab.footer._execute_btn.text() == "중복 탐지"


def test_footer_hides_primary_while_running(qapp) -> None:
    footer = WizardFooter()
    footer.show()
    footer.set_step_running(True)
    assert footer._execute_btn.isHidden()
    assert not footer._cancel_btn.isHidden()


def test_work_tab_does_not_import_confirm_sheet() -> None:
    import gui.views.work.work_tab as work_tab_module

    source = Path(work_tab_module.__file__).read_text(encoding="utf-8")
    assert "pipeline_run_confirm_sheet" not in source
    assert "PipelineRunConfirmSheet" not in source
    assert "compute_pipeline_run_preview" not in source
    assert "WorkPipelineRunner" not in source
