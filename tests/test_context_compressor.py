"""Tests for automation.runners.context_compressor."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from automation.runners.context_compressor import (
    _coerce_memory,
    compress_job_context,
    load_schema,
    memory_cache_path,
    source_hash,
)


def test_source_hash_stable():
    assert source_hash("hello") == source_hash("hello")
    assert source_hash("hello") != source_hash("world")


def test_load_schema_has_required_fields():
    schema = load_schema()
    assert "locked_decisions" in schema["properties"]


def test_compress_job_context_uses_cache(tmp_path: Path):
    cfg = {
        "context_compressor": {
            "enabled": True,
            "endpoint": "http://localhost:11434/api/generate",
            "model": "gemma4:latest",
            "cache_dir": str(tmp_path),
            "max_input_chars": 5000,
            "timeout_seconds": 30,
            "num_ctx": 8192,
            "top_p": 0.9,
        }
    }
    payload = {
        "id": "linear-NOV-38-in-progress-implement-x",
        "issue_identifier": "NOV-38",
        "prompt_file": "linear/in-progress/implement.md",
        "meta": {"route_reason": "status→In Progress"},
    }
    raw = "Issue NOV-38: implement bridge timeout table."
    fake_memory = {
        "goal": "Implement bridge timeouts",
        "current_phase": "implementation",
        "locked_decisions": ["[LOCK] No LibrarySession split"],
        "must_keep_context": [],
        "changed_files": ["web/src/bridgeTimeouts.ts"],
        "relevant_tests": ["web bridge contract tests"],
        "risks": [],
        "unknowns": [],
        "discarded_noise": ["greeting"],
        "next_prompt": "Implement bridgeTimeouts.ts per spec.",
    }

    with patch(
        "automation.runners.context_compressor._ollama_generate_json",
        return_value=fake_memory,
    ):
        first = compress_job_context(cfg, payload=payload, raw_context=raw)
        second = compress_job_context(cfg, payload=payload, raw_context=raw)

    assert first["memory"] == fake_memory
    assert second["cached"] is True
    assert memory_cache_path(tmp_path, payload["id"]).is_file()


def test_coerce_memory_fills_missing_required_keys():
    payload = {
        "issue_identifier": "NOV-0",
        "prompt_file": "linear/in-progress/implement.md",
        "meta": {"route_reason": "doctor"},
    }
    raw = "Doctor smoke: preserve [LOCK] demo decision."
    memory = _coerce_memory(
        {"locked_decisions": ["[LOCK] demo decision"], "next_prompt": "Run doctor."},
        payload=payload,
        raw_context=raw,
    )
    assert memory["goal"] == "NOV-0"
    assert memory["current_phase"] == "implement"
    assert memory["locked_decisions"] == ["[LOCK] demo decision"]
    assert memory["next_prompt"] == "Run doctor."


def test_compress_coerces_partial_ollama_response(tmp_path: Path):
    cfg = {
        "context_compressor": {
            "enabled": True,
            "endpoint": "http://localhost:11434/api/generate",
            "model": "gemma4:latest",
            "cache_dir": str(tmp_path),
            "max_input_chars": 5000,
            "timeout_seconds": 30,
            "num_ctx": 8192,
            "top_p": 0.9,
        }
    }
    payload = {
        "id": "doctor-smoke",
        "issue_identifier": "NOV-0",
        "prompt_file": "linear/in-progress/implement.md",
        "meta": {"route_reason": "doctor"},
    }
    raw = "Doctor smoke: preserve [LOCK] demo decision."
    partial = {
        "locked_decisions": ["[LOCK] demo decision"],
        "next_prompt": "Preserve locked decision.",
    }

    with patch(
        "automation.runners.context_compressor._ollama_generate_json",
        return_value=partial,
    ):
        result = compress_job_context(cfg, payload=payload, raw_context=raw)

    assert result["memory"]["goal"] == "NOV-0"
    assert result["memory"]["locked_decisions"] == ["[LOCK] demo decision"]


def test_compress_skipped_when_disabled():
    cfg = {"context_compressor": {"enabled": False}}
    result = compress_job_context(cfg, payload={"id": "x"}, raw_context="raw")
    assert result["skipped"] is True
    assert result["memory"] is None
