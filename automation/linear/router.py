"""Map Linear webhook events to compact automation prompt files."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class LinearRoute:
    prompt_file: str
    commit: bool
    verify: str
    git_prepare: bool
    reason: str


@dataclass(frozen=True)
class LinearEventRoute:
    event: dict[str, Any]
    route: LinearRoute


def _issue_data(payload: dict[str, Any]) -> dict[str, Any]:
    data = payload.get("data")
    return data if isinstance(data, dict) else {}


def _project_name(data: dict[str, Any]) -> str:
    project = data.get("project")
    if isinstance(project, dict):
        return str(project.get("name") or "")
    return str(project or "")


def _team_name(data: dict[str, Any]) -> str:
    team = data.get("team")
    if isinstance(team, dict):
        return str(team.get("name") or "")
    return str(team or "")


def _state_name(data: dict[str, Any]) -> str:
    state = data.get("state")
    if isinstance(state, dict):
        return str(state.get("name") or "")
    return str(state or "")


def _state_id(data: dict[str, Any]) -> str:
    state = data.get("state")
    if isinstance(state, dict):
        return str(state.get("id") or "")
    return str(data.get("stateId") or "")


def _issue_identifier(data: dict[str, Any]) -> str:
    return str(data.get("identifier") or data.get("id") or "")


def _issue_url(data: dict[str, Any]) -> str:
    return str(data.get("url") or "")


def _label_names(data: dict[str, Any]) -> frozenset[str]:
    labels = data.get("labels")
    if not isinstance(labels, list):
        return frozenset()
    out: set[str] = set()
    for item in labels:
        if isinstance(item, dict):
            name = item.get("name")
            if name:
                out.add(str(name))
        elif item:
            out.add(str(item))
    return frozenset(out)


def _label_ids(data: dict[str, Any]) -> set[str]:
    raw = data.get("labelIds")
    if isinstance(raw, list):
        return {str(label_id) for label_id in raw if label_id}
    labels = data.get("labels")
    if not isinstance(labels, list):
        return set()
    return {
        str(item["id"])
        for item in labels
        if isinstance(item, dict) and item.get("id")
    }


def _labels_from_updated_from(updated_from: dict[str, Any]) -> set[str]:
    labels = updated_from.get("labels")
    if not isinstance(labels, list):
        return set()
    out: set[str] = set()
    for item in labels:
        if isinstance(item, dict):
            name = item.get("name")
            if name:
                out.add(str(name))
        elif item:
            out.add(str(item))
    return out


def resolve_label_names(
    *,
    data: dict[str, Any],
    added_ids: set[str],
    removed_ids: set[str],
) -> tuple[set[str], set[str]]:
    labels = data.get("labels")
    if not isinstance(labels, list):
        return set(), set()

    by_id: dict[str, str] = {}
    nameless_ids: set[str] = set()
    for item in labels:
        if not isinstance(item, dict):
            continue
        label_id = item.get("id")
        name = item.get("name")
        if not label_id:
            continue
        if name:
            by_id[str(label_id)] = str(name)
        else:
            nameless_ids.add(str(label_id))

    added_labels = {by_id[label_id] for label_id in added_ids if label_id in by_id}
    removed_labels = {by_id[label_id] for label_id in removed_ids if label_id in by_id}
    _ = nameless_ids
    return added_labels, removed_labels


def classify_linear_events(payload: dict[str, Any]) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    action = payload.get("action")
    data = _issue_data(payload)
    updated_from = payload.get("updatedFrom")
    if not isinstance(updated_from, dict):
        updated_from = {}

    if action == "create":
        return [{"trigger": "linear.issue.created"}]
    if action != "update":
        return events

    if "stateId" in updated_from or "state" in updated_from:
        events.append({"trigger": "linear.statusChanged", "state": _state_name(data)})

    added_labels: set[str] = set()
    if "labelIds" in updated_from:
        old_ids = {str(label_id) for label_id in updated_from.get("labelIds") or []}
        new_ids = _label_ids(data)
        added_ids = new_ids - old_ids
        added_labels, _ = resolve_label_names(
            data=data,
            added_ids=added_ids,
            removed_ids=old_ids - new_ids,
        )
        if not old_ids and not new_ids:
            added_labels = set(_label_names(data))
    elif "labels" in updated_from:
        added_labels = set(_label_names(data)) - _labels_from_updated_from(updated_from)

    for label in sorted(label for label in added_labels if label.startswith("auto:")):
        events.append({"trigger": "linear.labelAdded", "label": label})

    return events


def _auto_label_slug(data: dict[str, Any]) -> str:
    auto = sorted(
        name.removeprefix("auto:") for name in _label_names(data) if name.startswith("auto:")
    )
    if not auto:
        return ""
    slug = "-".join(auto)
    if len(slug) > 24:
        digest = hashlib.sha256(slug.encode()).hexdigest()[:8]
        return f"h{digest}"
    return slug


def in_scope(data: dict[str, Any], *, project_names: set[str], team_names: set[str]) -> bool:
    project = _project_name(data)
    team = _team_name(data)
    return bool((project and project in project_names) or (team and team in team_names))


_SKIP_CREATE_STATES = frozenset({"Done", "Canceled", "Cancelled", "Duplicate"})


def _route(
    prompt_file: str,
    *,
    reason: str,
    commit: bool = False,
    verify: str = "none",
    git_prepare: bool = False,
) -> LinearRoute:
    return LinearRoute(
        prompt_file=prompt_file,
        commit=commit,
        verify=verify,
        git_prepare=git_prepare,
        reason=reason,
    )


def _route_phase(state: str, labels: frozenset[str]) -> LinearRoute | None:
    if state == "Todo" and "auto:research-done" in labels:
        return _route("01a-linear-spec.md", reason="Todo+auto:research-done→spec")
    if state == "Backlog" and "auto:spec-done" in labels:
        return _route("01b-linear-grill-plan.md", reason="Backlog+auto:spec-done→plan")
    if state == "Todo" and "auto:grill-needs-revision" in labels:
        return _route(
            "01c-linear-spec-revise.md",
            reason="Todo+auto:grill-needs-revision→spec-revision",
        )
    if state == "Todo" and "auto:plan-done" in labels:
        return _route("01d-linear-todo-list.md", reason="Todo+auto:plan-done→todo-list")
    return None


def _route_event(event: dict[str, Any], *, data: dict[str, Any]) -> LinearRoute | None:
    state = _state_name(data)
    labels = _label_names(data)
    trigger = str(event.get("trigger") or "")

    if trigger == "linear.issue.created":
        if state in _SKIP_CREATE_STATES or state != "Backlog":
            return None
        return _route("00-linear-create-pr-to-spec.md", reason="issue.created")

    if trigger == "linear.statusChanged":
        if state == "In Progress":
            return _route(
                "02-linear-in-progress-implement.md",
                reason="status→In Progress",
                commit=True,
            )
        if state == "In Review":
            return _route(
                "03-linear-in-review-verification.md",
                reason="status→In Review",
                commit=True,
            )
        return _route_phase(state, labels)

    if trigger != "linear.labelAdded":
        return None

    label = str(event.get("label") or "")
    if not label.startswith("auto:"):
        return None
    if label == "auto:todo-list-done" and state == "In Progress":
        return _route(
            "02-linear-in-progress-implement.md",
            reason="label→auto:todo-list-done",
            commit=True,
        )
    if label == "auto:impl-done" and state == "In Review":
        return _route(
            "03-linear-in-review-verification.md",
            reason="label→auto:impl-done",
            commit=True,
        )
    return _route_phase(state, labels)


def route_linear_webhook_events(
    payload: dict[str, Any],
    *,
    project_names: set[str] | None = None,
    team_names: set[str] | None = None,
) -> list[LinearEventRoute]:
    if payload.get("type") not in (None, "Issue", "issue"):
        return []

    data = _issue_data(payload)
    if not data:
        return []

    projects = project_names or {"NovelGuard"}
    teams = team_names or {"NoverGuard", "NovelGuard"}
    if not in_scope(data, project_names=projects, team_names=teams):
        return []

    identifier = _issue_identifier(data)
    state = _state_name(data)
    seen: set[tuple[str, str, str]] = set()
    routes: list[LinearEventRoute] = []
    for event in classify_linear_events(payload):
        route = _route_event(event, data=data)
        if route is None:
            continue
        key = (identifier, state, route.prompt_file)
        if key in seen:
            continue
        seen.add(key)
        routes.append(LinearEventRoute(event=event, route=route))
    return routes


def route_linear_webhook(
    payload: dict[str, Any],
    *,
    project_names: set[str] | None = None,
    team_names: set[str] | None = None,
) -> LinearRoute | None:
    event_routes = route_linear_webhook_events(
        payload,
        project_names=project_names,
        team_names=team_names,
    )
    if not event_routes:
        return None
    return event_routes[0].route


def build_job_payload(
    webhook_payload: dict[str, Any],
    route: LinearRoute,
    *,
    repo_key: str = "novelguard",
) -> dict[str, Any]:
    data = _issue_data(webhook_payload)
    identifier = _issue_identifier(data)
    state = _state_name(data)
    state_id = _state_id(data)
    action = str(webhook_payload.get("action") or "update")

    slug_state = state.lower().replace(" ", "-") if state else "unknown"
    prompt_prefix = (route.prompt_file or "job")[:3].removesuffix("-")
    label_slug = _auto_label_slug(data)
    label_suffix = f"-{label_slug}" if label_slug else ""
    job_id = (
        f"linear-{identifier}-{slug_state}-{prompt_prefix}-{state_id[:8] or action}"
        f"{label_suffix}"
    )

    return {
        "id": job_id,
        "repo": repo_key,
        "kind": "linear",
        "task": f"{identifier} · {state} · {route.reason}",
        "prompt_file": route.prompt_file,
        "issue_identifier": identifier,
        "issue_url": _issue_url(data),
        "linear_action": action,
        "linear_state": state,
        "commit": route.commit,
        "merge_approved": False,
        "safety_level": 3 if route.commit else 2,
        "verify": route.verify,
        "git_prepare": route.git_prepare,
        "source": "linear:webhook",
        "meta": {
            "route_reason": route.reason,
            "webhook_type": webhook_payload.get("type"),
        },
    }


def dedupe_key(webhook_payload: dict[str, Any], route: LinearRoute) -> str:
    data = _issue_data(webhook_payload)
    identifier = _issue_identifier(data)
    state = _state_name(data)
    labels = ",".join(sorted(_label_names(data)))
    return f"{identifier}:{route.prompt_file}:{state}:{labels}"
