"""Tests for automation.linear.router."""

from __future__ import annotations

import json
from pathlib import Path

from automation.linear.router import (
    _labels_changed,
    _state_changed,
    build_job_payload,
    dedupe_key,
    resolve_planning_prompt,
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


def _label_set(*names: str) -> list[dict[str, str]]:
    return [{"name": n} for n in names]


def test_create_backlog_routes_to_create_research():
    route = route_linear_webhook(_issue(action="create", state="Backlog", state_id="b1"))
    assert route is not None
    assert route.prompt_file == "linear/backlog/create-research.md"
    assert route.reason == "issue.created"


def test_create_todo_is_ignored():
    assert route_linear_webhook(_issue(action="create", state="Todo")) is None


def test_create_done_is_ignored():
    assert route_linear_webhook(_issue(action="create", state="Done")) is None


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
    assert route.reason == "status→Todo"


def test_status_backlog_spec_done_routes_grill_plan():
    route = route_linear_webhook(
        _issue(
            state="Backlog",
            state_id="b1",
            labels=_label_set("auto:spec-done"),
            updated_from={"stateId": "t1"},
        ),
    )
    assert route is not None
    assert route.prompt_file == "linear/backlog/grill-plan.md"


def test_status_todo_plan_done_routes_write_todo_list():
    route = route_linear_webhook(
        _issue(
            state="Todo",
            labels=_label_set("auto:spec-done", "auto:plan-done"),
            updated_from={"stateId": "b1"},
        ),
    )
    assert route is not None
    assert route.prompt_file == "linear/todo/write-todo-list.md"


def test_status_in_progress_routes_implement():
    route = route_linear_webhook(
        _issue(
            state="In Progress",
            state_id="p1",
            labels=_label_set("auto:todo-list-done"),
            updated_from={"stateId": "t1"},
        ),
    )
    assert route is not None
    assert route.prompt_file == "linear/in-progress/implement.md"


def test_status_in_review_routes_verify():
    route = route_linear_webhook(
        _issue(
            state="In Review",
            state_id="r1",
            updated_from={"stateId": "p1"},
        ),
    )
    assert route is not None
    assert route.prompt_file == "linear/in-review/verify.md"


def test_label_only_plan_done_routes_write_todo_list():
    route = route_linear_webhook(
        _issue(
            state="Todo",
            labels=_label_set("auto:spec-done", "auto:plan-done"),
            updated_from={"labelIds": ["old-id"]},
        ),
    )
    assert route is not None
    assert route.prompt_file == "linear/todo/write-todo-list.md"
    assert route.reason == "labels@Todo"


def test_label_only_progress_triaging_is_ignored():
    assert (
        route_linear_webhook(
            _issue(
                state="Backlog",
                state_id="b1",
                labels=_label_set("auto:triaging"),
                updated_from={"labelIds": []},
            ),
        )
        is None
    )


def test_label_only_in_progress_is_ignored():
    assert (
        route_linear_webhook(
            _issue(
                state="In Progress",
                state_id="p1",
                labels=_label_set("auto:impl-running"),
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
    assert route.prompt_file == "linear/todo/write-todo-list.md"
    assert route.reason == "labels@Todo"


def test_resolve_planning_priority_grill_over_plan():
    labels = frozenset({"auto:grill-needs-revision", "auto:plan-done"})
    assert resolve_planning_prompt("Todo", labels) == "linear/todo/revise-spec.md"


def test_resolve_planning_defer_spec_without_plan():
    labels = frozenset({"auto:spec-done"})
    assert resolve_planning_prompt("Todo", labels) == "linear/todo/defer-to-backlog.md"


def test_dedupe_key_ignores_labels():
    payload = _issue(
        state="Todo",
        labels=_label_set("auto:spec-done", "auto:plan-done"),
        updated_from={"labelIds": []},
    )
    route = route_linear_webhook(payload)
    assert route is not None
    key = dedupe_key(payload, route)
    assert key == "NOV-X:linear/todo/write-todo-list.md:Todo"
    payload["data"]["labels"] = _label_set("auto:spec-done")
    assert dedupe_key(payload, route) == key


def test_status_in_progress_impl_done_without_verify_failed_is_ignored():
    assert (
        route_linear_webhook(
            _issue(
                state="In Progress",
                state_id="p1",
                labels=_label_set("auto:impl-done", "auto:todo-list-done"),
                updated_from={"stateId": "r1"},
            ),
        )
        is None
    )


def test_status_in_progress_verify_failed_routes_implement():
    route = route_linear_webhook(
        _issue(
            state="In Progress",
            state_id="p1",
            labels=_label_set("auto:impl-done", "auto:verify-failed"),
            updated_from={"stateId": "r1"},
        ),
    )
    assert route is not None
    assert route.prompt_file == "linear/in-progress/implement.md"
    assert route.reason == "status→In Progress (verify-failed)"


def test_build_job_payload_includes_linear_event():
    payload = _issue(
        state="Todo",
        labels=_label_set("auto:research-done"),
        updated_from={"stateId": "b1"},
    )
    route = route_linear_webhook(payload)
    assert route is not None
    job = build_job_payload(payload, route)
    assert job["meta"]["linear_event"]["identifier"] == "NOV-X"


def test_job_id_uses_prompt_stem():
    payload = _issue(
        state="Todo",
        labels=_label_set("auto:plan-done"),
        updated_from={"labelIds": []},
    )
    route = route_linear_webhook(payload)
    assert route is not None
    job = build_job_payload(payload, route)
    assert "write-todo-list" in job["id"]
    assert "plan-done" in job["id"]


def test_example_fixtures_route():
    create = json.loads((EXAMPLES / "linear-webhook-issue-create.json").read_text(encoding="utf-8"))
    update = json.loads((EXAMPLES / "linear-webhook-issue-update.json").read_text(encoding="utf-8"))
    assert route_linear_webhook(create).prompt_file == "linear/backlog/create-research.md"
    assert route_linear_webhook(update).prompt_file == "linear/todo/write-spec.md"
