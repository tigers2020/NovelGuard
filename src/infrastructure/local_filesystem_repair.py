"""Local filesystem adapter for PR-22 UTF-8 repair."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from application.ports.filesystem_apply import ApplyRowResult


class LocalFilesystemRepairAdapter:
    def read_bytes(self, path: Path) -> bytes:
        return path.read_bytes()

    def backup_original(
        self,
        backup_dir: Path,
        *,
        original_bytes: bytes,
        metadata: dict[str, object],
    ) -> ApplyRowResult:
        try:
            backup_dir.mkdir(parents=True, exist_ok=True)
            (backup_dir / "original.bin").write_bytes(original_bytes)
            meta = {
                **metadata,
                "backupCreatedAt": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            }
            (backup_dir / "metadata.json").write_text(
                json.dumps(meta, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError as exc:
            return ApplyRowResult(outcome="error", error=str(exc))
        return ApplyRowResult(outcome="ok")

    def write_utf8_atomic(self, path: Path, text: str, *, temp_suffix: str) -> ApplyRowResult:
        temp_path = path.parent / f"{path.name}{temp_suffix}"
        try:
            temp_path.write_text(text, encoding="utf-8")
            temp_path.replace(path)
        except OSError as exc:
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except OSError:
                    pass
            return ApplyRowResult(outcome="error", error=str(exc))
        return ApplyRowResult(outcome="ok")
