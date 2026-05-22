"""Tests for reading duplicate detection summaries from SAVE JSON."""

import json
from pathlib import Path

from application.utils.duplicate_json import find_latest_duplicate_summary


def _write_duplicate_json(
    save_dir: Path,
    name: str,
    *,
    folder: str,
    total_groups: int,
    unique_in_groups: int,
) -> None:
    payload = {
        "detection_info": {
            "detection_timestamp": "2026-05-22T10:20:32",
            "folder_path": folder,
            "total_groups": total_groups,
            "total_unique_files_in_groups": unique_in_groups,
        },
        "groups": [],
    }
    path = save_dir / name
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_find_latest_duplicate_summary_matches_folder(tmp_path: Path) -> None:
    folder = tmp_path / "novels"
    folder.mkdir()
    _write_duplicate_json(
        tmp_path,
        "duplicate_results_20260101_000000.json",
        folder=str(folder),
        total_groups=10,
        unique_in_groups=25,
    )
    _write_duplicate_json(
        tmp_path,
        "duplicate_results_20260522_120000.json",
        folder=str(folder),
        total_groups=534,
        unique_in_groups=1187,
    )

    summary = find_latest_duplicate_summary(folder, save_dir=tmp_path)
    assert summary is not None
    assert summary.total_groups == 534
    assert summary.duplicate_move_count == 653


def test_find_latest_duplicate_summary_ignores_other_folder(tmp_path: Path) -> None:
    folder = tmp_path / "novels"
    folder.mkdir()
    other = tmp_path / "other"
    other.mkdir()
    _write_duplicate_json(
        tmp_path,
        "duplicate_results_20260522_120000.json",
        folder=str(other),
        total_groups=99,
        unique_in_groups=200,
    )

    assert find_latest_duplicate_summary(folder, save_dir=tmp_path) is None
