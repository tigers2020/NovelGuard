"""Map Linear webhook events to automation prompt files."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any

from automation.linear.linear_ids import (
    has_label_key,
    has_task_list_done,
    issue_in_scope,
    issue_label_ids,
    label_ids_before,
    resolve_state_id,
    resolve_state_name,
    route_debug,
    task_list_done_label_ids,
    task_list_done_reason_suffix,
)

_PROMPT_CREATE = "linear/backlog/create-research.md"
_PROMPT_IMPLEMENT = "linear/in-progress/implement.md"
_PROMPT_VERIFY = "linear/in-review/verify.md"

_SKIP_CREATE_STATES = frozenset({"Done", "Canceled", "Cancelled", "Duplicate"})
_SKIP_UPDATE_STATES = frozenset({"Done", "Canceled", "Cancelled", "Duplicate"})


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


def _state_name(data: dict[str, Any], cfg: dict[str, Any] | None = None) -> str:
    return resolve_state_name(data, cfg)


def _state_id(data: dict[str, Any]) -> str:
    return resolve_state_id(data)


def _issue_identifier(data: dict[str, Any]) -> str:
    return str(data.get("identifier") or data.get("id") or "")


def _issue_url(data: dict[str, Any]) -> str:
    return str(data.get("url") or "")


def _auto_label_slug(label_ids: frozenset[str]) -> str:
    if not label_ids:
        return ""
    slug = "-".join(sorted(label_id[:8] for label_id in label_ids))
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


def resolve_planning_prompt(
    state: str,
    data: dict[str, Any],
    cfg: dict[str, Any] | None,
) -> str | None:
    """Pick one planning prompt from status + routing label UUIDs (priority order)."""
    if state == "Todo":
        if has_label_key(data, cfg, "grill_needs_revision"):
            return "linear/todo/revise-spec.md"
        if has_label_key(data, cfg, "plan_done"):
            return "linear/todo/write-task-list.md"
        if has_label_key(data, cfg, "spec_done") and not has_label_key(data, cfg, "plan_done"):
            return "linear/todo/defer-to-backlog.md"
        if has_label_key(data, cfg, "research_done"):
            return "linear/todo/write-spec.md"
    if state == "Backlog" and has_label_key(data, cfg, "spec_done"):
        return "linear/backlog/grill-plan.md"
    return None


def _route_planning(
    state: str,
    data: dict[str, Any],
    cfg: dict[str, Any] | None,
    *,
    reason: str,
    commit: bool = False,
) -> LinearRoute | None:
    prompt = resolve_planning_prompt(state, data, cfg)
    if prompt is None:
        return None
    return LinearRoute(
        prompt_file=prompt,
        commit=commit,
        verify="none",
        git_prepare=False,
        reason=reason,
    )


def _route_execution_from_labels(
    state: str,
    data: dict[str, Any],
    cfg: dict[str, Any] | None,
    *,
    reason_prefix: str,
) -> LinearRoute | None:
    """Infer implement/verify from phase-done labels — status column optional."""
    if has_label_key(data, cfg, "verify_done"):
        return None

    if has_label_key(data, cfg, "verify_failed"):
        if state == "In Progress":
            return LinearRoute(
                prompt_file=_PROMPT_IMPLEMENT,
                commit=True,
                verify="none",
                git_prepare=False,
                reason=f"{reason_prefix} (verify-failed→implement)",
            )
        return LinearRoute(
            prompt_file=_PROMPT_VERIFY,
            commit=True,
            verify="none",
            git_prepare=False,
            reason=f"{reason_prefix} (verify-failed→verify)",
        )

    if has_label_key(data, cfg, "impl_done"):
        return LinearRoute(
            prompt_file=_PROMPT_VERIFY,
            commit=True,
            verify="none",
            git_prepare=False,
            reason=f"{reason_prefix} (impl-done→verify)",
        )

    if has_task_list_done(data, cfg):
        if state in ("In Progress", "Todo", "Backlog"):
            suffix = task_list_done_reason_suffix(data, cfg)
            return LinearRoute(
                prompt_file=_PROMPT_IMPLEMENT,
                commit=True,
                verify="none",
                git_prepare=False,
                reason=f"{reason_prefix} ({suffix})",
            )

    return None


def _label_only_should_route(state: str, data: dict[str, Any], cfg: dict[str, Any] | None) -> bool:
    if state not in ("Backlog", "Todo"):
        return False
    return resolve_planning_prompt(state, data, cfg) is not None


def _route_label_only_execution(
    payload: dict[str, Any],
    state: str,
    data: dict[str, Any],
    cfg: dict[str, Any] | None,
) -> LinearRoute | None:
    before = label_ids_before(payload)
    current = issue_label_ids(data)

    from automation.linear.linear_ids import DEFAULT_LABEL_IDS

    merged = (cfg or {}).get("linear", {}).get("label_ids") or {}
    impl_done_id = str(merged.get("impl_done") or DEFAULT_LABEL_IDS.get("impl_done") or "")
    blocked_id = str(merged.get("impl_blocked") or DEFAULT_LABEL_IDS.get("impl_blocked") or "")
    done_ids = task_list_done_label_ids(cfg)

    if impl_done_id and impl_done_id in current and impl_done_id not in before:
        if not has_label_key(data, cfg, "verify_done"):
            return LinearRoute(
                prompt_file=_PROMPT_VERIFY,
                commit=True,
                verify="none",
                git_prepare=False,
                reason=f"labels@{state} (impl-done→verify)",
            )

    newly_done = [
        label_id for label_id in done_ids if label_id in current and label_id not in before
    ]
    if (
        newly_done
        and not has_label_key(data, cfg, "impl_done")
        and state in ("In Progress", "Todo", "Backlog")
    ):
        suffix = task_list_done_reason_suffix(data, cfg)
        return LinearRoute(
            prompt_file=_PROMPT_IMPLEMENT,
            commit=True,
            verify="none",
            git_prepare=False,
            reason=f"labels@{state} ({suffix})",
        )

    if state == "In Progress":
        if has_label_key(data, cfg, "verify_failed"):
            return LinearRoute(
                prompt_file=_PROMPT_IMPLEMENT,
                commit=True,
                verify="none",
                git_prepare=False,
                reason="labels@In Progress (verify-failed)",
            )
        if (
            blocked_id
            and blocked_id in before
            and blocked_id not in current
            and not has_label_key(data, cfg, "impl_done")
        ):
            return LinearRoute(
                prompt_file=_PROMPT_IMPLEMENT,
                commit=True,
                verify="none",
                git_prepare=False,
                reason="labels@In Progress (unblocked)",
            )

    if state == "In Review" and has_label_key(data, cfg, "verify_failed"):
        return LinearRoute(
            prompt_file=_PROMPT_VERIFY,
            commit=True,
            verify="none",
            git_prepare=False,
            reason="labels@In Review (verify-failed)",
        )

    return None


def route_linear_webhook(
    payload: dict[str, Any],
    *,
    project_names: set[str] | None = None,
    team_names: set[str] | None = None,
    cfg: dict[str, Any] | None = None,
) -> LinearRoute | None:
    """Return prompt route or None when event should be ignored."""
    if payload.get("type") not in (None, "Issue", "issue"):
        return None

    data = _issue_data(payload)
    if not data:
        return None

    projects = project_names or {"NovelGuard"}
    teams = team_names or {"NoverGuard", "NovelGuard"}
    if not issue_in_scope(data, project_names=projects, team_names=teams, cfg=cfg):
        return None

    action = str(payload.get("action") or "")
    state = _state_name(data, cfg)

    if action == "create":
        if state in _SKIP_CREATE_STATES:
            return None
        if state != "Backlog":
            return None
        return LinearRoute(
            prompt_file=_PROMPT_CREATE,
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

    if state in _SKIP_UPDATE_STATES:
        return None

    if state_changed:
        execution = _route_execution_from_labels(
            state,
            data,
            cfg,
            reason_prefix=f"status→{state}",
        )
        if execution is not None:
            return execution

        if state in ("Backlog", "Todo"):
            return _route_planning(state, data, cfg, reason=f"status→{state}")

        if state == "In Progress":
            return LinearRoute(
                prompt_file=_PROMPT_IMPLEMENT,
                commit=True,
                verify="none",
                git_prepare=False,
                reason="status→In Progress",
            )

        if state == "In Review":
            return LinearRoute(
                prompt_file=_PROMPT_VERIFY,
                commit=True,
                verify="none",
                git_prepare=False,
                reason="status→In Review",
            )

        return None

    if not labels_changed:
        return None

    execution = _route_execution_from_labels(
        state,
        data,
        cfg,
        reason_prefix=f"labels@{state}",
    )
    if execution is not None:
        return execution

    if _label_only_should_route(state, data, cfg):
        return _route_planning(state, data, cfg, reason=f"labels@{state}")

    return _route_label_only_execution(payload, state, data, cfg)


def build_job_payload(
    webhook_payload: dict[str, Any],
    route: LinearRoute,
    *,
    repo_key: str = "novelguard",
    cfg: dict[str, Any] | None = None,
) -> dict[str, Any]:
    data = _issue_data(webhook_payload)
    identifier = _issue_identifier(data)
    state = _state_name(data, cfg)
    state_id = _state_id(data)
    action = str(webhook_payload.get("action") or "update")

    slug_state = state.lower().replace(" ", "-") if state else (state_id[:8] or "unknown")
    prompt_stem = PurePosixPath(route.prompt_file).stem
    label_slug = _auto_label_slug(issue_label_ids(data))
    label_suffix = f"-{label_slug}" if label_slug else ""
    job_id = (
        f"linear-{identifier}-{slug_state}-{prompt_stem}-" f"{state_id[:8] or action}{label_suffix}"
    )

    task = f"{identifier}: {route.reason}"

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
            "linear_event": data,
        },
    }


def dedupe_key(
    webhook_payload: dict[str, Any],
    route: LinearRoute,
    *,
    cfg: dict[str, Any] | None = None,
) -> str:
    data = _issue_data(webhook_payload)
    identifier = _issue_identifier(data)
    state = _state_name(data, cfg) or resolve_state_id(data)
    parts = [identifier, route.prompt_file, state]
    if _state_changed(webhook_payload, data):
        parts.append(f"state:{resolve_state_id(data)}")
    if _labels_changed(webhook_payload):
        parts.append(",".join(sorted(issue_label_ids(data))))
    webhook_id = webhook_payload.get("webhookId")
    if webhook_id:
        parts.append(str(webhook_id))
    return ":".join(parts)


__all__ = [
    "LinearRoute",
    "_labels_changed",
    "_state_changed",
    "build_job_payload",
    "dedupe_key",
    "resolve_planning_prompt",
    "route_debug",
    "route_linear_webhook",
]
