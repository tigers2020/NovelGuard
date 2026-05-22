"""Navigation icons (Qt standard icons until custom SVGs are added)."""

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QStyle, QWidget

_NAV_ICON_MAP: dict[str, str] = {
    "work": "SP_DirHomeIcon",
    "scan": "SP_DirIcon",
    "duplicate": "SP_FileDialogDetailedView",
    "move_organize": "SP_DirOpenIcon",
    "small": "SP_FileIcon",
    "integrity": "SP_DialogApplyButton",
    "encoding": "SP_FileDialogContentsView",
    "stats": "SP_FileDialogInfoView",
    "logs": "SP_FileDialogListView",
    "undo": "SP_ArrowBack",
    "settings": "SP_FileDialogInfoView",
}


def nav_icon(widget: QWidget, tab_name: str) -> QIcon:
    """Return a standard icon for a sidebar tab id."""
    style = widget.style()
    if style is None:
        return QIcon()
    attr = _NAV_ICON_MAP.get(tab_name, "SP_FileIcon")
    standard = getattr(QStyle.StandardPixmap, attr, QStyle.StandardPixmap.SP_FileIcon)
    return style.standardIcon(standard)
