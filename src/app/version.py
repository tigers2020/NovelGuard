"""Release diagnostics metadata (PR-24). Not used for feature gating."""

from __future__ import annotations

import platform
from dataclasses import asdict, dataclass
from typing import Literal

from app.runtime_paths import is_frozen

APP_NAME = "NovelGuard"
APP_VERSION = "0.24.0"
BUILD_TYPE: Literal["dev", "production", "packaged"] = "dev"
GIT_COMMIT: str | None = None
BUILT_AT: str | None = None
FRONTEND_BUILD = "web/build"


@dataclass(frozen=True)
class AppInfo:
    appName: str
    version: str
    buildType: str
    gitCommit: str | None
    builtAt: str | None
    frontendBuild: str
    pythonRuntime: str


def resolve_build_type() -> Literal["dev", "production", "packaged"]:
    if is_frozen():
        return "packaged"
    return BUILD_TYPE


def apply_build_stamp(
    *,
    git_commit: str | None = None,
    built_at: str | None = None,
    build_type: Literal["dev", "production", "packaged"] | None = None,
) -> None:
    """Called by packaging scripts before PyInstaller freeze (plan Task 7)."""
    global GIT_COMMIT, BUILT_AT, BUILD_TYPE
    if git_commit is not None:
        GIT_COMMIT = git_commit
    if built_at is not None:
        BUILT_AT = built_at
    if build_type is not None:
        BUILD_TYPE = build_type


def get_app_info() -> dict[str, object]:
    return asdict(
        AppInfo(
            appName=APP_NAME,
            version=APP_VERSION,
            buildType=resolve_build_type(),
            gitCommit=GIT_COMMIT,
            builtAt=BUILT_AT,
            frontendBuild=FRONTEND_BUILD,
            pythonRuntime=platform.python_version(),
        )
    )
