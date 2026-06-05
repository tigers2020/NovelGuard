"""NOV-26 acceptance criteria verification for near/relation post-scan policy ADR."""

from __future__ import annotations

from pathlib import Path

import pytest

ADR_PATH = (
    Path(__file__).resolve().parent.parent
    / "docs"
    / "superpowers"
    / "specs"
    / "033-2026-06-05-near-relation-post-scan-policy-design.md"
)

RELATED_SPECS = (
    "007-2026-06-01-near-duplicate-detection-design.md",
    "008-2026-06-02-relation-filename-blocking-design.md",
    "011-2026-06-02-finalize-cleanup-pipeline-design.md",
)


@pytest.fixture(scope="module")
def adr_text() -> str:
    assert ADR_PATH.is_file(), f"missing ADR: {ADR_PATH}"
    return ADR_PATH.read_text(encoding="utf-8")


def test_ac_written_decision_in_docs(adr_text: str) -> None:
    """AC: Written decision in ADR or spec under docs/."""
    assert "linear: NOV-26" in adr_text
    assert "status: approved" in adr_text
    assert "Hybrid A + D" in adr_text or "Hybrid **A+D**" in adr_text


def test_ac_parent_nov25_linked(adr_text: str) -> None:
    """AC: Parent epic NOV-25 후처리 정책 satisfied."""
    assert "parent: NOV-25" in adr_text
    assert "Persistence (A)" in adr_text
    assert "Presentation (D)" in adr_text


def test_ac_rationale_covers_pr19_pr20_finalize(adr_text: str) -> None:
    """AC: Rationale covers PR-19/PR-20 review-only apply constraints."""
    assert "## Rationale vs PR-19 / PR-20 / Finalize" in adr_text
    assert "PR-19 near review-only apply" in adr_text
    assert "PR-20 relation review-only apply" in adr_text
    assert "Finalize G2" in adr_text
    assert "NOV-17 exact auto-approve" in adr_text
    for spec in RELATED_SPECS:
        assert spec in adr_text


def test_ac_follow_up_linkage(adr_text: str) -> None:
    """AC: B/C/D follow-up linked — B/C rejected; D delegated to NOV-27."""
    assert "## Follow-up issues" in adr_text
    assert "NOV-27" in adr_text
    assert "Auto-mark reviewed" in adr_text
    assert "Auto-exclude" in adr_text
    assert "Rejected for v1" in adr_text


def test_count_semantics_contract(adr_text: str) -> None:
    """Plan Task 4: moveReadyCount / reviewSignalCount invariant documented."""
    assert "moveReadyCount" in adr_text
    assert "reviewSignalCount" in adr_text
    assert "queueCount === moveReadyCount + reviewSignalCount" in adr_text
    assert "exactUnresolvedQueueCount" in adr_text
    assert "Post-scan worker MUST NOT add near/relation auto-approve/exclude hooks" in adr_text
