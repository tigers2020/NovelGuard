"""NOV-37: synthetic 7k fixture generator + large-library loading smoke gate."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest
from large_library_gate import (
    SMOKE_SCRIPT as SMOKE,
)
from large_library_gate import (
    assert_slo_report,
    require_full_fixture,
)

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "packaging" / "fixtures" / "library-large" / "manifest.json"
GENERATOR = ROOT / "scripts" / "generate_large_library_fixture.py"


def _load_generator_module():
    spec = importlib.util.spec_from_file_location("generate_large_library_fixture", GENERATOR)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _load_smoke_module():
    spec = importlib.util.spec_from_file_location("large_library_loading_smoke", SMOKE)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _write_mini_library(folder: Path, *, count: int = 12) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    for i in range(count):
        (folder / f"mini-{i:03d}.txt").write_text(f"mini body {i}\n", encoding="utf-8")


def test_manifest_fields() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert manifest["expected_file_count"] == 7200
    assert manifest["expected_exact_duplicate_pairs"] == 30
    assert manifest["expected_stem_clusters"] == 10
    assert manifest["generator_seed"] == 20260605


def test_generator_produces_expected_structure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    mod = _load_generator_module()
    monkeypatch.setattr(mod, "OUT_DIR", tmp_path / "generated")
    out = mod.generate(20260605, 120)
    assert out.exists()
    txt_files = list(out.rglob("*.txt"))
    assert len(txt_files) >= 115
    dup_a = out / "dup-00-a.txt"
    dup_b = out / "dup-00-b.txt"
    assert dup_a.is_file() and dup_b.is_file()
    assert dup_a.read_text(encoding="utf-8") == dup_b.read_text(encoding="utf-8")


@pytest.mark.large_library
def test_generator_main_exit_zero() -> None:
    result = subprocess.run(
        [sys.executable, str(GENERATOR)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=300,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout.strip().splitlines()[-1])
    assert payload["file_count"] >= 7150


def test_smoke_emits_json_timing_report(tmp_path: Path) -> None:
    fixture = tmp_path / "library"
    _write_mini_library(fixture)
    result = subprocess.run(
        [sys.executable, str(SMOKE), "--folder", str(fixture), "--skip-generate"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=300,
    )
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["status"] == "PASS"
    assert "timings" in report
    assert "query_file_rows_p95_ms" in report["timings"]
    assert "query_review_rows_first_ms" in report["timings"]
    assert "index_ready_ms" in report["timings"]


def test_smoke_folder_override(tmp_path: Path) -> None:
    custom = tmp_path / "custom-folder"
    _write_mini_library(custom, count=8)
    result = subprocess.run(
        [sys.executable, str(SMOKE), "--folder", str(custom), "--skip-generate"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=300,
    )
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["status"] == "PASS"


def test_smoke_slo_fail_exits_nonzero(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    fixture = tmp_path / "slo-library"
    _write_mini_library(fixture, count=6)
    mod = _load_smoke_module()

    def slow_timed(call):
        return call(), 99999.0

    monkeypatch.setattr(mod, "_timed", slow_timed)
    monkeypatch.setattr(
        sys,
        "argv",
        ["large_library_loading_smoke.py", "--folder", str(fixture), "--skip-generate"],
    )
    assert mod.main() == 1


@pytest.mark.large_library
def test_large_library_full_slo_gate() -> None:
    fixture = require_full_fixture()
    result = subprocess.run(
        [sys.executable, str(SMOKE), "--folder", str(fixture), "--skip-generate"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=900,
    )
    if result.returncode != 0 and not result.stdout.strip():
        pytest.fail(
            "large-library SLO gate subprocess failed before JSON report:\n"
            f"exit={result.returncode}\n"
            f"stderr:\n{result.stderr}"
        )
    report = json.loads(result.stdout)
    assert_slo_report(report)
