"""Tests for automation.linear.router."""

from __future__ import annotations

import inspect
import json
from pathlib import Path

import automation.linear.router as router_mod

from automation.linear.linear_ids import DEFAULT_LABEL_IDS
from automation.linear.router import (
    _labels_changed,
    _state_changed,
    build_job_payload,
    dedupe_key,
    resolve_planning_prompt,
    route_linear_webhook,
)

_TEST_CFG: dict = {"linear": {"label_ids": dict(DEFAULT_LABEL_IDS)}}

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


_NAME_TO_KEY = {
    "auto:research-done": "research_done",
    "auto:spec-done": "spec_done",
    "auto:plan-done": "plan_done",
    "auto:grill-needs-revision": "grill_needs_revision",
    "auto:todo-list-done": "todo_list_done",
    "auto:impl-done": "impl_done",
}


def _label_set(*names: str) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for name in names:
        key = _NAME_TO_KEY.get(name)
        label_id = DEFAULT_LABEL_IDS.get(key or "")
        row = {"name": name}
        if label_id:
            row["id"] = label_id
        out.append(row)
    return out


def test_router_committed_surface_uses_uuid_routing():
    """Guard: feature-branch checkouts must not regress to name-only _label_names routing."""
    src = inspect.getsource(router_mod)
    assert "from automation.linear.linear_ids import" in src
    assert "issue_in_scope" in src
    assert "has_label_key" in src
    assert "_label_names" not in src


def test_create_backlog_routes_to_create_research():
    route = route_linear_webhook(_issue(action="create", state="Backlog", state_id="b1"))
    assert route is not None
    assert route.prompt_file == "linear/backlog/create-research.md"


def test_create_todo_is_ignored():
    assert route_linear_webhook(_issue(action="create", state="Todo")) is None


def test_status_todo_research_done_routes_write_spec():
    route = route_linear_webhook(
        _issue(
            state="Todo",
            labels=_label_set("auto:research-done"),
            updated_from={"stateId": "b1"},
        ),
    )
    assert route is not None
    assert route.prompt_file == "linear/todo/write-spec.md"


def test_status_todo_todo_list_done_routes_implement_over_planning():
    route = route_linear_webhook(
        _issue(
            state="Todo",
            labels=_label_set("auto:spec-done", "auto:plan-done", "auto:todo-list-done"),
            updated_from={"stateId": "b1"},
        ),
        cfg=_TEST_CFG,
    )
    assert route is not None
    assert route.prompt_file == "linear/in-progress/implement.md"
    assert "todo-list-done→implement" in route.reason


def test_status_in_progress_impl_done_routes_verify():
    route = route_linear_webhook(
        _issue(
            state="In Progress",
            state_id="p1",
            labels=_label_set("auto:impl-done"),
            updated_from={"stateId": "r1"},
        ),
        cfg=_TEST_CFG,
    )
    assert route is not None
    assert route.prompt_file == "linear/in-review/verify.md"


def test_status_stateid_only_routes_verify():
    payload = json.loads(
        (EXAMPLES / "linear-webhook-issue-stateid-only.json").read_text(encoding="utf-8"),
    )
    route = route_linear_webhook(payload, cfg=_TEST_CFG)
    assert route is not None
    assert route.prompt_file == "linear/in-review/verify.md"


def test_status_stateid_only_routes_implement_for_nov38():
    payload = {
        "action": "update",
        "type": "Issue",
        "updatedFrom": {"stateId": "49a46ce6-eb18-4377-95ae-b76f655a77b7"},
        "data": {
            "identifier": "NOV-38",
            "teamId": "97047174-6453-4458-b170-a9bf5f7b52e0",
            "projectId": "20965ebc-3ea7-4787-9310-f15ad9019007",
            "stateId": "0be134b7-bc56-4ba6-ba76-6b0a705e2ded",
            "labelIds": [],
        },
    }
    route = route_linear_webhook(payload, cfg=_TEST_CFG)
    assert route is not None
    assert route.prompt_file == "linear/in-progress/implement.md"


def test_done_status_is_ignored():
    payload = {
        "action": "update",
        "type": "Issue",
        "updatedFrom": {"stateId": "31a91042-9d59-49eb-8821-43ddd92ed76d"},
        "data": {
            "identifier": "NOV-37",
            "teamId": "97047174-6453-4458-b170-a9bf5f7b52e0",
            "projectId": "20965ebc-3ea7-4787-9310-f15ad9019007",
            "stateId": "537a17f3-7fe0-46f0-94d3-89f36f48e98c",
            "labelIds": [DEFAULT_LABEL_IDS["impl_done"], DEFAULT_LABEL_IDS["verify_done"]],
        },
    }
    assert route_linear_webhook(payload, cfg=_TEST_CFG) is None


def test_label_ids_only_routes_by_uuid():
    payload = json.loads(
        (EXAMPLES / "linear-webhook-issue-labelids-only.json").read_text(encoding="utf-8"),
    )
    route = route_linear_webhook(payload, cfg=_TEST_CFG)
    assert route is not None
    assert route.prompt_file == "linear/todo/write-todo-list.md"


def test_build_job_payload_task_is_compact():
    payload = {
        "action": "update",
        "type": "Issue",
        "updatedFrom": {"stateId": "49a46ce6-eb18-4377-95ae-b76f655a77b7"},
        "data": {
            "identifier": "NOV-38",
            "teamId": "97047174-6453-4458-b170-a9bf5f7b52e0",
            "projectId": "20965ebc-3ea7-4787-9310-f15ad9019007",
            "stateId": "0be134b7-bc56-4ba6-ba76-6b0a705e2ded",
            "labelIds": [],
        },
    }
    from automation.linear.router import build_job_payload, route_linear_webhook

    route = route_linear_webhook(payload, cfg=_TEST_CFG)
    assert route is not None
    job = build_job_payload(payload, route, cfg=_TEST_CFG)
    assert job["task"] == "NOV-38: status→In Progress"
    assert "Follow prompt" not in job["task"]
    assert len(job["task"]) < 80


def test_dedupe_key_varies_with_webhook_id():
    payload = _issue(
        state="Todo",
        labels=_label_set("auto:spec-done", "auto:plan-done"),
        updated_from={"labelIds": ["old"]},
    )
    route = route_linear_webhook(payload, cfg=_TEST_CFG)
    assert route is not None
    payload["webhookId"] = "wh-1"
    key_a = dedupe_key(payload, route, cfg=_TEST_CFG)
    payload["webhookId"] = "wh-2"
    key_b = dedupe_key(payload, route, cfg=_TEST_CFG)
    assert key_a != key_b
