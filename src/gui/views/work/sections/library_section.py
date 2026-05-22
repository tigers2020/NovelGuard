"""Library section: folder pick, preview trigger, full scan."""

import logging
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from application.dto.scan_result import ScanResult
from application.ports.log_sink import ILogSink
from application.utils.scan_json import generate_scan_json_filename, save_scan_result_to_json
from gui.view_models.scan_view_model import ScanViewModel
from gui.views.work.app_context import get_app_state, get_main_window, get_settings_tab

logger = logging.getLogger(__name__)


class LibrarySection(QWidget):
    """Folder selection and full scan (single owner of folder picker)."""

    folder_selected = Signal(Path)

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        job_manager=None,
        log_sink: Optional[ILogSink] = None,
    ) -> None:
        super().__init__(parent)
        self._log_sink = log_sink
        self._scan_folder: Optional[Path] = None
        self._app_state = get_app_state(self)
        self._view_model = ScanViewModel(self, job_manager=job_manager, log_sink=log_sink)
        self._view_model.progress_updated.connect(self._on_progress_updated)
        self._view_model.scan_completed.connect(self._on_scan_completed)
        self._view_model.scan_error.connect(self._on_scan_error)
        self._view_model.error_occurred.connect(self._on_error_occurred)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        preview_row = QHBoxLayout()
        self._preview_status = QLabel("빠른 미리보기: 대기")
        self._preview_status.setObjectName("progressInfo")
        preview_row.addWidget(self._preview_status)
        preview_row.addStretch()
        layout.addLayout(preview_row)

        action_bar = QHBoxLayout()
        action_bar.setSpacing(16)
        folder_btn = QPushButton("폴더 선택")
        folder_btn.setObjectName("btnPrimary")
        folder_btn.clicked.connect(self._on_select_folder)
        action_bar.addWidget(folder_btn)
        scan_btn = QPushButton("전체 스캔")
        scan_btn.setObjectName("btnPrimary")
        scan_btn.clicked.connect(self._on_start_scan)
        action_bar.addWidget(scan_btn)
        stop_btn = QPushButton("중지")
        stop_btn.setObjectName("btnSecondary")
        stop_btn.clicked.connect(self._on_stop_scan)
        action_bar.addWidget(stop_btn)
        action_bar.addStretch()
        layout.addLayout(action_bar)

        self._progress_section = self._create_progress_section()
        layout.addWidget(self._progress_section)

        folder_block = QWidget()
        folder_block.setObjectName("pipelineFieldBlock")
        fg_layout = QVBoxLayout(folder_block)
        fg_layout.setContentsMargins(0, 0, 0, 0)
        folder_label = QLabel("대상 폴더")
        folder_label.setObjectName("formLabel")
        fg_layout.addWidget(folder_label)
        self._folder_input = QLineEdit()
        self._folder_input.setReadOnly(True)
        self._folder_input.setPlaceholderText("폴더를 선택하세요")
        fg_layout.addWidget(self._folder_input)
        hint = QLabel("확장자·하위 폴더 옵션은 설정 탭에서 변경할 수 있습니다.")
        hint.setObjectName("formHint")
        hint.setWordWrap(True)
        fg_layout.addWidget(hint)
        layout.addWidget(folder_block)

    def _create_progress_section(self) -> QWidget:
        group = QWidget()
        group.setObjectName("pipelineProgressBlock")
        layout = QVBoxLayout(group)
        layout.setContentsMargins(12, 12, 12, 12)
        progress_header = QHBoxLayout()
        progress_title = QLabel("전체 스캔")
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

    def set_preview_status(self, text: str) -> None:
        self._preview_status.setText(f"빠른 미리보기: {text}")

    @property
    def scan_view_model(self) -> ScanViewModel:
        return self._view_model

    def request_full_scan(self) -> None:
        self._on_start_scan()

    def cancel_scan(self) -> None:
        self._on_stop_scan()

    def set_scan_folder(self, folder: Path) -> None:
        self._scan_folder = folder
        self._folder_input.setText(str(folder))

    def get_scan_folder(self) -> Optional[Path]:
        return self._scan_folder

    def _on_select_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self, "스캔할 폴더 선택", str(self._scan_folder) if self._scan_folder else ""
        )
        if folder:
            folder_path = Path(folder)
            self.set_scan_folder(folder_path)
            self.folder_selected.emit(folder_path)

    def _get_settings(self):
        return get_settings_tab(self)

    def _on_start_scan(self) -> None:
        if not self._scan_folder:
            QMessageBox.warning(self, "스캔 폴더 미선택", "스캔할 폴더를 선택해주세요.")
            return
        settings = self._get_settings()
        extensions = settings.get_extension_filter() if settings else ""
        self._view_model.start_scan(
            folder=self._scan_folder,
            extensions=extensions,
            include_subdirs=settings.get_include_subdirs() if settings else True,
            include_hidden=settings.get_include_hidden() if settings else False,
            include_symlinks=settings.get_include_symlinks() if settings else True,
            incremental_scan=settings.get_incremental_scan() if settings else True,
        )

    def _on_stop_scan(self) -> None:
        self._view_model.stop_scan()

    def _on_progress_updated(self, progress: int, message: str) -> None:
        self._progress_bar.setRange(0, 0)
        count = self._view_model.progress_count
        if count > 0:
            self._progress_info.setText(f"{message} ({count}개 파일)")
        else:
            self._progress_info.setText(message)
        self._progress_percent.setText("")

    def _on_scan_completed(self, result: ScanResult) -> None:
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(100)
        self._progress_percent.setText("100%")
        self._progress_info.setText(
            f"완료: {result.total_files}개 파일, {result.total_bytes:,} bytes"
        )
        if result.entries:
            data_store = self._app_state.file_data_store
            if self._scan_folder:
                data_store.scan_folder = self._scan_folder
            data_store.add_files(result.entries)
        self._save_scan_result_to_json(result)

    def _on_scan_error(self, error_message: str) -> None:
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_info.setText(f"오류: {error_message}")
        main_window = get_main_window(self)
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setWindowTitle("스캔 오류")
        msg.setText("파일 스캔 중 오류가 발생했습니다.")
        msg.setDetailedText(error_message)
        if main_window:
            msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            msg.button(QMessageBox.StandardButton.Yes).setText("로그 탭 열기")
            if msg.exec() == QMessageBox.StandardButton.Yes:
                main_window._switch_tab("logs")  # type: ignore[attr-defined]
        else:
            msg.exec()

    def _on_error_occurred(self, error_message: str) -> None:
        self._progress_info.setText(f"오류: {error_message}")

    def _save_scan_result_to_json(self, result: ScanResult) -> None:
        try:
            project_root = Path(__file__).resolve().parents[5]
            output_path = (
                project_root / "SAVE" / generate_scan_json_filename(result.scan_timestamp)
            ).resolve()
            save_scan_result_to_json(result, output_path, self._scan_folder)
        except Exception as e:
            logger.warning("스캔 결과 JSON 저장 실패: %s", e, exc_info=True)
