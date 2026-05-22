"""One-button sequential work pipeline orchestrator (GUI layer)."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Optional
from uuid import uuid4

from PySide6.QtCore import QObject, Signal

from application.dto.scan_result import ScanResult
from gui.view_models.work_pipeline_dto import (
    STEP_LABELS,
    STEP_ORDER,
    PipelineRunProgress,
    StepId,
    compute_overall_percent,
)

if TYPE_CHECKING:
    from gui.views.main_window import MainWindow
    from gui.views.work.sections.duplicate_section import DuplicateSection
    from gui.views.work.sections.finalize_section import FinalizeSection
    from gui.views.work.sections.library_section import LibrarySection
    from gui.views.work.sections.move_section import MoveSection

logger = logging.getLogger(__name__)


class WorkPipelineRunner(QObject):
    """Runs scan → duplicate → move → finalize with UI step sync and global progress."""

    progress_changed = Signal(object)
    finished = Signal(str)
    step_changed = Signal(str)
    flags_changed = Signal()

    def __init__(
        self,
        *,
        main_window: MainWindow,
        library: LibrarySection,
        duplicate: DuplicateSection,
        move: MoveSection,
        finalize: FinalizeSection,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self._main_window = main_window
        self._library = library
        self._duplicate = duplicate
        self._move = move
        self._finalize = finalize
        self._cancelled = False
        self._auto_run = False
        self._run_id = ""
        self._flags: dict[str, bool] = {
            "scan_done": False,
            "duplicate_done": False,
            "duplicate_skipped": False,
            "move_done": False,
            "move_skipped": False,
        }

    @property
    def flags(self) -> dict[str, bool]:
        return dict(self._flags)

    def start(self, folder: Path, *, auto_run: bool = False) -> None:
        if self._library.scan_view_model.is_scanning:
            logger.warning("pipeline start ignored: scan already running")
            return
        self._cancelled = False
        self._auto_run = auto_run
        self._run_id = str(uuid4())[:8]
        self._reset_flags()
        self._main_window._switch_tab("work")
        self._library.set_scan_folder(folder)
        self._begin_scan()

    def cancel(self) -> None:
        self._cancelled = True
        if self._library.scan_view_model.is_scanning:
            self._library.cancel_scan()
        self._emit_progress(
            StepId.SCAN,
            0,
            "중지됨",
            0.0,
            phase="cancelled",
        )
        self.finished.emit("cancelled")

    def _reset_flags(self) -> None:
        for key in self._flags:
            self._flags[key] = False
        self.flags_changed.emit()

    def _begin_scan(self) -> None:
        self.step_changed.emit(StepId.SCAN.value)
        self._emit_progress(StepId.SCAN, 0, "전체 스캔 시작…", 0.05)
        vm = self._library.scan_view_model
        self._connect_once(vm.scan_completed, self._on_scan_completed)
        self._connect_once(vm.scan_error, self._on_scan_failed)
        self._library.request_full_scan()

    def _on_scan_completed(self, result: ScanResult) -> None:
        if self._cancelled:
            self.finished.emit("cancelled")
            return
        self._flags["scan_done"] = True
        self.flags_changed.emit()
        self._emit_progress(
            StepId.SCAN,
            0,
            f"{result.total_files:,}개 파일",
            1.0,
        )
        self._begin_duplicate()

    def _on_scan_failed(self, _message: str) -> None:
        self._emit_progress(StepId.SCAN, 0, "스캔 실패", 0.0, phase="failed")
        self.finished.emit("failed")

    def _begin_duplicate(self) -> None:
        self.step_changed.emit(StepId.DUPLICATE.value)
        self._emit_progress(StepId.DUPLICATE, 1, "중복 탐지 시작…", 0.05)
        vm = self._duplicate.duplicate_view_model
        self._connect_once(vm.duplicate_completed, self._on_duplicate_completed)
        self._connect_once(vm.duplicate_error, self._on_duplicate_failed)
        self._duplicate.request_detection()

    def _on_duplicate_completed(self, results: list) -> None:
        if self._cancelled:
            self.finished.emit("cancelled")
            return
        if not results:
            self._flags["duplicate_skipped"] = True
            self.flags_changed.emit()
            self._emit_progress(StepId.DUPLICATE, 1, "중복 그룹 없음 — 건너뜀", 1.0)
            self._begin_move()
            return
        self._flags["duplicate_done"] = True
        self.flags_changed.emit()
        self._emit_progress(StepId.DUPLICATE, 1, f"{len(results)}개 그룹", 0.5)
        if self._auto_run:
            self._emit_progress(StepId.DUPLICATE, 1, f"{len(results)}개 그룹 자동 적용…", 0.6)
            self._connect_once(
                self._duplicate.pipeline_apply_finished, self._on_duplicate_apply_done
            )
            if not self._duplicate.pipeline_apply_auto():
                self._emit_progress(StepId.DUPLICATE, 1, "적용 없음 — 건너뜀", 1.0)
                self._begin_move()
            return
        parent = self._main_window
        if not self._duplicate.pipeline_dry_run_preview(parent):
            self._emit_progress(StepId.DUPLICATE, 1, "사용자 취소", 0.0, phase="cancelled")
            self.finished.emit("cancelled")
            return
        self._emit_progress(StepId.DUPLICATE, 1, "승인 대기", 0.6, phase="awaiting_approval")
        self._connect_once(self._duplicate.pipeline_apply_finished, self._on_duplicate_apply_done)
        if not self._duplicate.pipeline_start_apply(parent):
            self._emit_progress(StepId.DUPLICATE, 1, "적용 없음 — 건너뜀", 1.0)
            self._begin_move()

    def _on_duplicate_apply_done(self, success: bool) -> None:
        if self._cancelled:
            self.finished.emit("cancelled")
            return
        if not success:
            self._emit_progress(StepId.DUPLICATE, 1, "적용 실패", 0.0, phase="failed")
            self.finished.emit("failed")
            return
        self._emit_progress(StepId.DUPLICATE, 1, "중복 적용 완료", 1.0)
        self._begin_move()

    def _on_duplicate_failed(self, _message: str) -> None:
        self._emit_progress(StepId.DUPLICATE, 1, "중복 탐지 실패", 0.0, phase="failed")
        self.finished.emit("failed")

    def _begin_move(self) -> None:
        self.step_changed.emit(StepId.MOVE.value)
        self._emit_progress(StepId.MOVE, 2, "이동 Dry Run…", 0.1)
        if not self._move.pipeline_dry_run_sync():
            self._emit_progress(StepId.MOVE, 2, "Dry Run 실패", 0.0, phase="failed")
            self.finished.emit("failed")
            return
        if self._auto_run:
            if not self._move.pipeline_execute_auto():
                self._emit_progress(StepId.MOVE, 2, "이동 실패", 0.0, phase="failed")
                self.finished.emit("failed")
                return
        else:
            self._emit_progress(StepId.MOVE, 2, "이동 승인 대기", 0.5, phase="awaiting_approval")
            if not self._move.pipeline_execute_with_confirmation(self._main_window):
                self._emit_progress(StepId.MOVE, 2, "이동 취소", 0.0, phase="cancelled")
                self.finished.emit("cancelled")
                return
        self._flags["move_done"] = True
        self.flags_changed.emit()
        self._emit_progress(StepId.MOVE, 2, "이동 완료", 1.0)
        self._begin_finalize()

    def _begin_finalize(self) -> None:
        self.step_changed.emit(StepId.FINALIZE.value)
        self._emit_progress(StepId.FINALIZE, 3, "적용 · 무결성…", 0.1)
        if not self._finalize.run_apply_and_integrity_auto(self._main_window):
            self._emit_progress(StepId.FINALIZE, 3, "검증 실패", 0.0, phase="failed")
            self.finished.emit("failed")
            return
        self._emit_progress(StepId.FINALIZE, 3, "완료", 1.0, phase="completed")
        self.finished.emit("completed")

    def _emit_progress(
        self,
        step_id: StepId,
        step_index: int,
        detail: str,
        intra_ratio: float,
        *,
        phase: str = "running",
    ) -> None:
        overall = compute_overall_percent(step_index, len(STEP_ORDER), intra_ratio)
        progress = PipelineRunProgress(
            run_id=self._run_id,
            current_step_id=step_id.value,
            step_index=step_index,
            step_label=STEP_LABELS[step_id],
            detail_message=detail,
            overall_percent=overall,
            phase=phase,  # type: ignore[arg-type]
        )
        self.progress_changed.emit(progress)

    @staticmethod
    def _connect_once(signal, slot: Callable) -> None:
        def wrapper(*args, **kwargs):
            try:
                signal.disconnect(wrapper)
            except (TypeError, RuntimeError):
                pass
            slot(*args, **kwargs)

        signal.connect(wrapper)
