"""Tests for automation.linear.router."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from automation.linear.router import (
    _labels_changed,
    _state_changed,
    build_job_payload,
    dedupe_key,
    route_linear_webhook,
)

EXAMPLES = Path(__file__).resolve().parents[1] / "automation" / "examples"


def _issue(
    *,
    action: str = "update",
    state: str = "Todo",
    state_id: str = "t1",
    identifier: str = "NOV-X",
    labels: list[dict[str, str]] | None = None,
    updated_from: dict | None = None,
) -> dict:
    payload: dict = {
        "action": action,
        "type": "Issue",
        "data": {
            "identifier": identifier,
            "project": {"name": "NovelGuard"},
            "team": {"name": "NoverGuard"},
            "state": {"name": state, "id": state_id},
            "labels": labels or [],
        },
    }
    if updated_from is not None:
        payload["updatedFrom"] = updated_from
    return payload


def test_create_backlog_routes_to_00():
    route = route_linear_webhook(_issue(action="create", state="Backlog", state_id="b1"))
    assert route is not None
    assert route.prompt_file == "00-linear-create-pr-to-spec.md"
    assert route.reason == "issue.created"


def test_create_todo_is_ignored():
    assert route_linear_webhook(_issue(action="create", state="Todo")) is None


def test_create_done_is_ignored():
    assert route_linear_webhook(_issue(action="create", state="Done")) is None


def test_status_todo_routes_to_01():
    route = route_linear_webhook(
        _issue(state="Todo", updated_from={"stateId": "b1"}),
    )
    assert route is not None
    assert route.prompt_file == "01-linear-status-changed-router.md"
    assert route.reason == "status→Todo"


def test_status_in_progress_routes_to_02():
    route = route_linear_webhook(
        _issue(state="In Progress", state_id="p1", updated_from={"stateId": "t1"}),
    )
    assert route is not None
    assert route.prompt_file == "02-linear-in-progress-implement.md"


def test_status_in_review_routes_to_03():
    route = route_linear_webhook(
        _issue(state="In Review", state_id="r1", updated_from={"stateId": "p1"}),
    )
    assert route is not None
    assert route.prompt_file == "03-linear-in-review-verification.md"


def test_label_only_todo_routes_to_01():
    route = route_linear_webhook(
        _issue(
            state="Todo",
            labels=[{"name": "auto:plan-done"}],
            updated_from={"labelIds": ["old-id"]},
        ),
    )
    assert route is not None
    assert route.prompt_file == "01-linear-status-changed-router.md"
    assert route.reason == "labels@Todo"


def test_label_only_in_progress_is_ignored():
    assert (
        route_linear_webhook(
            _issue(
                state="In Progress",
                state_id="p1",
                labels=[{"name": "auto:impl-done"}],
                updated_from={"labelIds": []},
            ),
        )
        is None
    )


def test_label_only_fixture_file():
    payload = json.loads(
        (EXAMPLES / "linear-webhook-issue-label-plan-done.json").read_text(encoding="utf-8"),
    )
    assert _state_changed(payload, payload["data"]) is False
    assert _labels_changed(payload) is True
    route = route_linear_webhook(payload)
    assert route is not None
    assert route.prompt_file == "01-linear-status-changed-router.md"
    assert route.reason == "labels@Todo"


def test_dedupe_key_includes_labels():
    payload = _issue(
        state="Todo",
        labels=[{"name": "auto:spec-done"}, {"name": "auto:plan-done"}],
        updated_from={"labelIds": []},
    )
    route = route_linear_webhook(payload)
    assert route is not None
    key = dedupe_key(payload, route)
    assert "auto:plan-done" in key
    assert "auto:spec-done" in key


def test_job_id_includes_auto_labels():
    payload = _issue(
        state="Todo",
        labels=[{"name": "auto:plan-done"}],
        updated_from={"labelIds": []},
    )
    route = route_linear_webhook(payload)
    assert route is not None
    job = build_job_payload(payload, route)
    assert "plan-done" in job["id"]


def test_example_fixtures_route():
    create = json.loads((EXAMPLES / "linear-webhook-issue-create.json").read_text(encoding="utf-8"))
    update = json.loads((EXAMPLES / "linear-webhook-issue-update.json").read_text(encoding="utf-8"))
    assert route_linear_webhook(create).prompt_file == "00-linear-create-pr-to-spec.md"
    assert route_linear_webhook(update).prompt_file == "01-linear-status-changed-router.md"
