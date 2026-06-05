#!/usr/bin/env python3
"""Smoke-test Ollama context compressor."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from automation.runners.config import load_config
from automation.runners.context_compressor import compress_job_context


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
    result = compress_job_context(cfg, payload=payload, raw_context=raw)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result.get("memory") else 1


if __name__ == "__main__":
    raise SystemExit(main())
