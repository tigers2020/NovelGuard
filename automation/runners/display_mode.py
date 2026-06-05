from __future__ import annotations

from typing import Literal

DisplayMode = Literal["plain", "tui"]


def resolve_display_mode(args: object, *, stdout_isatty: bool, ci: bool) -> DisplayMode:
    plain = bool(getattr(args, "plain", False))
    tui = bool(getattr(args, "tui", False))
    if plain:
        return "plain"
    if ci and not tui:
        return "plain"
    if not stdout_isatty and not tui:
        return "plain"
    if tui:
        return "tui"
    if stdout_isatty:
        return "tui"
    return "plain"
