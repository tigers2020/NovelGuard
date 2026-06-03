"""Load automation/config.yaml (or .json)."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_CONFIG = _REPO_ROOT / "automation" / "config.yaml"


def repo_root() -> Path:
    return _REPO_ROOT


def config_path() -> Path:
    env = os.environ.get("AUTOMATION_CONFIG")
    if env:
        return Path(env).expanduser().resolve()
    return _DEFAULT_CONFIG


def load_config(path: Path | None = None) -> dict[str, Any]:
    cfg_path = path or config_path()
    if not cfg_path.is_file():
        example = cfg_path.parent / "config.example.yaml"
        raise FileNotFoundError(f"Missing {cfg_path}. Copy {example} to {cfg_path.name} and edit.")
    text = cfg_path.read_text(encoding="utf-8")
    if cfg_path.suffix.lower() in (".yaml", ".yml"):
        try:
            import yaml
        except ImportError as exc:
            raise SystemExit(
                "YAML config requires PyYAML: pip install pyyaml "
                "(or use automation optional: pip install -e '.[automation]')"
            ) from exc
        data = yaml.safe_load(text)
    else:
        data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError(f"Config root must be a mapping: {cfg_path}")
    return data


def repo_path(cfg: dict[str, Any], repo_key: str) -> Path:
    repos = cfg.get("repos") or {}
    entry = repos.get(repo_key)
    if not isinstance(entry, dict):
        raise KeyError(f"Unknown repo key: {repo_key!r}")
    raw = entry.get("path", ".")
    path = Path(str(raw))
    if not path.is_absolute():
        path = (repo_root() / path).resolve()
    return path
