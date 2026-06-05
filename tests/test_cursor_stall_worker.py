"""Tests for cursor stall detection helpers."""

from automation.runners.cursor_stall import CursorOutputTracker, cursor_stall_config


def test_cursor_stall_config_defaults():
    stall, retries, poll = cursor_stall_config({"cursor": {}})
    assert stall == 300.0
    assert retries == 1
    assert poll == 5.0


def test_output_tracker_idle_seconds():
    t0 = 1000.0
    tracker = CursorOutputTracker(now=t0)
    assert tracker.idle_seconds(now=t0 + 10) == 10.0
