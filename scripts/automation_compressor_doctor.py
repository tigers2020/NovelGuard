#!/usr/bin/env python3
"""Smoke-test Ollama context compressor."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from automation.runners.config import load_config  # noqa: E402
from automation.runners.context_compressor import compress_job_context  # noqa: E402


def main() -> int:
    cfg = load_config()
    comp = cfg.get("context_compressor") or {}
    if not comp.get("enabled"):
        print("context_compressor.enabled is false — enable to test")
        return 0
    payload = {
        "id": "doctor-smoke",
        "issue_identifier": "NOV-0",
        "prompt_file": "linear/in-progress/implement.md",
        "meta": {"route_reason": "doctor"},
    }
    raw = "Doctor smoke: preserve [LOCK] demo decision."
    try:
        result = compress_job_context(cfg, payload=payload, raw_context=raw)
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"compressor doctor failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, ensure_ascii=False))
    memory = result.get("memory") or {}
    if not memory.get("goal"):
        print("memory.goal empty after compression", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
