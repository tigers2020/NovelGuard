"""Tests for automation.linear.router."""

from __future__ import annotations

from automation.linear.router import (
    build_job_payload,
    classify_linear_events,
    route_linear_webhook,
    route_linear_webhook_events,
)


def _issue(
    *,
    action: str = "update",
    state: str = "Todo",
    state_id: str = "t1",
    identifier: str = "NOV-X",
    labels: list[dict[str, str]] | None = None,
    label_ids: list[str] | None = None,
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
            "labelIds": label_ids or [],
        },
    }
    if updated_from is not None:
        payload["updatedFrom"] = updated_from
    return payload


def _label(label_id: str, name: str) -> dict[str, str]:
    return {"id": label_id, "name": name}


def _route(payload: dict) -> str | None:
    route = route_linear_webhook(payload)
    return route.prompt_file if route is not None else None


def test_create_backlog_routes_once_to_00():
    routes = route_linear_webhook_events(_issue(action="create", state="Backlog", state_id="b1"))
    assert len(routes) == 1
    assert routes[0].route.prompt_file == "00-linear-create-pr-to-spec.md"
    assert routes[0].event["trigger"] == "linear.issue.created"


def test_todo_added_research_done_routes_to_01a():
    assert _route(
        _issue(
            state="Todo",
            labels=[_label("l1", "auto:research-done")],
            label_ids=["l1"],
            updated_from={"labelIds": []},
        )
    ) == "01a-linear-spec.md"


def test_backlog_added_spec_done_routes_to_01b():
    assert _route(
        _issue(
            state="Backlog",
            labels=[_label("l2", "auto:spec-done")],
            label_ids=["l2"],
            updated_from={"labelIds": []},
        )
    ) == "01b-linear-grill-plan.md"


def test_todo_added_grill_revision_routes_to_01c():
    assert _route(
        _issue(
            state="Todo",
            labels=[_label("l3", "auto:grill-needs-revision")],
            label_ids=["l3"],
            updated_from={"labelIds": []},
        )
    ) == "01c-linear-spec-revise.md"


def test_todo_added_plan_done_routes_to_01d():
    assert _route(
        _issue(
            state="Todo",
            labels=[_label("l4", "auto:plan-done")],
            label_ids=["l4"],
            updated_from={"labelIds": []},
        )
    ) == "01d-linear-todo-list.md"


def test_in_progress_status_and_todo_label_routes_once_to_02():
    payload = _issue(
        state="In Progress",
        state_id="p1",
        labels=[_label("l5", "auto:todo-list-done")],
        label_ids=["l5"],
        updated_from={"stateId": "t1", "labelIds": []},
    )
    routes = route_linear_webhook_events(payload)
    assert [item.route.prompt_file for item in routes] == ["02-linear-in-progress-implement.md"]


def test_in_review_status_and_impl_label_routes_once_to_03():
    payload = _issue(
        state="In Review",
        state_id="r1",
        labels=[_label("l6", "auto:impl-done")],
        label_ids=["l6"],
        updated_from={"stateId": "p1", "labelIds": []},
    )
    routes = route_linear_webhook_events(payload)
    assert [item.route.prompt_file for item in routes] == [
        "03-linear-in-review-verification.md"
    ]


def test_non_auto_label_change_does_not_route():
    payload = _issue(
        state="Todo",
        labels=[_label("l7", "triaged")],
        label_ids=["l7"],
        updated_from={"labelIds": []},
    )
    assert classify_linear_events(payload) == []
    assert route_linear_webhook_events(payload) == []


def test_removed_auto_label_only_does_not_route():
    payload = _issue(
        state="Todo",
        labels=[],
        label_ids=[],
        updated_from={"labelIds": ["l4"]},
    )
    assert classify_linear_events(payload) == []
    assert route_linear_webhook_events(payload) == []


def test_one_webhook_dedupes_same_issue_state_prompt():
    payload = _issue(
        state="In Progress",
        state_id="p1",
        labels=[_label("l5", "auto:todo-list-done")],
        label_ids=["l5"],
        updated_from={"stateId": "t1", "labelIds": []},
    )
    routes = route_linear_webhook_events(payload)
    keys = {
        (
            payload["data"]["identifier"],
            payload["data"]["state"]["name"],
            item.route.prompt_file,
        )
        for item in routes
    }
    assert len(routes) == len(keys) == 1


def test_status_in_progress_without_label_routes_to_02():
    assert _route(
        _issue(state="In Progress", state_id="p1", updated_from={"stateId": "t1"})
    ) == "02-linear-in-progress-implement.md"


def test_status_in_review_without_label_routes_to_03():
    assert _route(
        _issue(state="In Review", state_id="r1", updated_from={"stateId": "p1"})
    ) == "03-linear-in-review-verification.md"


def test_todo_status_without_phase_label_is_ignored():
    assert _route(_issue(state="Todo", updated_from={"stateId": "b1"})) is None


def test_job_payload_task_is_compact_and_keeps_reason():
    payload = _issue(
        state="Todo",
        labels=[_label("l4", "auto:plan-done")],
        label_ids=["l4"],
        updated_from={"labelIds": []},
    )
    route = route_linear_webhook(payload)
    assert route is not None
    job = build_job_payload(payload, route)
    assert job["task"] == "NOV-X · Todo · Todo+auto:plan-done→todo-list"
    assert job["meta"]["route_reason"] == "Todo+auto:plan-done→todo-list"
