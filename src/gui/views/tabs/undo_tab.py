"""Undo/Rollback 탭."""

from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
)

from gui.views.tabs.base_tab import BaseTab

_NOT_IMPLEMENTED_MSG = (
    "이 화면은 아직 구현되지 않았습니다. "
    "작업 되돌리기·실행 기록 복원은 향후 버전에서 제공될 예정입니다. "
    "아래 컨트롤은 UI 뼈대용이며 동작하지 않습니다."
)


class UndoTab(BaseTab):
    """Undo/Rollback 탭."""

    def get_title(self) -> str:
        """페이지 제목 반환."""
        return "↩️ Undo / Rollback"

    def _create_not_implemented_notice(self) -> QGroupBox:
        """미구현 안내 (Phase 4: 플레이스홀더 명시)."""
        group = QGroupBox("안내")
        group.setObjectName("settingsGroup")
        gl = QVBoxLayout(group)
        msg = QLabel(_NOT_IMPLEMENTED_MSG)
        msg.setWordWrap(True)
        msg.setObjectName("progressInfo")
        msg.setStyleSheet("font-size: 13px; color: #a0a0a0; padding: 4px 0;")
        gl.addWidget(msg)
        return group

    def _setup_content(self, layout: QVBoxLayout) -> None:
        """컨텐츠 설정."""
        layout.addWidget(self._create_not_implemented_notice())
        # 액션 바
        action_bar = self._create_action_bar()
        layout.addLayout(action_bar)

        # 프로그레스 섹션
        self._progress_section = self._create_progress_section()
        layout.addWidget(self._progress_section)

        # 실행 기록 그룹
        history_group = self._create_history_group()
        layout.addWidget(history_group)

    def _create_action_bar(self) -> QHBoxLayout:
        """액션 바 생성."""
        layout = QHBoxLayout()
        layout.setSpacing(16)

        undo_btn = QPushButton("선택 작업 되돌리기")
        undo_btn.setObjectName("btnPrimary")
        undo_btn.setEnabled(False)
        undo_btn.setToolTip("미구현")
        layout.addWidget(undo_btn)

        reset_btn = QPushButton("모든 작업 초기화")
        reset_btn.setObjectName("btnDanger")
        reset_btn.setEnabled(False)
        reset_btn.setToolTip("미구현")
        layout.addWidget(reset_btn)

        layout.addStretch()

        return layout

    def _create_progress_section(self) -> QGroupBox:
        """프로그레스 섹션 생성."""
        group = QGroupBox()
        group.setTitle("")

        layout = QVBoxLayout(group)
        layout.setSpacing(12)

        # 프로그레스 헤더
        progress_header = QHBoxLayout()
        progress_header.setContentsMargins(0, 0, 0, 0)

        progress_title = QLabel("작업 되돌리기 진행 중...")
        progress_title.setObjectName("progressTitle")
        progress_header.addWidget(progress_title)

        progress_header.addStretch()

        self._progress_percent = QLabel("0%")
        self._progress_percent.setObjectName("progressPercent")
        progress_header.addWidget(self._progress_percent)

        layout.addLayout(progress_header)

        # 프로그레스 바
        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_bar.setTextVisible(False)
        layout.addWidget(self._progress_bar)

        # 프로그레스 정보
        self._progress_info = QLabel("대기 중...")
        self._progress_info.setObjectName("progressInfo")
        self._progress_info.setStyleSheet("font-size: 12px; color: #808080;")
        layout.addWidget(self._progress_info)

        # 항상 보이도록 설정
        group.setVisible(True)

        return group

    def _create_history_group(self) -> QGroupBox:
        """실행 기록 그룹 생성."""
        group = QGroupBox("실행 기록")
        group.setObjectName("settingsGroup")

        layout = QVBoxLayout(group)

        placeholder = QLabel("구현 후 실행 기록이 여기에 표시됩니다.")
        placeholder.setStyleSheet("color: #808080; font-size: 14px; padding: 20px;")
        layout.addWidget(placeholder)

        return group
