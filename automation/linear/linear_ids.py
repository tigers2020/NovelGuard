"""Resolve Linear webhook UUID fields (stateId, teamId, labelIds) for routing."""

from __future__ import annotations

from typing import Any

# NovelGuard / NoverGuard workspace defaults (override in automation/config.yaml).
DEFAULT_STATE_IDS: dict[str, str] = {
    "180fc254-f066-4fad-a425-7ebab180d4c6": "Backlog",
    "49a46ce6-eb18-4377-95ae-b76f655a77b7": "Todo",
    "0be134b7-bc56-4ba6-ba76-6b0a705e2ded": "In Progress",
    "31a91042-9d59-49eb-8821-43ddd92ed76d": "In Review",
    "537a17f3-7fe0-46f0-94d3-89f36f48e98c": "Done",
    "0ea84fa9-26e3-4710-b90a-92566bce60ff": "Canceled",
    "96c4ea2a-3792-49a2-8f5e-2bdd373e3c44": "Duplicate",
}

DEFAULT_TEAM_IDS: frozenset[str] = frozenset({"97047174-6453-4458-b170-a9bf5f7b52e0"})
DEFAULT_PROJECT_IDS: frozenset[str] = frozenset({"20965ebc-3ea7-4787-9310-f15ad9019007"})

# Semantic key → Linear label UUID (routing uses IDs, not display names).
DEFAULT_LABEL_IDS: dict[str, str] = {
    "research_done": "b26a0e92-112f-49dc-bdc1-16628995c020",
    "spec_done": "bffa5b70-6009-4c1c-8f6a-f7fd62e79621",
    "plan_done": "f3424dcd-6d2c-47f9-a8fe-5f4d5b626d27",
    "grill_needs_revision": "6213baed-1cd7-4bb7-acb4-1572e7fbdf36",
    "task_list_done": "972c97e9-1c0d-4a3a-a8ec-04310b6e45eb",
    "todo_list_done": "75d4a692-8214-4592-8f45-f29f93162b45",
    "impl_done": "41269879-fa85-478c-bca6-3329340d8069",
    "verify_done": "65836882-f344-4675-b3a2-552a3fb3c79c",
    "impl_blocked": "21887166-c56e-4a0b-bf66-5f8cca32703b",
}


def _linear_cfg(cfg: dict[str, Any] | None) -> dict[str, Any]:
    return (cfg or {}).get("linear") or {}


def _merged_state_ids(cfg: dict[str, Any] | None) -> dict[str, str]:
    raw = _linear_cfg(cfg).get("state_ids") or {}
    merged = dict(DEFAULT_STATE_IDS)
    if isinstance(raw, dict):
        merged.update({str(k): str(v) for k, v in raw.items() if k and v})
    return merged


def _merged_label_ids(cfg: dict[str, Any] | None) -> dict[str, str]:
    raw = _linear_cfg(cfg).get("label_ids") or {}
    merged = {k: v for k, v in DEFAULT_LABEL_IDS.items() if not v.startswith("00000000")}
    if isinstance(raw, dict):
        for key, value in raw.items():
            if key and value:
                merged[str(key)] = str(value)
    return merged


def _team_ids(cfg: dict[str, Any] | None) -> frozenset[str]:
    raw = _linear_cfg(cfg).get("team_ids")
    if isinstance(raw, list) and raw:
        return frozenset(str(x) for x in raw)
    return DEFAULT_TEAM_IDS


def _project_ids(cfg: dict[str, Any] | None) -> frozenset[str]:
    raw = _linear_cfg(cfg).get("project_ids")
    if isinstance(raw, list) and raw:
        return frozenset(str(x) for x in raw)
    return DEFAULT_PROJECT_IDS


def resolve_state_id(data: dict[str, Any]) -> str:
    state = data.get("state")
    if isinstance(state, dict) and state.get("id"):
        return str(state["id"])
    return str(data.get("stateId") or "")


def resolve_state_name(data: dict[str, Any], cfg: dict[str, Any] | None = None) -> str:
    state = data.get("state")
    if isinstance(state, dict) and state.get("name"):
        return str(state["name"])
    state_id = resolve_state_id(data)
    if state_id:
        name = _merged_state_ids(cfg).get(state_id)
        if name:
            return name
    return ""


def resolve_team_id(data: dict[str, Any]) -> str:
    team = data.get("team")
    if isinstance(team, dict) and team.get("id"):
        return str(team["id"])
    return str(data.get("teamId") or "")


def resolve_project_id(data: dict[str, Any]) -> str:
    project = data.get("project")
    if isinstance(project, dict) and project.get("id"):
        return str(project["id"])
    return str(data.get("projectId") or "")


def issue_in_scope(
    data: dict[str, Any],
    *,
    project_names: set[str],
    team_names: set[str],
    cfg: dict[str, Any] | None = None,
) -> bool:
    project = data.get("project")
    if isinstance(project, dict):
        name = str(project.get("name") or "")
        if name and name in project_names:
            return True
    team = data.get("team")
    if isinstance(team, dict):
        name = str(team.get("name") or "")
        if name and name in team_names:
            return True

    team_id = resolve_team_id(data)
    if team_id and team_id in _team_ids(cfg):
        return True
    project_id = resolve_project_id(data)
    if project_id and project_id in _project_ids(cfg):
        return True
    return False


def issue_label_ids(data: dict[str, Any]) -> frozenset[str]:
    label_ids = data.get("labelIds")
    if isinstance(label_ids, list):
        return frozenset(str(label_id) for label_id in label_ids if label_id)
    labels = data.get("labels")
    if isinstance(labels, list):
        out: set[str] = set()
        for item in labels:
            if isinstance(item, dict) and item.get("id"):
                out.add(str(item["id"]))
        if out:
            return frozenset(out)
    return frozenset()


def label_ids_before(payload: dict[str, Any]) -> frozenset[str]:
    updated_from = payload.get("updatedFrom")
    if not isinstance(updated_from, dict):
        return frozenset()
    before_ids = updated_from.get("labelIds")
    if isinstance(before_ids, list):
        return frozenset(str(label_id) for label_id in before_ids if label_id)
    return frozenset()


def has_label_key(data: dict[str, Any], cfg: dict[str, Any] | None, key: str) -> bool:
    label_uuid = _merged_label_ids(cfg).get(key)
    if not label_uuid:
        return False
    return label_uuid in issue_label_ids(data)


_TASK_LIST_DONE_KEYS = ("task_list_done", "todo_list_done")


def task_list_done_label_ids(cfg: dict[str, Any] | None = None) -> frozenset[str]:
    merged = _merged_label_ids(cfg)
    ids: set[str] = set()
    for key in _TASK_LIST_DONE_KEYS:
        value = merged.get(key)
        if value:
            ids.add(str(value))
    return frozenset(ids)


def has_task_list_done(data: dict[str, Any], cfg: dict[str, Any] | None = None) -> bool:
    return bool(task_list_done_label_ids(cfg) & issue_label_ids(data))


def task_list_done_reason_suffix(data: dict[str, Any], cfg: dict[str, Any] | None) -> str:
    if has_label_key(data, cfg, "task_list_done"):
        return "task-list-done→implement"
    return "todo-list-done→implement"


def route_debug(data: dict[str, Any], cfg: dict[str, Any] | None = None) -> str:
    return (
        f"stateId={resolve_state_id(data)} "
        f"state={resolve_state_name(data, cfg)!r} "
        f"teamId={resolve_team_id(data)} "
        f"labelIds={sorted(issue_label_ids(data))}"
    )
