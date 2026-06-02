"""Application setting keys (PR-20, PR-28)."""

from __future__ import annotations

SETTINGS_KEY_INCLUDE_RELATION = "include_relation"

SETTINGS_KEY_SCAN_EXTENSION_FILTER = "scan.extensionFilter"
SETTINGS_KEY_SCAN_INCLUDE_SUBDIRS = "scan.includeSubdirs"
SETTINGS_KEY_SCAN_INCLUDE_HIDDEN = "scan.includeHidden"
SETTINGS_KEY_SCAN_INCREMENTAL = "scan.incrementalScan"
SETTINGS_KEY_SCAN_INCLUDE_SYMLINKS = "scan.includeSymlinks"

VISIBLE_SCAN_KEYS: frozenset[str] = frozenset(
    {
        SETTINGS_KEY_SCAN_EXTENSION_FILTER,
        SETTINGS_KEY_SCAN_INCLUDE_SUBDIRS,
        SETTINGS_KEY_SCAN_INCLUDE_HIDDEN,
    }
)

RESERVED_SCAN_KEYS: frozenset[str] = frozenset(
    {
        SETTINGS_KEY_SCAN_INCREMENTAL,
        SETTINGS_KEY_SCAN_INCLUDE_SYMLINKS,
    }
)

ALL_SCAN_SETTING_KEYS: frozenset[str] = VISIBLE_SCAN_KEYS | RESERVED_SCAN_KEYS

ALL_SETTING_KEYS: frozenset[str] = (
    frozenset({SETTINGS_KEY_INCLUDE_RELATION}) | ALL_SCAN_SETTING_KEYS
)

STRING_SETTING_KEYS: frozenset[str] = frozenset({SETTINGS_KEY_SCAN_EXTENSION_FILTER})

BOOL_SETTING_KEYS: frozenset[str] = ALL_SETTING_KEYS - STRING_SETTING_KEYS
