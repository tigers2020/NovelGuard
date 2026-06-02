"""In-memory application settings (PR-20)."""

from __future__ import annotations

from domain.settings_keys import SETTINGS_KEY_INCLUDE_RELATION

_DEFAULTS: dict[str, bool] = {SETTINGS_KEY_INCLUDE_RELATION: False}


class AppSettings:
    def __init__(self) -> None:
        self._bools = dict(_DEFAULTS)

    def get_bool(self, key: str, default: bool = False) -> bool:
        return self._bools.get(key, default)

    def set_bool(self, key: str, value: bool) -> None:
        self._bools[key] = value
