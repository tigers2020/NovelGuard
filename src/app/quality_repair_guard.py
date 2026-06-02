"""PR-22 pending quality repair frozen plan storage."""

from __future__ import annotations

from dataclasses import dataclass

from application.repair_plan_fingerprint import repair_plan_fingerprint
from domain.repair_models import RepairOperation


@dataclass
class PendingQualityRepair:
    token: str
    session_id: str
    fingerprint: str
    library_revision: int
    plan_fingerprint: str
    repair_operations: list[RepairOperation]


class QualityRepairGuard:
    def __init__(self) -> None:
        self._pending: PendingQualityRepair | None = None

    def store(
        self,
        *,
        token: str,
        session_id: str,
        fingerprint: str,
        library_revision: int,
        operations: list[RepairOperation],
    ) -> None:
        ops = list(operations)
        self._pending = PendingQualityRepair(
            token=token,
            session_id=session_id,
            fingerprint=fingerprint,
            library_revision=library_revision,
            plan_fingerprint=repair_plan_fingerprint(ops),
            repair_operations=ops,
        )

    def get(self) -> PendingQualityRepair | None:
        return self._pending

    def get_by_token(self, token: str) -> PendingQualityRepair | None:
        pending = self._pending
        if pending and pending.token == token:
            return pending
        return None

    def clear(self) -> None:
        self._pending = None

    def load_operations(self, pending: PendingQualityRepair) -> list[RepairOperation]:
        ops = list(pending.repair_operations)
        if repair_plan_fingerprint(ops) != pending.plan_fingerprint:
            return []
        return ops
