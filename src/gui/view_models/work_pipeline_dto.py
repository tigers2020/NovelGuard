"""DTOs for the work-screen step pipeline and auto-run orchestrator."""

from dataclasses import dataclass
from enum import Enum
from typing import Literal

StepState = Literal["locked", "ready", "running", "done", "skipped", "blocked"]
PipelinePhase = Literal["running", "awaiting_approval", "completed", "failed", "cancelled"]
FinalizeSubstate = Literal[
    "idle",
    "applying",
    "apply_done",
    "integrity_running",
    "integrity_done",
    "apply_failed",
]


class StepId(str, Enum):
    """Ordered work pipeline step identifiers."""

    SCAN = "scan"
    DUPLICATE = "duplicate"
    MOVE = "move"
    FINALIZE = "finalize"


STEP_ORDER: tuple[StepId, ...] = (
    StepId.SCAN,
    StepId.DUPLICATE,
    StepId.MOVE,
    StepId.FINALIZE,
)

STEP_LABELS: dict[StepId, str] = {
    StepId.SCAN: "스캔",
    StepId.DUPLICATE: "중복 정리",
    StepId.MOVE: "이동 계획",
    StepId.FINALIZE: "적용 · 검증",
}


def compute_overall_percent(step_index: int, step_count: int, intra_step_ratio: float) -> int:
    """Map step index and intra-step ratio to 0..100 overall pipeline percent."""
    if step_count <= 0:
        return 0
    bucket = 100.0 / step_count
    raw = step_index * bucket + intra_step_ratio * bucket
    return min(100, int(raw))


@dataclass(frozen=True)
class PipelineSnapshot:
    """Per-step states and active step for the work pipeline UI."""

    steps: dict[str, StepState]
    active_step_id: str | None
    finalize_substate: FinalizeSubstate


@dataclass(frozen=True)
class PipelineRunProgress:
    """Step pipeline progress (legacy DTO; footer uses step-only UI in rev. 3.3)."""

    run_id: str
    current_step_id: str
    step_index: int
    step_label: str
    detail_message: str
    overall_percent: int
    phase: PipelinePhase
