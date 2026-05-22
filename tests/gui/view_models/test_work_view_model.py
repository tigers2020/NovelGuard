"""WorkViewModel summary tests."""

from gui.models.app_state import AppState
from gui.view_models.work_view_model import WorkViewModel


def test_work_view_model_library_idle_without_folder(qapp) -> None:
    state = AppState()
    vm = WorkViewModel(app_state=state, job_manager=None, log_sink=None)
    snap = vm.build_summary()
    assert snap.folder_path is None
    assert snap.library_state == "idle"
