"""UI theme mode."""

from enum import Enum


class ThemeMode(str, Enum):
    """Application color theme."""

    DARK = "dark"
    LIGHT = "light"

    @classmethod
    def from_settings_value(cls, raw: object) -> "ThemeMode":
        if isinstance(raw, str) and raw.lower() == cls.LIGHT.value:
            return cls.LIGHT
        return cls.DARK
