"""이동 정리 탭 (초성별 폴더 정리)."""

import logging
from pathlib import Path
from typing import Optional, cast

from PySide6.QtCore import QObject
from PySide6.QtWidgets import (
    QFileDialog,
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
from gui.models.app_state import AppState
from gui.views.tabs.base_tab import BaseTab

logger = logging.getLogger(__name__)


class MoveOrganizeTab(BaseTab):
    """이동 정리 탭. 대상 폴더 직하위 파일을 ㄱ-ㄷ·ㄹ-ㅂ·…·기타 구간 폴더로 초성별 정리."""

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        job_manager=None,
        index_repository=None,
        log_sink: Optional[ILogSink] = None,
    ) -> None:
        self._log_sink = log_sink
        self._app_state: Optional[AppState] = None
        self._use_case = OrganizeByChosungUseCase(log_sink=log_sink)
        super().__init__(parent)

    def _get_app_state(self) -> AppState:
        """AppState 가져오기."""
        parent: QObject | None = self.parent()
        while parent is not None:
            if hasattr(parent, "_app_state"):
                return cast(AppState, getattr(parent, "_app_state"))
            parent = parent.parent()
        return AppState()

    def get_title(self) -> str:
        """페이지 제목 반환."""
        return "📂 이동 정리"

    def _setup_content(self, layout: QVBoxLayout) -> None:
        if self._app_state is None:
            self._app_state = self._get_app_state()

        folder_group = self._create_folder_group()
        layout.addWidget(folder_group)

        options_group = self._create_options_group()
        layout.addWidget(options_group)

        action_bar = self._create_action_bar()
        layout.addLayout(action_bar)

        self._progress_section = self._create_progress_section()
        layout.addWidget(self._progress_section)

        self._result_label = QLabel("")
        self._result_label.setStyleSheet("font-size: 12px; color: #808080;")
        self._result_label.setWordWrap(True)
        layout.addWidget(self._result_label)

    def _create_folder_group(self) -> QGroupBox:
        group = QGroupBox("대상 폴더")
        group.setObjectName("settingsGroup")
        layout = QVBoxLayout(group)
        row = QHBoxLayout()
        self._folder_edit = QLineEdit()
        self._folder_edit.setPlaceholderText(
            "파일 스캔 탭에서 선택한 폴더와 연동됩니다. 여기서 바꾸면 스캔 탭에도 반영됩니다."
        )
        self._folder_edit.setReadOnly(True)
        row.addWidget(self._folder_edit)
        browse_btn = QPushButton("폴더 선택")
        browse_btn.setObjectName("btnSecondary")
        browse_btn.clicked.connect(self._on_browse_folder)
        row.addWidget(browse_btn)
        layout.addLayout(row)
        hint = QLabel(
            f"결과는 대상 폴더 아래 '{OUTPUT_SUBFOLDER}' 폴더에 저장되며, 파일명 끝 ' (1)' 은 제거됩니다."
        )
        hint.setStyleSheet("font-size: 11px; color: #606060;")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        return group

    def _create_options_group(self) -> QGroupBox:
        group = QGroupBox("동작")
        group.setObjectName("settingsGroup")
        layout = QHBoxLayout(group)
        self._move_radio = QRadioButton("이동")
        self._move_radio.setChecked(True)
        self._copy_radio = QRadioButton("복사")
        layout.addWidget(self._move_radio)
        layout.addWidget(self._copy_radio)
        layout.addStretch()
        return group

    def _create_action_bar(self) -> QHBoxLayout:
        bar = QHBoxLayout()
        bar.setSpacing(16)
        dry_run_btn = QPushButton("Dry Run")
        dry_run_btn.setObjectName("btnSecondary")
        dry_run_btn.clicked.connect(self._on_dry_run)
        bar.addWidget(dry_run_btn)
        run_btn = QPushButton("초성별로 정리 실행")
        run_btn.setObjectName("btnPrimary")
        run_btn.clicked.connect(self._on_run)
        bar.addWidget(run_btn)
        bar.addStretch()
        return bar

    def _create_progress_section(self) -> QGroupBox:
        group = QGroupBox()
        group.setTitle("")
        layout = QVBoxLayout(group)
        layout.setSpacing(12)
        progress_header = QHBoxLayout()
        progress_header.setContentsMargins(0, 0, 0, 0)
        self._progress_title = QLabel("대기 중...")
        self._progress_title.setObjectName("progressTitle")
        progress_header.addWidget(self._progress_title)
        progress_header.addStretch()
        self._progress_percent = QLabel("")
        self._progress_percent.setObjectName("progressPercent")
        progress_header.addWidget(self._progress_percent)
        layout.addLayout(progress_header)
        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_bar.setTextVisible(False)
        layout.addWidget(self._progress_bar)
        self._progress_info = QLabel("대기 중...")
        self._progress_info.setObjectName("progressInfo")
        self._progress_info.setStyleSheet("font-size: 12px; color: #808080;")
        layout.addWidget(self._progress_info)
        group.setVisible(True)
        return group

    def _on_browse_folder(self) -> None:
        """폴더 선택 시 파일 스캔 탭과 연동(동일 폴더로 설정)."""
        current = self._folder_edit.text().strip()
        start = current if current else ""
        folder = QFileDialog.getExistingDirectory(
            self,
            "대상 폴더 선택",
            start,
            QFileDialog.Option.ShowDirsOnly,
        )
        if folder:
            folder_path = Path(folder)
            self._folder_edit.setText(folder)
            # 앱 상태 및 파일 스캔 탭과 연동
            mw = self._get_main_window()
            if mw and hasattr(mw, "save_scan_folder"):
                mw.save_scan_folder(folder_path)
            scan_tab = self._get_scan_tab()
            if scan_tab and hasattr(scan_tab, "set_scan_folder"):
                scan_tab.set_scan_folder(folder_path)
            if scan_tab and hasattr(scan_tab, "folder_selected"):
                scan_tab.folder_selected.emit(folder_path)

    def _get_target_path(self) -> Optional[Path]:
        text = self._folder_edit.text().strip()
        if text:
            p = Path(text)
            return p if p.is_dir() else None
        return None

    def _refresh_folder_from_scan(self) -> None:
        """파일 스캔 탭과 연동: 앱 상태의 스캔 폴더를 대상 폴더 편집창에 항상 반영."""
        if self._app_state is None:
            self._app_state = self._get_app_state()
        folder = self._app_state.scan_folder or ""
        self._folder_edit.setText(folder)

    def _get_scan_tab(self):
        """MainWindow를 통해 ScanTab 위젯 반환."""
        mw = self._get_main_window()
        if mw and hasattr(mw, "_get_scan_tab"):
            return mw._get_scan_tab()
        return None

    def showEvent(self, event) -> None:
        """탭이 보일 때 파일 스캔 탭 대상 폴더와 동기화."""
        super().showEvent(event)
        self._refresh_folder_from_scan()

    def _on_dry_run(self) -> None:
        self._refresh_folder_from_scan()
        root = self._get_target_path()
        if not root:
            QMessageBox.warning(
                self,
                "대상 폴더 필요",
                "대상 폴더를 선택해 주세요.",
            )
            return
        debug_step(self._log_sink, "move_organize_tab_dry_run")
        self._progress_bar.setRange(0, 0)
        self._progress_title.setText("Dry Run 중...")
        self._progress_info.setText("계획만 계산 중...")
        self._result_label.setText("")
        try:
            result = self._use_case.execute(root_path=root, move=True, dry_run=True)
            self._progress_bar.setRange(0, 100)
            self._progress_bar.setValue(100)
            self._progress_title.setText("Dry Run 완료")
            if result.total_processed == 0:
                self._progress_info.setText("정리할 파일이 없습니다.")
                if result.files_already_in_chosung > 0:
                    self._result_label.setText(
                        f"이미 초성 구간(ㄱ-ㄷ 등) 폴더 안에 있는 파일이 {result.files_already_in_chosung}개 있어서 제외되었습니다. "
                        "한 번 실행한 뒤에는 같은 폴더를 다시 정리할 대상이 없습니다."
                    )
                else:
                    self._result_label.setText(
                        "대상 폴더에 파일이 없거나, 읽을 수 있는 파일이 없습니다."
                    )
            else:
                self._progress_info.setText(
                    f"총 {result.total_processed}개 파일이 초성별로 분류됩니다."
                )
                parts = [
                    f"{name}: {result.counts_by_folder.get(name, 0)}개" for name in FOLDER_NAMES
                ]
                self._result_label.setText(" · ".join(parts))
        except Exception as e:
            logger.exception("Dry run failed")
            self._progress_bar.setRange(0, 100)
            self._progress_title.setText("오류")
            self._progress_info.setText(str(e))
            QMessageBox.critical(self, "Dry Run 오류", str(e))

    def _on_run(self) -> None:
        self._refresh_folder_from_scan()
        root = self._get_target_path()
        if not root:
            QMessageBox.warning(
                self,
                "대상 폴더 필요",
                "대상 폴더를 선택해 주세요.",
            )
            return
        move = self._move_radio.isChecked()
        debug_step(self._log_sink, "move_organize_tab_run", {"path": str(root), "move": move})
        self._progress_bar.setRange(0, 0)
        self._progress_title.setText("정리 중...")
        self._progress_info.setText("이동 중..." if move else "복사 중...")
        self._result_label.setText("")
        try:
            result = self._use_case.execute(root_path=root, move=move, dry_run=False)
            self._progress_bar.setRange(0, 100)
            self._progress_bar.setValue(100)
            self._progress_title.setText("완료")
            if result.moved_or_copied == 0 and result.total_processed == 0:
                self._progress_info.setText("정리할 파일이 없습니다.")
                if result.files_already_in_chosung > 0:
                    self._result_label.setText(
                        f"이미 초성 구간(ㄱ-ㄷ 등) 폴더 안에 있는 파일이 {result.files_already_in_chosung}개 있어서 제외되었습니다."
                    )
                else:
                    self._result_label.setText("대상 폴더에 파일이 없습니다.")
            else:
                self._progress_info.setText(
                    f"{result.moved_or_copied}개 파일 {'이동' if move else '복사'} 완료"
                    + (f" (건너뜀: {result.skipped}개)" if result.skipped else "")
                )
                parts = [
                    f"{name}: {result.counts_by_folder.get(name, 0)}개" for name in FOLDER_NAMES
                ]
                self._result_label.setText(" · ".join(parts))
        except Exception as e:
            logger.exception("Organize by chosung failed")
            self._progress_bar.setRange(0, 100)
            self._progress_title.setText("오류")
            self._progress_info.setText(str(e))
            QMessageBox.critical(self, "실행 오류", str(e))
