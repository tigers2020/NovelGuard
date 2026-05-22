"""Numbered pipeline step card for the Work screen (flat panel, not QGroupBox)."""

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from gui.view_models.work_pipeline_dto import StepState

_STATE_LABELS: dict[StepState, str] = {
    "locked": "대기",
    "ready": "준비",
    "running": "진행중",
    "done": "완료",
    "skipped": "건너뜀",
    "blocked": "차단",
}


class StepCard(QWidget):
    """Single pipeline step: flat card with badge, title, state pill, body slot."""

    def __init__(
        self,
        step_id: str,
        badge: str,
        title: str,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.step_id = step_id
        self.setObjectName("stepCard")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 16, 20, 16)
        outer.setSpacing(12)

        header = QWidget()
        header.setObjectName("stepCardHeader")
        title_layout = QHBoxLayout(header)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(12)

        self._badge = QLabel(badge)
        self._badge.setObjectName("stepBadge")
        self._badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_layout.addWidget(self._badge)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        self._title = QLabel(title)
        self._title.setObjectName("stepTitle")
        title_col.addWidget(self._title)
        title_layout.addLayout(title_col, stretch=1)

        self._state_pill = QLabel(_STATE_LABELS["locked"])
        self._state_pill.setObjectName("stepStatePill")
        title_layout.addWidget(self._state_pill)

        outer.addWidget(header)

        divider = QFrame()
        divider.setObjectName("stepCardDivider")
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setFrameShadow(QFrame.Shadow.Plain)
        outer.addWidget(divider)

        self.body = QWidget()
        self.body.setObjectName("stepCardBody")
        self.body_layout = QVBoxLayout(self.body)
        self.body_layout.setContentsMargins(0, 0, 0, 0)
        self.body_layout.setSpacing(12)
        outer.addWidget(self.body)

        self._state: StepState = "locked"
        self.set_active(False)

    def set_state(self, state: StepState) -> None:
        self._state = state
        self._state_pill.setText(_STATE_LABELS.get(state, state))
        self.setProperty("stepState", state)

    def set_active(self, active: bool) -> None:
        self.setProperty("active", "true" if active else "false")

    def state(self) -> StepState:
        return self._state
