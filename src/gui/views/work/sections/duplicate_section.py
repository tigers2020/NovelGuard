"""Duplicate detection section with groups table and evidence panel."""

import logging
from pathlib import Path
from typing import Any, Callable, Optional

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from application.dto.duplicate_group_result import DuplicateGroupResult
from application.ports.index_repository import IIndexRepository
from application.ports.job_runner import IJobRunner
from application.ports.log_sink import ILogSink
from application.use_cases.move_duplicate_files import MoveDuplicateFilesUseCase
from application.utils.duplicate_json import (
    generate_duplicate_json_filename,
    save_duplicate_result_to_json,
)
from gui.view_models.duplicate_view_model import DuplicateViewModel
from gui.views.components.dry_run_preview_dialog import DryRunPreviewDialog
from gui.views.components.duplicate_groups_table_view import DuplicateGroupsTableView
from gui.views.components.evidence_panel import EvidencePanel
from gui.views.work.app_context import get_app_state
from gui.workers.file_move_worker import FileMoveWorker

logger = logging.getLogger(__name__)


class DuplicateSection(QWidget):
    """Duplicate detect, dry-run, apply, groups + evidence."""

    pipeline_apply_finished = Signal(bool)

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        job_manager: Optional[IJobRunner] = None,
        index_repository: Optional[IIndexRepository] = None,
        log_sink: Optional[ILogSink] = None,
        on_groups_found: Optional[Callable[[], None]] = None,
    ) -> None:
        super().__init__(parent)
        self._log_sink = log_sink
        self._on_groups_found = on_groups_found
        self._app_state = get_app_state(self)
        self._move_worker: Optional[FileMoveWorker] = None
        self._view_model = DuplicateViewModel(
            parent=None,
            job_manager=job_manager,
            index_repository=index_repository,
            log_sink=log_sink,
        )
        self._view_model.setParent(self)
        self._view_model.progress_updated.connect(self._on_progress_updated)
        self._view_model.duplicate_completed.connect(self._on_duplicate_completed)
        self._view_model.duplicate_error.connect(self._on_duplicate_error)
        self._view_model.results_updated.connect(self._on_results_updated)
        self._pipeline_apply_pending = False
        self._build_ui()

    @property
    def duplicate_view_model(self) -> DuplicateViewModel:
        return self._view_model

    def request_detection(self) -> None:
        self._on_start_detection()

    def pipeline_dry_run_preview(self, parent: QWidget) -> bool:
        store = self._app_state.file_data_store
        scan_folder = store.scan_folder
        if not scan_folder:
            QMessageBox.warning(parent, "오류", "스캔 폴더가 설정되지 않았습니다.")
            return False
        use_case = MoveDuplicateFilesUseCase(store, self._log_sink)
        operations = use_case.execute(scan_folder)
        if not operations:
            return True
        dialog = DryRunPreviewDialog(operations, scan_folder, parent)
        return dialog.exec() == QDialog.DialogCode.Accepted

    def pipeline_start_apply(self, parent: QWidget) -> bool:
        store = self._app_state.file_data_store
        scan_folder = store.scan_folder
        if not scan_folder:
            QMessageBox.warning(parent, "오류", "스캔 폴더가 설정되지 않았습니다.")
            return False
        use_case = MoveDuplicateFilesUseCase(store, self._log_sink)
        operations = use_case.execute(scan_folder)
        if not operations:
            return False
        reply = QMessageBox.question(
            parent,
            "적용하기",
            f"총 {len(operations)}개 파일을 duplicate/ 폴더로 이동합니다.\n계속하시겠습니까?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return False
        self._pipeline_apply_pending = True
        self._move_worker = FileMoveWorker(use_case, scan_folder, self._log_sink, self)
        self._move_worker.move_completed.connect(self._on_move_completed)
        self._move_worker.move_error.connect(self._on_move_error)
        self._move_worker.start()
        self._progress_bar.setRange(0, 0)
        self._progress_info.setText("파일 이동 중...")
        return True

    def pipeline_apply_auto(self) -> bool:
        """Apply duplicate moves without confirmation (auto pipeline)."""
        store = self._app_state.file_data_store
        scan_folder = store.scan_folder
        if not scan_folder:
            return False
        use_case = MoveDuplicateFilesUseCase(store, self._log_sink)
        operations = use_case.execute(scan_folder)
        if not operations:
            return False
        self._pipeline_apply_pending = True
        self._move_worker = FileMoveWorker(use_case, scan_folder, self._log_sink, self)
        self._move_worker.move_completed.connect(self._on_move_completed)
        self._move_worker.move_error.connect(self._on_move_error)
        self._move_worker.start()
        self._progress_bar.setRange(0, 0)
        self._progress_info.setText(f"자동 적용 중… {len(operations)}건 → duplicate/")
        return True

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        action_bar = QHBoxLayout()
        action_bar.setSpacing(16)
        detect_btn = QPushButton("중복 탐지 시작")
        detect_btn.setObjectName("btnPrimary")
        detect_btn.clicked.connect(self._on_start_detection)
        action_bar.addWidget(detect_btn)
        dry_run_btn = QPushButton("Dry Run")
        dry_run_btn.setObjectName("btnSecondary")
        dry_run_btn.clicked.connect(self._on_dry_run)
        action_bar.addWidget(dry_run_btn)
        apply_btn = QPushButton("적용하기")
        apply_btn.setObjectName("btnSuccess")
        apply_btn.clicked.connect(self._on_apply)
        action_bar.addWidget(apply_btn)
        action_bar.addStretch()
        layout.addLayout(action_bar)

        self._progress_section = self._create_progress_section()
        layout.addWidget(self._progress_section)

        store = self._app_state.file_data_store
        self._groups_view = DuplicateGroupsTableView(self, file_data_store=store)
        self._groups_view.setMinimumHeight(240)
        self._groups_view.group_selected.connect(self._on_group_selected)
        layout.addWidget(self._groups_view)

        self._evidence_panel = EvidencePanel(self)
        layout.addWidget(self._evidence_panel)

    def _create_progress_section(self) -> QWidget:
        group = QWidget()
        group.setObjectName("pipelineProgressBlock")
        layout = QVBoxLayout(group)
        layout.setContentsMargins(12, 12, 12, 12)
        progress_header = QHBoxLayout()
        progress_title = QLabel("중복 탐지")
        progress_title.setObjectName("progressTitle")
        progress_header.addWidget(progress_title)
        progress_header.addStretch()
        self._progress_percent = QLabel("0%")
        self._progress_percent.setObjectName("progressPercent")
        progress_header.addWidget(self._progress_percent)
        layout.addLayout(progress_header)
        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_bar.setTextVisible(False)
        self._progress_bar.setMaximumWidth(520)
        layout.addWidget(self._progress_bar)
        self._progress_info = QLabel("대기 중...")
        self._progress_info.setObjectName("progressInfo")
        layout.addWidget(self._progress_info)
        return group

    def _on_start_detection(self) -> None:
        self._view_model.start_duplicate_detection()

    def _on_progress_updated(self, progress: int, message: str) -> None:
        self._progress_bar.setRange(0, 0)
        self._progress_info.setText(message)
        self._progress_percent.setText("")

    def _on_results_updated(self) -> None:
        self._groups_view.set_results(self._view_model.results)

    def _on_group_selected(self, group_id: int) -> None:
        result = self._view_model.get_group_by_id(group_id)
        if result:
            self._evidence_panel.set_group(result)

    @staticmethod
    def _similarity_score_for_result(result: DuplicateGroupResult) -> Optional[float]:
        if result.duplicate_type != "near":
            return None
        evidence: dict[str, Any] = result.evidence or {}
        raw = evidence.get("similarity")
        return result.confidence if raw is None else raw

    def _build_duplicate_batch_updates(
        self, results: list[DuplicateGroupResult]
    ) -> list[tuple[int, Optional[int], bool, Optional[float]]]:
        batch_updates_dict: dict[int, tuple[int, Optional[int], bool, Optional[float]]] = {}
        for result in results:
            similarity_score = self._similarity_score_for_result(result)
            keeper = result.recommended_keeper_id
            for file_id in result.file_ids:
                is_canonical = keeper is not None and file_id == keeper
                batch_updates_dict[file_id] = (
                    file_id,
                    result.group_id,
                    is_canonical,
                    similarity_score,
                )
        return list(batch_updates_dict.values())

    def _on_duplicate_completed(self, results: list) -> None:
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(100)
        self._progress_percent.setText("100%")
        self._progress_info.setText(f"완료: {len(results)}개 그룹")
        self._groups_view.set_results(results)
        if results and self._on_groups_found:
            self._on_groups_found()
        batch_updates = self._build_duplicate_batch_updates(results)
        if batch_updates:
            self._app_state.file_data_store.set_duplicate_groups_batch(batch_updates)
        self._save_duplicate_result_to_json(results)

    def _save_duplicate_result_to_json(self, results: list) -> None:
        try:
            project_root = Path(__file__).resolve().parents[5]
            output_path = project_root / "SAVE" / generate_duplicate_json_filename()
            store = self._app_state.file_data_store
            save_duplicate_result_to_json(results, output_path.resolve(), store, store.scan_folder)
        except Exception as e:
            logger.warning("중복 JSON 저장 실패: %s", e, exc_info=True)

    def _on_duplicate_error(self, error_message: str) -> None:
        self._progress_bar.setRange(0, 100)
        self._progress_info.setText(f"오류: {error_message}")

    def _on_dry_run(self) -> None:
        store = self._app_state.file_data_store
        scan_folder = store.scan_folder
        if not scan_folder:
            QMessageBox.warning(
                self, "오류", "스캔 폴더가 설정되지 않았습니다. 먼저 스캔을 실행하세요."
            )
            return
        use_case = MoveDuplicateFilesUseCase(store, self._log_sink)
        operations = use_case.execute(scan_folder)
        if not operations:
            QMessageBox.information(self, "Dry Run", "이동할 파일이 없습니다.")
            return
        DryRunPreviewDialog(operations, scan_folder, self).exec()

    def _on_apply(self) -> None:
        store = self._app_state.file_data_store
        scan_folder = store.scan_folder
        if not scan_folder:
            QMessageBox.warning(self, "오류", "스캔 폴더가 설정되지 않았습니다.")
            return
        use_case = MoveDuplicateFilesUseCase(store, self._log_sink)
        operations = use_case.execute(scan_folder)
        if not operations:
            QMessageBox.information(self, "적용하기", "이동할 파일이 없습니다.")
            return
        reply = QMessageBox.question(
            self,
            "적용하기",
            f"총 {len(operations)}개 파일을 duplicate/ 폴더로 이동합니다.\n계속하시겠습니까?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        self._move_worker = FileMoveWorker(use_case, scan_folder, self._log_sink, self)
        self._move_worker.move_completed.connect(self._on_move_completed)
        self._move_worker.move_error.connect(self._on_move_error)
        self._move_worker.start()
        self._progress_bar.setRange(0, 0)
        self._progress_info.setText("파일 이동 중...")

    def _on_move_completed(
        self, moved_count: int, error_count: int, error_list: list, moved_file_ids: list[int]
    ) -> None:
        if moved_file_ids:
            self._app_state.file_data_store.remove_files(moved_file_ids)
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(100)
        self._progress_info.setText(f"완료: {moved_count}개 이동")
        if self._move_worker:
            self._move_worker.deleteLater()
            self._move_worker = None
        if self._pipeline_apply_pending:
            self._pipeline_apply_pending = False
            self.pipeline_apply_finished.emit(error_count == 0)

    def _on_move_error(self, error_message: str) -> None:
        self._progress_info.setText(f"오류: {error_message}")
        if self._move_worker:
            self._move_worker.deleteLater()
            self._move_worker = None
        if self._pipeline_apply_pending:
            self._pipeline_apply_pending = False
            self.pipeline_apply_finished.emit(False)
