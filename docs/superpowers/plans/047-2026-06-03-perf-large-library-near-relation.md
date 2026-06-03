# Plan 047: Large-library scan performance and duplicate visibility

**Goal:** 7k+ libraries finish deep analysis in minutes (not 10+), and review UI shows exact + near + relation groups.

**Spec alignment:** [028](../specs/028-2026-06-03-infra-scan-streaming-phases-design.md) LOCK-SCAN-7 (background analyze, non-blocking index).

## Tasks

- [x] Bounded near dup: head-only I/O, band index, caps (`duplicate_near.py`, `near_duplicate_detect.py`)
- [x] Stem-hash for title groups 2–32 files (`scan_content_probe.py`)
- [x] Relation detection default on (`app_settings.py`)
- [x] Group count + near filter + review default filter `all`
- [x] Relation before near in post-scan worker
- [x] UI: show 심층 분석 track when `deepAnalysisStatus=running` and pipeline idle
- [x] `pytest tests/test_bridge_contract.py` (149 passed on main, 2026-06-03)
- [x] Commit on `main` (`5ae1bbc`)
- [x] Full gate `python scripts/verify_phase_completion.py` — **7/7 PASS** (2026-06-03)

## Non-goals

- Full `package_windows.py` rebuild in this slice (operator manual per beta-readiness)
- New test files
