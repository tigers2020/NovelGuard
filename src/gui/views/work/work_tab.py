"""Single work surface: wizard shell + collapsible file dock (rev. 3.3)."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QSettings, Qt
from PySide6.QtWidgets import (
    QScrollArea,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from application.ports.index_repository import IIndexRepository
from application.ports.log_sink import ILogSink
from gui.services.work_stats import compute_work_stats
from gui.view_models.work_pipeline_dto import STEP_ORDER, StepId
from gui.view_models.work_pipeline_view_model import WorkPipelineViewModel
from gui.view_models.work_view_model import WorkViewModel
from gui.views.work.pipeline_stepper import PipelineStepper
from gui.views.work.sections.duplicate_section import DuplicateSection
from gui.views.work.sections.finalize_section import FinalizeSection
from gui.views.work.sections.library_section import LibrarySection
from gui.views.work.sections.move_section import MoveSection
from gui.views.work.wizard_footer import WizardFooter
from gui.views.work.work_compact_bar import WorkCompactBar
from gui.views.work.work_file_dock import WorkFileDock

_SETTINGS_SPLITTER = "ui/work_wizard_splitter"
_SETTINGS_DOCK_EXPANDED = "ui/work_file_dock_expanded"

_STEP_LABELS = {
    StepId.SCAN.value: "스캔",
    StepId.DUPLICATE.value: "중복 정리",
    StepId.MOVE.value: "이동 계획",
    StepId.FINALIZE.value: "적용 · 검증",
}


class WorkTab(QWidget):
    """Main work screen: compact bar, stepper, stacked steps, footer, file dock."""

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        job_manager=None,
        index_repository: Optional[IIndexRepository] = None,
        log_sink: Optional[ILogSink] = None,
        app_state=None,
    ) -> None:
        super().__init__(parent)
        self.setProperty("tab_name", "work")
        self._app_state = app_state
        self._log_sink = log_sink
        self._settings = QSettings()
        self._current_step_id = StepId.SCAN.value
        self._duplicate_phase = "detect"

        root = QVBoxLayout(self)
        root.setContentsMargins(32, 24, 32, 24)
        root.setSpacing(0)

        self._main_splitter = QSplitter(Qt.Orientation.Vertical)
        self._main_splitter.setObjectName("workWizardSplitter")

        wizard_page = QWidget()
        wizard_layout = QVBoxLayout(wizard_page)
        wizard_layout.setContentsMargins(0, 0, 0, 0)
        wizard_layout.setSpacing(16)

        self._compact_bar = WorkCompactBar()
        wizard_layout.addWidget(self._compact_bar)

        self._stepper = PipelineStepper()
        self._stepper.step_clicked.connect(self._on_stepper_clicked)
        wizard_layout.addWidget(self._stepper)

        self._step_stack = QStackedWidget()
        self._step_stack.setObjectName("pipelineStepStack")
        wizard_layout.addWidget(self._step_stack, stretch=1)

        self._footer = WizardFooter()
        wizard_layout.addWidget(self._footer)

        self._file_dock: Optional[WorkFileDock] = None
        self._main_splitter.addWidget(wizard_page)
        root.addWidget(self._main_splitter, stretch=1)

        self._pipeline_vm = WorkPipelineViewModel(app_state) if app_state else None
        self._completion_flags = {
            "scan_done": False,
            "duplicate_done": False,
            "duplicate_skipped": False,
            "move_done": False,
            "move_skipped": False,
        }
        self._step_index_by_id = {s.value: i for i, s in enumerate(STEP_ORDER)}

        self._library_section_widget = LibrarySection(
            self, job_manager=job_manager, log_sink=log_sink
        )
        self._duplicate_section_widget = DuplicateSection(
            self,
            job_manager=job_manager,
            index_repository=index_repository,
            log_sink=log_sink,
            on_groups_found=lambda: self._on_duplicate_groups_found(),
        )
        self._move_section_widget = MoveSection(self, log_sink=log_sink)
        self._finalize_section_widget = FinalizeSection(self, log_sink=log_sink)

        self._register_step_page(StepId.SCAN.value, self._library_section_widget)
        self._register_step_page(StepId.DUPLICATE.value, self._duplicate_section_widget)
        self._register_step_page(StepId.MOVE.value, self._move_section_widget)
        self._register_step_page(StepId.FINALIZE.value, self._finalize_section_widget)

        self._work_vm: Optional[WorkViewModel] = None

        if app_state is not None:
            self._work_vm = WorkViewModel(app_state, job_manager=job_manager, log_sink=log_sink)
            self._work_vm.summary_changed.connect(self._on_summary_changed)
            self._work_vm.refresh()
            self._refresh_pipeline_snapshot()

        self.set_active_step(StepId.SCAN.value)
        self._compact_bar.folder_change_requested.connect(
            self._library_section_widget.select_folder
        )
        self._compact_bar.rescan_requested.connect(self._library_section_widget.request_full_scan)
        self._footer.prev_clicked.connect(self._on_prev_step)
        self._footer.next_clicked.connect(self._on_next_step)
        self._footer.execute_step_requested.connect(self._on_execute_step)
        self._footer.cancel_step_requested.connect(self._on_cancel_step)
        self._library_section_widget.scan_completed.connect(self._on_scan_completed)
        self._library_section_widget.folder_selected.connect(lambda _: self._refresh_footer())
        lib_vm = self._library_section_widget.scan_view_model
        lib_vm.progress_updated.connect(lambda *_: self._refresh_footer())
        lib_vm.scan_error.connect(self._on_step_job_finished)
        dup_vm = self._duplicate_section_widget.duplicate_view_model
        dup_vm.duplicate_completed.connect(self._on_duplicate_detection_finished)
        dup_vm.duplicate_error.connect(self._on_step_job_finished)
        dup_vm.progress_updated.connect(lambda *_: self._refresh_footer())
        self._duplicate_section_widget.pipeline_apply_finished.connect(
            self._on_duplicate_apply_finished
        )

        self._main_splitter.splitterMoved.connect(self._save_splitter_state)

    def set_file_list_table(self, table_widget: QWidget) -> None:
        """Attach file list table as collapsible bottom dock."""
        if self._file_dock is not None:
            return
        self._file_dock = WorkFileDock(table_widget, self)
        self._file_dock.bind_splitter(self._main_splitter)
        self._main_splitter.addWidget(self._file_dock)
        self._main_splitter.setStretchFactor(0, 9)
        self._main_splitter.setStretchFactor(1, 1)
        self._file_dock.collapse()
        self._file_dock.collapsed_changed.connect(lambda _: self._save_splitter_state())
        self._restore_layout_settings()
        if self._app_state:
            count = len(self._app_state.file_data_store.get_all_files())
            self._file_dock.set_file_count(count)

    def _register_step_page(self, step_id: str, body: QWidget) -> None:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        page = QWidget()
        page.setObjectName(f"pipelineStepPage_{step_id}")
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(8, 8, 8, 8)
        page_layout.addWidget(body)
        scroll.setWidget(page)
        self._step_stack.addWidget(scroll)

    @property
    def compact_bar(self) -> WorkCompactBar:
        return self._compact_bar

    @property
    def footer(self) -> WizardFooter:
        return self._footer

    @property
    def library_section(self) -> LibrarySection:
        return self._library_section_widget

    def bind_main_window(self, main_window) -> None:
        """Reserved for future main-window hooks (rev. 3.3: no auto-pipeline)."""
        _ = main_window

    def bind_work_view_model(self, work_vm: WorkViewModel) -> None:
        self._work_vm = work_vm
        self._work_vm.summary_changed.connect(self._on_summary_changed)
        self._work_vm.refresh()

    def set_active_step(self, step_id: str) -> None:
        self._current_step_id = step_id
        index = self._step_index_by_id.get(step_id, 0)
        self._step_stack.setCurrentIndex(index)
        self._stepper.set_active_step(step_id)
        self._update_footer_nav()
        self._refresh_pipeline_snapshot(active_step_id=step_id)
        self._refresh_footer()

    def _update_footer_nav(self) -> None:
        step_ids = [s.value for s in STEP_ORDER]
        idx = step_ids.index(self._current_step_id)
        self._footer.set_prev_enabled(idx > 0 and self._stepper.is_step_enabled(step_ids[idx - 1]))
        can_next = idx < len(step_ids) - 1 and self._stepper.is_step_enabled(step_ids[idx + 1])
        self._footer.set_next_enabled(can_next)

    def _on_stepper_clicked(self, step_id: str) -> None:
        self.set_active_step(step_id)

    def _on_prev_step(self) -> None:
        step_ids = [s.value for s in STEP_ORDER]
        idx = step_ids.index(self._current_step_id)
        if idx > 0:
            self.set_active_step(step_ids[idx - 1])

    def _on_next_step(self) -> None:
        step_ids = [s.value for s in STEP_ORDER]
        idx = step_ids.index(self._current_step_id)
        if idx < len(step_ids) - 1:
            next_id = step_ids[idx + 1]
            if self._stepper.is_step_enabled(next_id):
                self.set_active_step(next_id)

    def _on_scan_completed(self) -> None:
        self._completion_flags["scan_done"] = True
        self._footer.set_step_running(False)
        self._compact_bar.set_actions_enabled(True)
        self._refresh_pipeline_snapshot()
        self._refresh_footer()
        if self._work_vm:
            self._work_vm.refresh()

    def _on_duplicate_groups_found(self) -> None:
        self._completion_flags["duplicate_done"] = True
        self._duplicate_phase = "detect"
        self._refresh_pipeline_snapshot()
        self._refresh_footer()

    def _on_duplicate_apply_finished(self, success: bool) -> None:
        self._footer.set_step_running(False)
        self._compact_bar.set_actions_enabled(True)
        if success:
            self._completion_flags["duplicate_done"] = True
            self._duplicate_phase = "detect"
        self._refresh_pipeline_snapshot()
        self._refresh_footer()

    def _on_summary_changed(self, summary) -> None:
        size_gb = 0.0
        file_count = 0
        if self._app_state:
            stats = compute_work_stats(self._app_state.file_data_store)
            size_gb = stats.total_size_gb
            file_count = stats.total_files
        self._compact_bar.update_summary(summary, total_size_gb=size_gb)
        if self._file_dock:
            self._file_dock.set_file_count(file_count)
        self._refresh_footer()

    def _refresh_pipeline_snapshot(self, active_step_id: str | None = None) -> None:
        if not self._pipeline_vm:
            return
        snap = self._pipeline_vm.build_snapshot(
            scan_done=self._completion_flags["scan_done"],
            duplicate_done=self._completion_flags["duplicate_done"],
            duplicate_skipped=self._completion_flags["duplicate_skipped"],
            move_done=self._completion_flags["move_done"],
            move_skipped=self._completion_flags["move_skipped"],
            active_step_id=active_step_id,
        )
        for step_id in self._step_index_by_id:
            state = snap.steps.get(step_id, "locked")
            if active_step_id == step_id and state in ("ready", "running"):
                state = "running"
            self._stepper.set_step_state(step_id, state)
        self._update_footer_nav()

    def _is_step_running(self) -> bool:
        lib = self._library_section_widget
        dup = self._duplicate_section_widget
        if self._current_step_id == StepId.SCAN.value:
            return lib.scan_view_model.is_scanning
        if self._current_step_id == StepId.DUPLICATE.value:
            return dup.duplicate_view_model.is_detecting or dup.is_apply_running()
        return False

    def _refresh_footer(self) -> None:
        step_ids = [s.value for s in STEP_ORDER]
        idx = step_ids.index(self._current_step_id)
        step_no = idx + 1
        label = _STEP_LABELS.get(self._current_step_id, "")
        detail = self._footer_action_detail()
        self._footer.set_summary(f"{step_no}/4 · {label} · {detail}")

        if self._is_step_running():
            self._footer.set_step_running(True)
            self._footer.set_step_progress(detail)
            return

        self._footer.set_step_running(False)
        execute_label, enabled = self._footer_execute_state()
        self._footer.set_execute_label(execute_label)
        self._footer.set_execute_enabled(enabled)

    def _footer_action_detail(self) -> str:
        if not self._library_section_widget.get_scan_folder():
            return "폴더를 선택하세요"
        if self._current_step_id == StepId.SCAN.value:
            if self._completion_flags["scan_done"]:
                return "마지막 스캔 결과 사용 가능"
            return "스캔 대기"
        if self._current_step_id == StepId.DUPLICATE.value:
            if self._duplicate_phase == "apply":
                return "중복 적용 대기"
            if self._duplicate_section_widget.has_detection_results():
                return "탐지 완료 · 적용 가능"
            return "중복 탐지 대기"
        if self._current_step_id == StepId.MOVE.value:
            return "이동·복사 계획"
        return "적용 및 무결성 검사"

    def _footer_execute_state(self) -> tuple[str, bool]:
        folder = self._library_section_widget.get_scan_folder()
        if not folder:
            return "현재 단계 실행", False

        step = self._current_step_id
        if step == StepId.SCAN.value:
            return "스캔 실행", True
        if step == StepId.DUPLICATE.value:
            if not self._completion_flags["scan_done"]:
                return "중복 탐지", False
            if self._completion_flags["duplicate_done"]:
                return "적용하기", False
            if self._duplicate_phase == "apply":
                return "적용하기", True
            return "중복 탐지", True
        if step == StepId.MOVE.value:
            if not (
                self._completion_flags["duplicate_done"]
                or self._completion_flags["duplicate_skipped"]
            ):
                return "정리 실행", False
            return "정리 실행", True
        if step == StepId.FINALIZE.value:
            if not (self._completion_flags["move_done"] or self._completion_flags["move_skipped"]):
                return "적용·검증", False
            return "적용·검증", True
        return "현재 단계 실행", False

    def _on_execute_step(self) -> None:
        from PySide6.QtWidgets import QMessageBox

        step = self._current_step_id
        if step == StepId.SCAN.value:
            if not self._library_section_widget.get_scan_folder():
                QMessageBox.warning(self, "폴더 필요", "먼저 스캔할 폴더를 선택하세요.")
                return
            self._footer.set_step_running(True)
            self._compact_bar.set_actions_enabled(False)
            self._footer.set_step_progress("스캔 실행 중…")
            self._library_section_widget.request_full_scan()
            self._refresh_footer()
            return

        if step == StepId.DUPLICATE.value:
            dup = self._duplicate_section_widget
            if self._duplicate_phase == "apply":
                self._footer.set_step_running(True)
                self._compact_bar.set_actions_enabled(False)
                self._footer.set_step_progress("중복 적용 중…")
                dup.apply_duplicates()
            else:
                self._footer.set_step_running(True)
                self._compact_bar.set_actions_enabled(False)
                self._footer.set_step_progress("중복 탐지 중…")
                dup.start_detection()
            self._refresh_footer()
            return

        if step == StepId.MOVE.value:
            self._footer.set_step_running(True)
            self._footer.set_step_progress("정리 실행 중…")
            ok = self._move_section_widget.execute_organize()
            self._footer.set_step_running(False)
            if ok:
                self._completion_flags["move_done"] = True
                self._refresh_pipeline_snapshot()
            self._refresh_footer()
            return

        if step == StepId.FINALIZE.value:
            self._footer.set_step_running(True)
            self._footer.set_step_progress("적용·검증 중…")
            self._finalize_section_widget.run_apply_and_integrity_auto(self)
            self._footer.set_step_running(False)
            self._refresh_footer()

    def _on_step_job_finished(self, _message: str = "") -> None:
        self._footer.set_step_running(False)
        self._compact_bar.set_actions_enabled(True)
        self._refresh_footer()

    def _on_duplicate_detection_finished(self, results: list) -> None:
        self._footer.set_step_running(False)
        self._compact_bar.set_actions_enabled(True)
        if not results:
            self._completion_flags["duplicate_skipped"] = True
            self._completion_flags["duplicate_done"] = True
            self._duplicate_phase = "detect"
        else:
            self._duplicate_phase = "apply"
        self._refresh_pipeline_snapshot()
        self._refresh_footer()

    def _on_cancel_step(self) -> None:
        if self._current_step_id == StepId.SCAN.value:
            self._library_section_widget.cancel_scan()
        elif self._current_step_id == StepId.DUPLICATE.value:
            dup = self._duplicate_section_widget
            if dup.duplicate_view_model.is_detecting:
                dup.duplicate_view_model.stop_duplicate_detection()
            else:
                dup.cancel_apply()
        self._footer.set_step_running(False)
        self._compact_bar.set_actions_enabled(True)
        self._refresh_footer()

    def expand_file_dock(self) -> None:
        if self._file_dock:
            self._file_dock.expand()

    def _restore_layout_settings(self) -> None:
        sizes = self._settings.value(_SETTINGS_SPLITTER)
        if isinstance(sizes, list) and len(sizes) >= 2:
            try:
                self._main_splitter.setSizes([int(s) for s in sizes])
            except (TypeError, ValueError):
                pass
        expanded = self._settings.value(_SETTINGS_DOCK_EXPANDED, False)
        if self._file_dock:
            if expanded in (True, "true", "1", 1):
                self._file_dock.expand()
            else:
                self._file_dock.collapse()

    def _save_splitter_state(self) -> None:
        self._settings.setValue(_SETTINGS_SPLITTER, self._main_splitter.sizes())
        if self._file_dock:
            self._settings.setValue(_SETTINGS_DOCK_EXPANDED, not self._file_dock.is_collapsed())

    def refresh_move_folder(self) -> None:
        self._move_section_widget.refresh_folder()
