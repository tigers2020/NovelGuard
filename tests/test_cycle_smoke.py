"""CI-safe automation cycle smoke (mock compressor)."""

from __future__ import annotations

from automation.runners.cycle_smoke import load_manifest, run_case, run_manifest


def test_load_manifest_has_twelve_cases():
    manifest = load_manifest()
    cases = [c for g in manifest["groups"] for c in g["cases"]]
    assert len(cases) == 12


def test_A_combined_routes_impl_done_over_status():
    manifest = load_manifest()
    case = next(
        c
        for g in manifest["groups"]
        for c in g["cases"]
        if c["id"] == "A-combined-in-review-impl-done"
    )
    result = run_case(case, live_compressor=False, render=False)
    assert result.ok, result.errors
    assert result.prompt_file == "linear/in-review/verify.md"
    assert result.route_reason and "impl-done→verify" in result.route_reason


def test_full_manifest_mock_compressor():
    results = run_manifest(live_compressor=False, stop_on_fail=False)
    failed = [r for r in results if not r.ok]
    assert len(results) == 12
    assert not failed, failed[0].errors if failed else []
