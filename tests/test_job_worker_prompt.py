"""Tests for prompt rendering in job_worker."""

from __future__ import annotations

from unittest.mock import patch

from automation.runners.job_worker import render_prompt


def test_render_prompt_injects_context_memory_when_enabled(tmp_path):
    cfg = {
        "prompts": {"dir": "automation/prompts"},
        "context_compressor": {"enabled": True, "cache_dir": str(tmp_path)},
    }
    payload = {
        "id": "linear-NOV-38-test",
        "repo": "novelguard",
        "kind": "linear",
        "task": "NOV-38: status→In Progress",
        "prompt_file": "linear/in-progress/implement.md",
        "issue_identifier": "NOV-38",
        "issue_url": "https://linear.app/example/NOV-38",
        "linear_state": "In Progress",
        "meta": {"route_reason": "status→In Progress", "linear_event": {}},
    }
    fake_memory = {
        "goal": "g",
        "current_phase": "implementation",
        "locked_decisions": [],
        "must_keep_context": [],
        "changed_files": [],
        "relevant_tests": [],
        "risks": [],
        "unknowns": [],
        "discarded_noise": [],
        "next_prompt": "Do the thing.",
    }
    with patch(
        "automation.runners.job_worker.compress_job_context",
        return_value={"memory": fake_memory, "cached": False},
    ):
        rendered = render_prompt(cfg, payload, branch="ai/job-test")

    assert "{{CONTEXT_MEMORY_JSON}}" not in rendered
    assert "Do the thing." in rendered


def test_resolve_legacy_write_todo_list_prompt_path():
    from automation.runners.job_worker import _resolve_prompt_file
    from automation.runners.config import repo_root

    prompts_dir = repo_root() / "automation" / "prompts"
    resolved = _resolve_prompt_file(prompts_dir, "linear/todo/write-todo-list.md")
    assert resolved == "linear/todo/write-todo-list.md"
    assert (prompts_dir / resolved).is_file()


def test_resolve_write_task_list_prompt_path():
    from automation.runners.job_worker import _resolve_prompt_file
    from automation.runners.config import repo_root

    prompts_dir = repo_root() / "automation" / "prompts"
    resolved = _resolve_prompt_file(prompts_dir, "linear/todo/write-task-list.md")
    assert resolved == "linear/todo/write-task-list.md"


def test_render_prompt_empty_memory_when_compressor_disabled():
    cfg = {
        "prompts": {"dir": "automation/prompts"},
        "context_compressor": {"enabled": False},
    }
    payload = {
        "id": "linear-NOV-38-test",
        "repo": "novelguard",
        "kind": "linear",
        "task": "NOV-38: status→In Progress",
        "prompt_file": "linear/in-progress/implement.md",
        "issue_identifier": "NOV-38",
        "issue_url": "",
        "linear_state": "In Progress",
        "meta": {"route_reason": "status→In Progress", "linear_event": {}},
    }
    rendered = render_prompt(cfg, payload, branch="ai/job-test")
    assert '"goal"' not in rendered or "{}" in rendered
