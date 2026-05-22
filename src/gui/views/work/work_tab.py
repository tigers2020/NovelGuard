"""Single work surface: wizard shell + collapsible file dock (rev. 3.2)."""

from __future__ import annotations

from pathlib import Path
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
from gui.services.pipeline_run_preview import compute_pipeline_run_preview
from gui.services.work_pipeline_runner import WorkPipelineRunner
from gui.services.work_stats import compute_work_stats
from gui.view_models.work_pipeline_dto import STEP_ORDER, StepId
from gui.view_models.work_pipeline_view_model import WorkPipelineViewModel
from gui.view_models.work_view_model import WorkViewModel
from gui.views.work.pipeline_run_confirm_sheet import PipelineRunConfirmSheet
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
        self._pending_run_folder: Path | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(32, 24, 32, 24)
        root.setSpacing(0)

        self._main_splitter = QSplitter(Qt.Orientation.Vertical)
        self._main_splitter.setObjectName("workWizardSplitter")

        self._wizard_column = QStackedWidget()
        self._wizard_page = QWidget()
        wizard_layout = QVBoxLayout(self._wizard_page)
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

        self._confirm_sheet = PipelineRunConfirmSheet()
        self._wizard_column.addWidget(self._wizard_page)
        self._wizard_column.addWidget(self._confirm_sheet)

        self._file_dock: Optional[WorkFileDock] = None
        self._main_splitter.addWidget(self._wizard_column)
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
        self._pipeline_runner: Optional[WorkPipelineRunner] = None
        self._main_window = None

        if app_state is not None:
            self._work_vm = WorkViewModel(app_state, job_manager=job_manager, log_sink=log_sink)
            self._work_vm.summary_changed.connect(self._on_summary_changed)
            self._work_vm.refresh()
            self._refresh_pipeline_snapshot()

        self.set_active_step(StepId.SCAN.value)
        self._compact_bar.folder_change_requested.connect(self._on_folder_change_requested)
        self._compact_bar.rescan_requested.connect(self._library_section_widget.request_full_scan)
        self._footer.prev_clicked.connect(self._on_prev_step)
        self._footer.next_clicked.connect(self._on_next_step)
        self._footer.run_pipeline_requested.connect(self._on_run_pipeline_requested)
        self._footer.cancel_pipeline_requested.connect(self._on_cancel_pipeline)
        self._confirm_sheet.confirmed.connect(self._on_confirm_sheet_confirmed)
        self._confirm_sheet.cancelled.connect(self._on_confirm_sheet_cancelled)

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
        self._main_window = main_window
        self._pipeline_runner = WorkPipelineRunner(
            main_window=main_window,
            library=self._library_section_widget,
            duplicate=self._duplicate_section_widget,
            move=self._move_section_widget,
            finalize=self._finalize_section_widget,
            parent=self,
        )
        self._pipeline_runner.progress_changed.connect(self._footer.update_pipeline_progress)
        self._pipeline_runner.progress_changed.connect(
            lambda _: self._footer.set_pipeline_running(True)
        )
        self._pipeline_runner.step_changed.connect(self.set_active_step)
        self._pipeline_runner.flags_changed.connect(self._on_runner_flags_changed)
        self._pipeline_runner.finished.connect(self._on_pipeline_finished)

    def bind_work_view_model(self, work_vm: WorkViewModel) -> None:
        self._work_vm = work_vm
        self._work_vm.summary_changed.connect(self._on_summary_changed)
        self._work_vm.refresh()

    def set_active_step(self, step_id: str) -> None:
        self._current_step_id = step_id
        index = self._step_index_by_id.get(step_id, 0)
        self._wizard_column.setCurrentWidget(self._wizard_page)
        self._step_stack.setCurrentIndex(index)
        self._stepper.set_active_step(step_id)
        self._update_footer_nav()
        self._refresh_pipeline_snapshot(active_step_id=step_id)

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

    def _on_duplicate_groups_found(self) -> None:
        self._completion_flags["duplicate_done"] = True
        self._refresh_pipeline_snapshot()

    def _on_runner_flags_changed(self) -> None:
        if self._pipeline_runner:
            self._completion_flags.update(self._pipeline_runner.flags)
            self._refresh_pipeline_snapshot()

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

    def _on_folder_change_requested(self) -> None:
        self._library_section_widget._on_select_folder()

    def _on_run_pipeline_requested(self) -> None:
        if not self._pipeline_runner or not self._app_state:
            return
        folder = self._library_section_widget.get_scan_folder()
        if not folder:
            from PySide6.QtWidgets import QMessageBox

            QMessageBox.warning(self, "폴더 필요", "먼저 스캔할 폴더를 선택하세요.")
            return
        preview = compute_pipeline_run_preview(
            self._app_state.file_data_store,
            scan_folder=folder,
            log_sink=self._log_sink,
        )
        self._pending_run_folder = folder
        self._confirm_sheet.set_preview(preview)
        self._wizard_column.setCurrentWidget(self._confirm_sheet)

    def _on_confirm_sheet_confirmed(self) -> None:
        if not self._pipeline_runner or self._pending_run_folder is None:
            return
        self._wizard_column.setCurrentWidget(self._wizard_page)
        self._footer.set_pipeline_running(True)
        self._compact_bar.set_actions_enabled(False)
        self._pipeline_runner.start(self._pending_run_folder, auto_run=True)
        self._pending_run_folder = None

    def _on_confirm_sheet_cancelled(self) -> None:
        self._pending_run_folder = None
        self._wizard_column.setCurrentWidget(self._wizard_page)

    def _on_cancel_pipeline(self) -> None:
        if self._pipeline_runner:
            self._pipeline_runner.cancel()

    def _on_pipeline_finished(self, status: str) -> None:
        self._footer.set_pipeline_running(False)
        self._footer.update_pipeline_progress(None)
        self._compact_bar.set_actions_enabled(True)
        self._wizard_column.setCurrentWidget(self._wizard_page)
        if status == "completed":
            self._completion_flags["scan_done"] = True
            if self._pipeline_runner:
                self._completion_flags.update(self._pipeline_runner.flags)
        self._refresh_pipeline_snapshot()
        if self._work_vm:
            self._work_vm.refresh()

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
