"""Move/organize by chosung section (collapsed by default)."""

import logging
from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

from application.ports.log_sink import ILogSink
from application.use_cases.organize_by_chosung import (
    FOLDER_NAMES,
    OUTPUT_SUBFOLDER,
    OrganizeByChosungUseCase,
)
from application.utils.debug_logger import debug_step
from gui.views.work.app_context import get_app_state

logger = logging.getLogger(__name__)


class MoveSection(QWidget):
    """Chosung folder organize — uses library scan folder (read-only)."""

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        log_sink: Optional[ILogSink] = None,
    ) -> None:
        super().__init__(parent)
        self._log_sink = log_sink
        self._app_state = get_app_state(self)
        self._use_case = OrganizeByChosungUseCase(log_sink=log_sink)
        self._build_ui()
        self.refresh_folder()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        folder_group = QGroupBox("대상 폴더 (라이브러리와 동일)")
        folder_group.setObjectName("settingsGroup")
        fg = QVBoxLayout(folder_group)
        self._folder_edit = QLineEdit()
        self._folder_edit.setReadOnly(True)
        fg.addWidget(self._folder_edit)
        hint = QLabel(
            f"결과는 '{OUTPUT_SUBFOLDER}' 하위에 저장됩니다. 폴더는 라이브러리 섹션에서 선택하세요."
        )
        hint.setObjectName("formHint")
        hint.setWordWrap(True)
        fg.addWidget(hint)
        layout.addWidget(folder_group)

        options = QGroupBox("동작")
        options.setObjectName("settingsGroup")
        opt_layout = QHBoxLayout(options)
        self._move_radio = QRadioButton("이동")
        self._move_radio.setChecked(True)
        self._copy_radio = QRadioButton("복사")
        opt_layout.addWidget(self._move_radio)
        opt_layout.addWidget(self._copy_radio)
        opt_layout.addStretch()
        layout.addWidget(options)

        bar = QHBoxLayout()
        dry_run_btn = QPushButton("Dry Run")
        dry_run_btn.setObjectName("btnSecondary")
        dry_run_btn.clicked.connect(self._on_dry_run)
        bar.addWidget(dry_run_btn)
        run_btn = QPushButton("초성별로 정리 실행")
        run_btn.setObjectName("btnPrimary")
        run_btn.clicked.connect(self._on_run)
        bar.addWidget(run_btn)
        bar.addStretch()
        layout.addLayout(bar)

        self._progress_bar = QProgressBar()
        layout.addWidget(self._progress_bar)
        self._progress_info = QLabel("대기 중...")
        self._progress_info.setObjectName("progressInfo")
        layout.addWidget(self._progress_info)
        self._result_label = QLabel("")
        self._result_label.setObjectName("progressInfo")
        self._result_label.setWordWrap(True)
        layout.addWidget(self._result_label)

    def refresh_folder(self) -> None:
        folder = self._app_state.scan_folder or ""
        self._folder_edit.setText(folder)

    def _get_target_path(self) -> Optional[Path]:
        text = self._folder_edit.text().strip()
        if text:
            p = Path(text)
            return p if p.is_dir() else None
        return None

    def _on_dry_run(self) -> None:
        self.refresh_folder()
        root = self._get_target_path()
        if not root:
            QMessageBox.warning(
                self, "대상 폴더 필요", "라이브러리에서 스캔 폴더를 먼저 선택하세요."
            )
            return
        debug_step(self._log_sink, "move_section_dry_run")
        self._progress_bar.setRange(0, 0)
        self._progress_info.setText("Dry Run 계산 중...")
        try:
            result = self._use_case.execute(root_path=root, move=True, dry_run=True)
            self._progress_bar.setRange(0, 100)
            self._progress_bar.setValue(100)
            self._progress_info.setText(f"예상 처리: {result.total_processed}개")
            parts = [f"{n}: {result.counts_by_folder.get(n, 0)}" for n in FOLDER_NAMES]
            self._result_label.setText(" · ".join(parts))
        except Exception as e:
            logger.exception("Dry run failed")
            QMessageBox.critical(self, "Dry Run 오류", str(e))

    def _on_run(self) -> None:
        self.refresh_folder()
        root = self._get_target_path()
        if not root:
            QMessageBox.warning(
                self, "대상 폴더 필요", "라이브러리에서 스캔 폴더를 먼저 선택하세요."
            )
            return
        move = self._move_radio.isChecked()
        self._progress_bar.setRange(0, 0)
        self._progress_info.setText("실행 중...")
        try:
            result = self._use_case.execute(root_path=root, move=move, dry_run=False)
            self._progress_bar.setRange(0, 100)
            self._progress_bar.setValue(100)
            self._progress_info.setText(
                f"{result.moved_or_copied}개 {'이동' if move else '복사'} 완료"
            )
            parts = [f"{n}: {result.counts_by_folder.get(n, 0)}" for n in FOLDER_NAMES]
            self._result_label.setText(" · ".join(parts))
        except Exception as e:
            logger.exception("Organize failed")
            QMessageBox.critical(self, "실행 오류", str(e))
