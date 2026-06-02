"""Settings persistence port (PR-28)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from application.app_settings import _DEFAULTS, SettingsSource, SettingValue
from domain.settings_keys import ALL_SETTING_KEYS, BOOL_SETTING_KEYS, STRING_SETTING_KEYS
from infrastructure.json_settings_store import JsonSettingsStore


class SettingsStore:
    def __init__(self, path: Path) -> None:
        self._json = JsonSettingsStore(path)

    def load_merged(self) -> tuple[dict[str, SettingValue], dict[str, SettingsSource]]:
        persisted = self._json.load()
        values: dict[str, SettingValue] = dict(_DEFAULTS)
        sources: dict[str, SettingsSource] = dict.fromkeys(_DEFAULTS, "default")
        for key in ALL_SETTING_KEYS:
            if key not in persisted:
                continue
            coerced = self._coerce_persisted(key, persisted[key])
            if coerced is None:
                continue
            values[key] = coerced
            sources[key] = "persisted"
        return values, sources

    def persist_values(self, values: dict[str, SettingValue]) -> None:
        data: dict[str, Any] = {}
        for key in ALL_SETTING_KEYS:
            value = values.get(key)
            if value is None:
                continue
            if value == _DEFAULTS.get(key):
                continue
            data[key] = value
        self._json.save(data)

    @staticmethod
    def _coerce_persisted(key: str, raw: Any) -> SettingValue | None:
        if key in STRING_SETTING_KEYS:
            return raw if isinstance(raw, str) else None
        if key in BOOL_SETTING_KEYS:
            return raw if isinstance(raw, bool) else None
        return None
