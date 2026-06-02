"""In-memory application settings (PR-20, PR-28)."""

from __future__ import annotations

from typing import Literal

from domain.settings_keys import (
    ALL_SETTING_KEYS,
    BOOL_SETTING_KEYS,
    RESERVED_SCAN_KEYS,
    SETTINGS_KEY_INCLUDE_RELATION,
    SETTINGS_KEY_SCAN_EXTENSION_FILTER,
    SETTINGS_KEY_SCAN_INCLUDE_HIDDEN,
    SETTINGS_KEY_SCAN_INCLUDE_SUBDIRS,
    SETTINGS_KEY_SCAN_INCREMENTAL,
    SETTINGS_KEY_SCAN_INCLUDE_SYMLINKS,
    STRING_SETTING_KEYS,
)

SettingsSource = Literal["default", "persisted"]
SettingValue = str | bool

_DEFAULTS: dict[str, SettingValue] = {
    SETTINGS_KEY_INCLUDE_RELATION: False,
    SETTINGS_KEY_SCAN_EXTENSION_FILTER: ".txt,.md",
    SETTINGS_KEY_SCAN_INCLUDE_SUBDIRS: True,
    SETTINGS_KEY_SCAN_INCLUDE_HIDDEN: False,
    SETTINGS_KEY_SCAN_INCREMENTAL: False,
    SETTINGS_KEY_SCAN_INCLUDE_SYMLINKS: False,
}


class UnknownSettingKeyError(ValueError):
    """Raised when a setting key is not in ALL_SETTING_KEYS."""


class InvalidSettingValueError(ValueError):
    """Raised when a setting value has the wrong type for its key."""


class AppSettings:
    """Typed in-memory settings. Persistence is added in PR-28 Task 2."""

    def __init__(self) -> None:
        self._values: dict[str, SettingValue] = dict(_DEFAULTS)
        self._sources: dict[str, SettingsSource] = dict.fromkeys(_DEFAULTS, "default")

    def get_value(self, key: str) -> tuple[SettingValue, SettingsSource]:
        self._validate_key(key)
        return self._values[key], self._sources[key]

    def set_value(self, key: str, value: SettingValue) -> tuple[SettingValue, SettingsSource]:
        self._validate_key(key)
        self._validate_value_type(key, value)
        self._values[key] = value
        self._sources[key] = "persisted"
        return value, "persisted"

    def get_bool(self, key: str, default: bool = False) -> bool:
        if key not in BOOL_SETTING_KEYS:
            msg = f"Setting {key!r} is not a boolean setting"
            raise InvalidSettingValueError(msg)
        value, _ = self.get_value(key)
        if not isinstance(value, bool):
            return default
        return value

    def set_bool(self, key: str, value: bool) -> None:
        self.set_value(key, value)

    def is_reserved_scan_key(self, key: str) -> bool:
        return key in RESERVED_SCAN_KEYS

    @staticmethod
    def _validate_key(key: str) -> None:
        if key not in ALL_SETTING_KEYS:
            msg = f"Unknown setting key: {key!r}"
            raise UnknownSettingKeyError(msg)

    @staticmethod
    def _validate_value_type(key: str, value: SettingValue) -> None:
        if key in STRING_SETTING_KEYS:
            if not isinstance(value, str):
                msg = f"Setting {key!r} requires str, got {type(value).__name__}"
                raise InvalidSettingValueError(msg)
            return
        if key in BOOL_SETTING_KEYS:
            if not isinstance(value, bool):
                msg = f"Setting {key!r} requires bool, got {type(value).__name__}"
                raise InvalidSettingValueError(msg)
            return
        msg = f"Setting {key!r} has no registered value type"
        raise InvalidSettingValueError(msg)
