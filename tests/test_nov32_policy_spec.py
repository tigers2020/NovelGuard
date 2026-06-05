"""Contract tests for NOV-32 locked policy spec (docs only)."""

from __future__ import annotations

from pathlib import Path

import pytest

SPEC_PATH = (
    Path(__file__).resolve().parents[1]
    / "docs/superpowers/specs/033-2026-06-05-auto-keeper-bulk-approve-policy.md"
)
PLAN_PATH = (
    Path(__file__).resolve().parents[1]
    / "docs/superpowers/plans/033-2026-06-05-auto-keeper-bulk-approve-policy.md"
)


@pytest.fixture
def spec_text() -> str:
    assert SPEC_PATH.is_file(), f"missing canonical spec: {SPEC_PATH}"
    return SPEC_PATH.read_text(encoding="utf-8")


def test_spec_front_matter_locked() -> None:
    text = SPEC_PATH.read_text(encoding="utf-8")
    assert "status: locked" in text
    assert "linear: NOV-32" in text


def test_plan_exists_and_references_spec() -> None:
    assert PLAN_PATH.is_file(), f"missing plan: {PLAN_PATH}"
    plan = PLAN_PATH.read_text(encoding="utf-8")
    assert "033-2026-06-05-auto-keeper-bulk-approve-policy.md" in plan


def test_ac_nov16_execution_approved_cross_ref(spec_text: str) -> None:
    assert "NOV-16" in spec_text
    assert "execution-approved" in spec_text
    assert "approved = execution-approved" in spec_text


def test_ac_exact_near_relation_and_conflict_excluded(spec_text: str) -> None:
    lowered = spec_text.lower()
    for token in ("exact", "near", "relation", "conflict"):
        assert token in lowered
    assert "filters.status" in spec_text or 'filters.status: ["unreviewed"]' in spec_text


def test_ac_keeper_tie_break_order(spec_text: str) -> None:
    assert "size_bytes" in spec_text
    assert "modified_at_ns" in spec_text
    assert "relative_path" in spec_text
    assert "file_id" in spec_text


def test_ac_preview_required_gate(spec_text: str) -> None:
    assert "Preview-required gate" in spec_text or "preview-required gate" in spec_text.lower()
    assert "no auto-apply" in spec_text.lower() or "no** auto-apply" in spec_text


def test_downstream_issues_linked(spec_text: str) -> None:
    for issue in ("NOV-33", "NOV-34", "NOV-35"):
        assert issue in spec_text
