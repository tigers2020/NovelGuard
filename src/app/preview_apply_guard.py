"""PR-13 pending preview state + immutable plan storage."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from application.plan_fingerprint import (
    plan_fingerprint,
    preview_operation_to_dict,
    preview_operations_from_dicts,
)
from domain.apply_models import PreviewOperation


@dataclass
class PendingPreview:
    token: str
    fingerprint: str
    library_revision: int
    plan_fingerprint: str
    preview_operations: list[PreviewOperation]

    def operations_as_dicts(self) -> list[dict[str, Any]]:
        return [preview_operation_to_dict(op) for op in self.preview_operations]


class PreviewApplyGuard:
    def __init__(self) -> None:
        self._pending: PendingPreview | None = None

    def store(
        self,
        *,
        token: str,
        fingerprint: str,
        library_revision: int,
        operations: list[PreviewOperation],
    ) -> None:
        self._pending = PendingPreview(
            token=token,
            fingerprint=fingerprint,
            library_revision=library_revision,
            plan_fingerprint=plan_fingerprint(operations),
            preview_operations=list(operations),
        )

    def get(self) -> PendingPreview | None:
        return self._pending

    def get_by_token(self, token: str) -> PendingPreview | None:
        pending = self._pending
        if pending and pending.token == token:
            return pending
        return None

    def clear(self) -> None:
        self._pending = None

    def load_operations(self, pending: PendingPreview) -> list[PreviewOperation]:
        stored_fp = pending.plan_fingerprint
        ops = list(pending.preview_operations)
        if plan_fingerprint(ops) != stored_fp:
            return []
        return ops

    @staticmethod
    def operations_from_pending_dict(data: dict[str, Any]) -> list[PreviewOperation]:
        raw = data.get("preview_operations")
        if not isinstance(raw, list):
            return []
        return preview_operations_from_dicts(raw)
