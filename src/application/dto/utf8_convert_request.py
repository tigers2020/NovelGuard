"""UTF-8 conversion request DTO."""

from dataclasses import dataclass
from typing import Literal

Utf8ConvertMode = Literal["auto_eligible", "manual_default", "manual_include_info"]


@dataclass(frozen=True)
class Utf8ConvertRequest:
    """Request to convert files to UTF-8."""

    file_ids: list[int] | None
    mode: Utf8ConvertMode
