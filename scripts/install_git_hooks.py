"""Copy tracked hooks from scripts/hooks/ into .git/hooks/."""

from __future__ import annotations

import shutil
import stat
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
HOOKS_SRC = REPO_ROOT / "scripts" / "hooks"
HOOKS_DST = REPO_ROOT / ".git" / "hooks"


def install_hook(name: str) -> None:
    src = HOOKS_SRC / name
    dst = HOOKS_DST / name
    if not src.is_file():
        raise FileNotFoundError(src)
    shutil.copy2(src, dst)
    mode = dst.stat().st_mode
    dst.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def main() -> int:
    if not (REPO_ROOT / ".git").is_dir():
        print("Not a git repository.", file=sys.stderr)
        return 1

    HOOKS_DST.mkdir(parents=True, exist_ok=True)
    for src in sorted(HOOKS_SRC.iterdir()):
        if src.is_file() and not src.name.startswith("."):
            install_hook(src.name)
            print(f"Installed {src.name} -> .git/hooks/{src.name}")

    print("\nTest guard: new staged test files are blocked unless ALLOW_NEW_TESTS=1.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
