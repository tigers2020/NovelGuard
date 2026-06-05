"""Guardrail: phase prompts stay compact."""

from pathlib import Path

PROMPTS = Path(__file__).resolve().parents[1] / "automation" / "prompts" / "linear"
REPO_ROOT = PROMPTS.parents[1]


def test_linear_prompts_use_compact_runner_brief():
    offenders: list[str] = []
    for path in PROMPTS.rglob("*.md"):
        text = path.read_text(encoding="utf-8")
        if "@docs/agents/runner-brief.md" in text:
            offenders.append(str(path.relative_to(REPO_ROOT)))
        assert "@docs/agents/runner-brief-compact.md" in text
    assert not offenders, f"Full runner-brief still referenced: {offenders}"


def test_write_task_list_prompt_exists():
    path = PROMPTS / "todo" / "write-task-list.md"
    assert path.is_file()
    text = path.read_text(encoding="utf-8")
    assert "## Task list" in text
    assert "auto:task-list-done" in text


def test_legacy_write_todo_list_still_exists():
    path = PROMPTS / "todo" / "write-todo-list.md"
    assert path.is_file()


def test_linear_prompt_file_size_budget():
    for path in PROMPTS.rglob("*.md"):
        chars = len(path.read_text(encoding="utf-8"))
        assert (
            chars < 3500
        ), f"{path.name} too large ({chars} chars); target <3500 after compact brief"
