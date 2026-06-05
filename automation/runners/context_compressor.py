"""Compress job context via local Ollama before Cursor prompt delivery."""

from __future__ import annotations

import hashlib
import json
import urllib.request
from pathlib import Path
from typing import Any

from automation.runners.config import repo_root

_SCHEMA_PATH = (
    Path(__file__).resolve().parents[1] / "schemas" / "context_memory.schema.json"
)

_COMPRESSOR_PROMPT = """You are a strict context compressor for an automation coding pipeline.
Return ONLY valid JSON matching the schema fields.
Preserve locked_decisions and destructive-action warnings verbatim.
Do not invent files, labels, commits, test results, or status changes.
Remove boilerplate and progress chatter.
Keep next_prompt under 1200 characters.

Input:
{raw}
"""


def load_schema() -> dict[str, Any]:
    return json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))


def source_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _compressor_cfg(cfg: dict[str, Any]) -> dict[str, Any]:
    return cfg.get("context_compressor") or {}


def memory_cache_path(cache_dir: Path, job_id: str) -> Path:
    safe = job_id.replace("/", "_")
    return cache_dir / safe / "memory.json"


def _cache_dir(cfg: dict[str, Any]) -> Path:
    raw = _compressor_cfg(cfg).get("cache_dir") or "automation/context_cache"
    path = Path(raw)
    if not path.is_absolute():
        path = repo_root() / path
    path.mkdir(parents=True, exist_ok=True)
    return path


def _ollama_generate_json(
    *,
    endpoint: str,
    model: str,
    prompt: str,
    options: dict[str, Any],
    timeout: float,
) -> dict[str, Any]:
    body = json.dumps(
        {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": options,
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        endpoint,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return json.loads(data["response"])


def _validate_memory(memory: dict[str, Any]) -> None:
    schema = load_schema()
    required = schema.get("required") or []
    for key in required:
        if key not in memory:
            raise ValueError(f"context memory missing required key: {key}")
    if len(str(memory.get("next_prompt") or "")) > 1200:
        raise ValueError("next_prompt exceeds 1200 chars")


def compress_job_context(
    cfg: dict[str, Any],
    *,
    payload: dict[str, Any],
    raw_context: str,
) -> dict[str, Any]:
    comp = _compressor_cfg(cfg)
    if not comp.get("enabled"):
        return {"memory": None, "cached": False, "skipped": True}

    job_id = str(payload.get("id") or "unknown")
    cache_dir = _cache_dir(cfg)
    cache_file = memory_cache_path(cache_dir, job_id)
    digest = source_hash(raw_context)
    meta_file = cache_file.parent / "source_hash.txt"

    if (
        cache_file.is_file()
        and meta_file.is_file()
        and meta_file.read_text(encoding="utf-8").strip() == digest
    ):
        memory = json.loads(cache_file.read_text(encoding="utf-8"))
        return {"memory": memory, "cached": True, "source_hash": digest}

    clipped = raw_context[: int(comp.get("max_input_chars") or 12000)]
    prompt = _COMPRESSOR_PROMPT.format(raw=clipped)
    options = {
        "temperature": 0,
        "num_ctx": int(comp.get("num_ctx") or 32768),
        "top_p": float(comp.get("top_p") or 0.9),
    }
    memory = _ollama_generate_json(
        endpoint=str(comp.get("endpoint") or "http://localhost:11434/api/generate"),
        model=str(comp.get("model") or "gemma4:latest"),
        prompt=prompt,
        options=options,
        timeout=float(comp.get("timeout_seconds") or 180),
    )
    _validate_memory(memory)

    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(json.dumps(memory, ensure_ascii=False, indent=2), encoding="utf-8")
    meta_file.write_text(digest + "\n", encoding="utf-8")

    ratio = len(json.dumps(memory)) / max(1, len(clipped))
    return {
        "memory": memory,
        "cached": False,
        "source_hash": digest,
        "compression_ratio": ratio,
    }
