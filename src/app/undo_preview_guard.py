"""Pending undo dry-run plan between previewUndoPlan and executeUndoPlan."""

from __future__ import annotations

from dataclasses import dataclass

from domain.recovery_models import UndoDryRunPlan


@dataclass(frozen=True, slots=True)
class PendingUndoPreview:
    token: str
    undo_plan_id: str
    library_id: str
    plan: UndoDryRunPlan


class UndoPreviewGuard:
    def __init__(self) -> None:
        self._pending: PendingUndoPreview | None = None

    def store(
        self,
        *,
        token: str,
        undo_plan_id: str,
        library_id: str,
        plan: UndoDryRunPlan,
    ) -> None:
        self._pending = PendingUndoPreview(
            token=token,
            undo_plan_id=undo_plan_id,
            library_id=library_id,
            plan=plan,
        )

    def get(self) -> PendingUndoPreview | None:
        return self._pending

    def clear(self) -> None:
        self._pending = None
