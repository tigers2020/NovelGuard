"""Single work surface: library, duplicate, move, quality sections."""

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from application.ports.index_repository import IIndexRepository
from application.ports.log_sink import ILogSink
from gui.view_models.work_view_model import WorkViewModel
from gui.views.work.sections.duplicate_section import DuplicateSection
from gui.views.work.sections.library_section import LibrarySection
from gui.views.work.sections.move_section import MoveSection
from gui.views.work.sections.quality_section import QualitySection
from gui.views.work.sections.summary_strip import SummaryStrip
from gui.views.work.work_section import WorkSection


class WorkTab(QWidget):
    """Main work screen (default stack page)."""

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

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(32, 32, 32, 32)
        content_layout.setSpacing(16)

        self._sections: dict[str, WorkSection] = {}

        self._summary_strip = SummaryStrip(on_jump=self.scroll_to_section)
        content_layout.addWidget(self._summary_strip)

        self._library_section_widget = LibrarySection(
            self, job_manager=job_manager, log_sink=log_sink
        )
        library = WorkSection("library", "라이브러리", expanded=True)
        library.body_layout.addWidget(self._library_section_widget)
        self._register_section(content_layout, library)

        self._duplicate_section_widget = DuplicateSection(
            self,
            job_manager=job_manager,
            index_repository=index_repository,
            log_sink=log_sink,
            on_groups_found=lambda: self.section("duplicate").set_expanded(True),
        )
        duplicate = WorkSection("duplicate", "중복 정리", expanded=False)
        duplicate.body_layout.addWidget(self._duplicate_section_widget)
        self._register_section(content_layout, duplicate)

        self._move_section_widget = MoveSection(self, log_sink=log_sink)
        move = WorkSection("move", "이동·구조", expanded=False)
        move.body_layout.addWidget(self._move_section_widget)
        self._register_section(content_layout, move)

        quality_inner = QualitySection(self)
        quality = WorkSection("quality", "품질 점검", expanded=False)
        quality.body_layout.addWidget(quality_inner)
        self._register_section(content_layout, quality)

        content_layout.addStretch()
        scroll.setWidget(content)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(scroll)

        self._work_vm: Optional[WorkViewModel] = None
        if app_state is not None:
            self._work_vm = WorkViewModel(app_state, job_manager=job_manager, log_sink=log_sink)
            self._work_vm.summary_changed.connect(self._summary_strip.update_summary)
            self._work_vm.refresh()

    @property
    def library_section(self) -> LibrarySection:
        return self._library_section_widget

    def bind_work_view_model(self, work_vm: WorkViewModel) -> None:
        self._work_vm = work_vm
        self._work_vm.summary_changed.connect(self._summary_strip.update_summary)
        self._work_vm.refresh()

    def _register_section(self, layout: QVBoxLayout, section: WorkSection) -> None:
        self._sections[section.section_id] = section
        layout.addWidget(section)

    def section(self, section_id: str) -> WorkSection:
        return self._sections[section_id]

    def scroll_to_section(self, section_id: str) -> None:
        section = self._sections.get(section_id)
        if section is None:
            return
        section.set_expanded(True)
        scroll = self.findChild(QScrollArea)
        if scroll is not None:
            scroll.ensureWidgetVisible(section)

    def refresh_move_folder(self) -> None:
        self._move_section_widget.refresh_folder()
