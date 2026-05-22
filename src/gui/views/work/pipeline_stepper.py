"""Horizontal installation-style pipeline step indicator."""

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from gui.view_models.work_pipeline_dto import STEP_LABELS, STEP_ORDER, StepId, StepState

_STATE_SUFFIX: dict[StepState, str] = {
    "locked": "대기",
    "ready": "준비",
    "running": "진행중",
    "done": "완료",
    "skipped": "건너뜀",
    "blocked": "차단",
}


class PipelineStepper(QWidget):
    """Wizard/installer progress rail — one active step; click to switch when ready."""

    step_clicked = Signal(str)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("pipelineStepper")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 16)
        layout.setSpacing(0)

        self._steps: dict[str, _StepNode] = {}
        step_ids = [s.value for s in STEP_ORDER]

        for index, step_id in enumerate(step_ids):
            if index > 0:
                connector = QLabel()
                connector.setObjectName("pipelineStepConnector")
                connector.setFixedHeight(2)
                connector.setMinimumWidth(24)
                layout.addWidget(connector, stretch=1)

            node = _StepNode(step_id, str(index + 1), STEP_LABELS[StepId(step_id)])
            node.clicked.connect(self._on_node_clicked)
            self._steps[step_id] = node
            layout.addWidget(node)

        self.set_active_step(step_ids[0])

    def _on_node_clicked(self, step_id: str) -> None:
        node = self._steps.get(step_id)
        if node and node.isEnabled():
            self.step_clicked.emit(step_id)

    def set_active_step(self, step_id: str) -> None:
        for sid, node in self._steps.items():
            node.setProperty("active", "true" if sid == step_id else "false")
            node.set_active_visual(sid == step_id)

    def set_step_state(self, step_id: str, state: StepState) -> None:
        node = self._steps.get(step_id)
        if node:
            node.set_state(state)
            node._apply_enabled(state not in ("locked",))

    def step_index(self, step_id: str) -> int:
        ids = [s.value for s in STEP_ORDER]
        return ids.index(step_id) if step_id in ids else 0

    def is_step_enabled(self, step_id: str) -> bool:
        node = self._steps.get(step_id)
        return node.isEnabled() if node else False


class _StepNode(QWidget):
    """Single step: circle button + title + status caption."""

    clicked = Signal(str)

    def __init__(
        self, step_id: str, badge: str, title: str, parent: Optional[QWidget] = None
    ) -> None:
        super().__init__(parent)
        self._step_id = step_id
        self.setObjectName("pipelineStepNode")

        col = QHBoxLayout(self)
        col.setContentsMargins(4, 0, 4, 0)
        col.setSpacing(10)

        self._circle = QPushButton(badge)
        self._circle.setObjectName("pipelineStepCircle")
        self._circle.setFixedSize(36, 36)
        self._circle.setCursor(Qt.CursorShape.PointingHandCursor)
        self._circle.clicked.connect(lambda: self.clicked.emit(self._step_id))
        col.addWidget(self._circle)

        text_col = QWidget()
        text_layout = QVBoxLayout(text_col)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(2)

        self._title = QLabel(title)
        self._title.setObjectName("pipelineStepTitle")
        text_layout.addWidget(self._title)

        self._status = QLabel(_STATE_SUFFIX["locked"])
        self._status.setObjectName("pipelineStepStatus")
        text_layout.addWidget(self._status)

        col.addWidget(text_col)

        self.set_state("locked")
        self._apply_enabled(False)

    def _apply_enabled(self, enabled: bool) -> None:
        self.setEnabled(enabled)
        self._circle.setEnabled(enabled)

    def set_state(self, state: StepState) -> None:
        self.setProperty("stepState", state)
        self._status.setText(_STATE_SUFFIX.get(state, state))
        if state == "done":
            self._circle.setText("✓")
        elif state == "skipped":
            self._circle.setText("—")
        else:
            ids = [s.value for s in STEP_ORDER]
            self._circle.setText(str(ids.index(self._step_id) + 1))

    def set_active_visual(self, active: bool) -> None:
        self._circle.setProperty("active", "true" if active else "false")
