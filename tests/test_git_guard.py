from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
from automation.runners.git_guard import (
    ALLOW_ENV,
    branch_change_error,
    forbidden_git_reason,
    guard_allowed,
    prepend_git_guard_path,
)

ROOT = Path(__file__).resolve().parents[1]
GUARD_SCRIPT = ROOT / "scripts" / "git_guard.py"


@pytest.fixture(autouse=True)
def _clear_allow_env(monkeypatch):
    monkeypatch.delenv(ALLOW_ENV, raising=False)


def test_forbidden_checkout_create():
    assert forbidden_git_reason(["checkout", "-b", "fix/foo"]) == "checkout -b"


def test_forbidden_switch_create():
    assert forbidden_git_reason(["switch", "-c", "fix/foo"]) == "switch -c"


def test_forbidden_branch_create_and_delete():
    assert forbidden_git_reason(["branch", "fix/foo"]) == "branch <name>"
    assert forbidden_git_reason(["branch", "-D", "fix/foo"]) == "branch mutate"


def test_allowed_readonly_git():
    for args in (
        ["status"],
        ["diff"],
        ["add", "file.py"],
        ["commit", "-m", "msg"],
        ["branch", "--show-current"],
        ["checkout", "--", "file.py"],
        ["rev-parse", "--abbrev-ref", "HEAD"],
    ):
        assert forbidden_git_reason(args) is None


def test_allow_env_bypass():
    os.environ[ALLOW_ENV] = "1"
    try:
        assert guard_allowed()
        assert forbidden_git_reason(["checkout", "-b", "x"]) is None
    finally:
        del os.environ[ALLOW_ENV]


def test_branch_change_error():
    assert branch_change_error("main", "main") is None
    err = branch_change_error("ai/job-1", "fix/other")
    assert err is not None
    assert "branch changed" in err


def test_prepend_git_guard_path_puts_bin_first():
    env = prepend_git_guard_path({"PATH": "/usr/bin"})
    first = env["PATH"].split(os.pathsep)[0]
    assert first.endswith(".automation/bin") or first.endswith(".automation\\bin")


def test_git_guard_cli_blocks_create_branch():
    proc = subprocess.run(
        [sys.executable, str(GUARD_SCRIPT), "checkout", "-b", "guard-test-block"],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    assert proc.returncode == 2
    assert "[git-guard] blocked" in proc.stderr


def test_git_guard_cli_allows_status():
    proc = subprocess.run(
        [sys.executable, str(GUARD_SCRIPT), "status", "--short"],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    assert proc.returncode == 0
