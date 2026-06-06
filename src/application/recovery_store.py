"""Persistence for recovery checkpoints and sealed undo manifests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from application.undo_manifest_errors import UndoManifestValidationError


class JsonlRecoveryStore:
    def __init__(
        self,
        *,
        checkpoints_path: Path,
        undo_plans_dir: Path,
    ) -> None:
        self._checkpoints_path = checkpoints_path
        self._undo_plans_dir = undo_plans_dir

    @property
    def checkpoints_path(self) -> Path:
        return self._checkpoints_path

    @property
    def undo_plans_dir(self) -> Path:
        return self._undo_plans_dir

    def append_checkpoint(self, record: dict[str, Any]) -> None:
        self._checkpoints_path.parent.mkdir(parents=True, exist_ok=True)
        with self._checkpoints_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    def write_undo_manifest(self, manifest: dict[str, Any]) -> Path:
        undo_plan_id = manifest["undoPlanId"]
        self._undo_plans_dir.mkdir(parents=True, exist_ok=True)
        path = self.undo_manifest_path(undo_plan_id)
        path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def undo_manifest_path(self, undo_plan_id: str) -> Path:
        return self._undo_plans_dir / f"{undo_plan_id}.json"

    def read_undo_manifest_raw(self, undo_plan_id: str) -> dict[str, Any]:
        path = self.undo_manifest_path(undo_plan_id)
        if not path.is_file():
            raise UndoManifestValidationError(
                "MANIFEST_NOT_FOUND",
                f"undo plan not found: {undo_plan_id}",
            )
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise UndoManifestValidationError("MANIFEST_MALFORMED", "invalid JSON") from exc
        if not isinstance(payload, dict):
            raise UndoManifestValidationError("MANIFEST_MALFORMED", "manifest must be an object")
        return payload
