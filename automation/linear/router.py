"""Map Linear webhook events to automation prompt files."""

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
    return ""


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


def _auto_label_slug(data: dict[str, Any]) -> str:
    auto = sorted(
        name.removeprefix("auto:")
        for name in _label_names(data)
        if name.startswith("auto:")
    )
    if not auto:
        return ""
    slug = "-".join(auto)
    if len(slug) > 24:
        digest = hashlib.sha256(slug.encode()).hexdigest()[:8]
        return f"h{digest}"
    return slug


def _state_changed(payload: dict[str, Any], data: dict[str, Any]) -> bool:
    updated_from = payload.get("updatedFrom")
    if not isinstance(updated_from, dict):
        return payload.get("action") == "create"

    after_state = data.get("state")
    after_id = ""
    if isinstance(after_state, dict):
        after_id = str(after_state.get("id") or "")
    if not after_id:
        after_id = str(data.get("stateId") or "")

    # Linear production webhooks use updatedFrom.stateId (not nested state object).
    before_id = str(updated_from.get("stateId") or "")
    if before_id and after_id:
        return before_id != after_id

    before = updated_from.get("state")
    if isinstance(before, dict) and isinstance(after_state, dict):
        return before.get("id") != after_state.get("id") or before.get("name") != after_state.get(
            "name"
        )

    if "state" in updated_from:
        return True

    return False


def _labels_changed(payload: dict[str, Any]) -> bool:
    updated_from = payload.get("updatedFrom")
    if not isinstance(updated_from, dict):
        return False
    return "labelIds" in updated_from or "labels" in updated_from


def in_scope(data: dict[str, Any], *, project_names: set[str], team_names: set[str]) -> bool:
    project = _project_name(data)
    team = _team_name(data)
    if project and project in project_names:
        return True
    if team and team in team_names:
        return True
    return False


_SKIP_CREATE_STATES = frozenset({"Done", "Canceled", "Cancelled", "Duplicate"})


def _route_status_router(state: str, *, reason: str) -> LinearRoute:
    return LinearRoute(
        prompt_file="01-linear-status-changed-router.md",
        commit=False,
        verify="none",
        git_prepare=False,
        reason=reason,
    )


def route_linear_webhook(
    payload: dict[str, Any],
    *,
    project_names: set[str] | None = None,
    team_names: set[str] | None = None,
) -> LinearRoute | None:
    """Return prompt route or None when event should be ignored."""
    if payload.get("type") not in (None, "Issue", "issue"):
        return None

    data = _issue_data(payload)
    if not data:
        return None

    projects = project_names or {"NovelGuard"}
    teams = team_names or {"NoverGuard", "NovelGuard"}
    if not in_scope(data, project_names=projects, team_names=teams):
        return None

    action = str(payload.get("action") or "")
    state = _state_name(data)

    if action == "create":
        if state in _SKIP_CREATE_STATES:
            return None
        if state != "Backlog":
            return None
        return LinearRoute(
            prompt_file="00-linear-create-pr-to-spec.md",
            commit=False,
            verify="none",
            git_prepare=False,
            reason="issue.created",
        )

    if action != "update":
        return None

    state_changed = _state_changed(payload, data)
    labels_changed = _labels_changed(payload)
    if not state_changed and not labels_changed:
        return None

    if state_changed:
        if state in ("Backlog", "Todo"):
            return _route_status_router(state, reason=f"status→{state}")

        if state == "In Progress":
            return LinearRoute(
                prompt_file="02-linear-in-progress-implement.md",
                commit=True,
                verify="none",
                git_prepare=False,
                reason="status→In Progress",
            )

        if state == "In Review":
            return LinearRoute(
                prompt_file="03-linear-in-review-verification.md",
                commit=True,
                verify="none",
                git_prepare=False,
                reason="status→In Review",
            )

        return None

    # Label-only update: route 01 at Todo/Backlog; ignore In Progress / In Review.
    if state in ("Backlog", "Todo"):
        return _route_status_router(state, reason=f"labels@{state}")

    return None


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
    prompt_prefix = (route.prompt_file or "job")[:2]
    label_slug = _auto_label_slug(data)
    label_suffix = f"-{label_slug}" if label_slug else ""
    job_id = (
        f"linear-{identifier}-{slug_state}-{prompt_prefix}-{state_id[:8] or action}{label_suffix}"
    )

    title = str(data.get("title") or "")
    task = (
        f"Linear automation: {route.reason} for {identifier} ({state}). "
        f"Issue: {title}. Follow prompt {route.prompt_file} exactly."
    )

    return {
        "id": job_id,
        "repo": repo_key,
        "kind": "linear",
        "task": task,
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
