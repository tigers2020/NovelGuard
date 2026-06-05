"""Prompt-pipeline smoke: route → payload → render (no queue/cursor)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from automation.linear.router import build_job_payload, route_linear_webhook
from automation.runners.config import load_config, repo_root

_MANIFEST = repo_root() / "automation" / "examples" / "cycle-smoke" / "manifest.json"
_FIXTURES = _MANIFEST.parent

_WORKER_PLACEHOLDERS = (
    "{{TASK}}",
    "{{JOB_ID}}",
    "{{BRANCH}}",
    "{{ISSUE_IDENTIFIER}}",
    "{{ISSUE_URL}}",
    "{{ROUTE_REASON}}",
    "{{LINEAR_STATE}}",
    "{{LINEAR_EVENT}}",
    "{{CONTEXT_MEMORY_JSON}}",
    "{{NEXT_PROMPT}}",
)

_MOCK_MEMORY: dict[str, Any] = {
    "goal": "NOV-SMOKE cycle smoke",
    "current_phase": "smoke",
    "locked_decisions": ["[LOCK] smoke fixture"],
    "must_keep_context": [],
    "changed_files": [],
    "relevant_tests": [],
    "risks": [],
    "unknowns": [],
    "discarded_noise": [],
    "next_prompt": "Continue smoke case.",
}


@dataclass
class CaseResult:
    case_id: str
    group_id: str
    ok: bool
    prompt_file: str | None = None
    route_reason: str | None = None
    rendered_chars: int = 0
    errors: list[str] = field(default_factory=list)


def load_manifest(path: Path | None = None) -> dict[str, Any]:
    p = path or _MANIFEST
    return json.loads(p.read_text(encoding="utf-8"))


def _load_fixture(name: str) -> dict[str, Any]:
    return json.loads((_FIXTURES / name).read_text(encoding="utf-8"))


def _expects_ignore(case: dict[str, Any]) -> bool:
    return "expect_prompt" not in case


def _validate_route(case: dict[str, Any], route) -> list[str]:
    errors: list[str] = []
    if _expects_ignore(case):
        if route is not None:
            errors.append(f"expected no route, got {route.prompt_file}")
        return errors
    if route is None:
        errors.append("expected route, got None")
        return errors
    expect_prompt = case.get("expect_prompt")
    if expect_prompt and route.prompt_file != expect_prompt:
        errors.append(f"prompt_file {route.prompt_file!r} != {expect_prompt!r}")
    substr = case.get("expect_reason_contains")
    if substr and substr not in route.reason:
        errors.append(f"route.reason {route.reason!r} missing {substr!r}")
    return errors


def _validate_render(
    case: dict[str, Any],
    cfg: dict[str, Any],
    webhook_payload: dict[str, Any],
    route,
    *,
    live_compressor: bool,
) -> list[str]:
    from unittest.mock import patch

    from automation.runners.job_worker import render_prompt

    errors: list[str] = []
    job = build_job_payload(webhook_payload, route, cfg=cfg)
    branch = f"ai/cycle-smoke-{case['id']}"

    if live_compressor:
        rendered = render_prompt(cfg, job, branch)
    else:
        with patch(
            "automation.runners.job_worker.compress_job_context",
            return_value={"memory": dict(_MOCK_MEMORY), "cached": False},
        ):
            rendered = render_prompt(cfg, job, branch)

    for ph in _WORKER_PLACEHOLDERS:
        if ph in rendered:
            errors.append(f"unresolved placeholder {ph}")

    if "@docs/agents/runner-brief.md" in rendered and "runner-brief-compact" not in rendered:
        errors.append("full runner-brief.md referenced")

    if "runner-brief-compact" not in rendered:
        errors.append("runner-brief-compact not referenced")

    mem_match = re.search(
        r"## Context memory\s*\n(\{.*?\n\})",
        rendered,
        re.DOTALL,
    )
    if not mem_match:
        errors.append("missing Context memory JSON block")
    else:
        try:
            json.loads(mem_match.group(1))
        except json.JSONDecodeError as exc:
            errors.append(f"invalid context memory JSON: {exc}")

    manifest = load_manifest()
    max_chars = int(case.get("max_chars") or manifest.get("default_max_chars") or 24000)
    if len(rendered) > max_chars:
        errors.append(f"rendered length {len(rendered)} > {max_chars}")

    return errors


def run_case(
    case: dict[str, Any],
    *,
    group_id: str = "",
    cfg: dict[str, Any] | None = None,
    live_compressor: bool = False,
    render: bool = True,
) -> CaseResult:
    cfg = cfg or load_config()
    case_id = str(case["id"])
    payload = _load_fixture(str(case["fixture"]))
    route = route_linear_webhook(payload, cfg=cfg)
    errors = _validate_route(case, route)
    prompt_file = route.prompt_file if route else None
    route_reason = route.reason if route else None
    rendered_chars = 0

    if render and route is not None and not errors:
        render_errors = _validate_render(
            case,
            cfg,
            payload,
            route,
            live_compressor=live_compressor,
        )
        errors.extend(render_errors)
        if not render_errors:
            from unittest.mock import patch

            from automation.runners.job_worker import render_prompt

            job = build_job_payload(payload, route, cfg=cfg)
            branch = f"ai/cycle-smoke-{case_id}"
            if live_compressor:
                rendered_chars = len(render_prompt(cfg, job, branch))
            else:
                with patch(
                    "automation.runners.job_worker.compress_job_context",
                    return_value={"memory": dict(_MOCK_MEMORY), "cached": False},
                ):
                    rendered_chars = len(render_prompt(cfg, job, branch))

    return CaseResult(
        case_id=case_id,
        group_id=group_id,
        ok=not errors,
        prompt_file=prompt_file,
        route_reason=route_reason,
        rendered_chars=rendered_chars,
        errors=errors,
    )


def run_manifest(
    *,
    group: str | None = None,
    live_compressor: bool = False,
    stop_on_fail: bool = True,
    cfg: dict[str, Any] | None = None,
) -> list[CaseResult]:
    manifest = load_manifest()
    cfg = cfg or load_config()
    results: list[CaseResult] = []
    for grp in manifest["groups"]:
        gid = str(grp["id"])
        if group and gid != group:
            continue
        for case in grp["cases"]:
            result = run_case(
                case,
                group_id=gid,
                cfg=cfg,
                live_compressor=live_compressor,
                render=True,
            )
            results.append(result)
            if not result.ok and stop_on_fail:
                return results
    return results
