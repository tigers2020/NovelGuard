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
- [x] `pytest tests/test_bridge_contract.py` (139 passed)
- [x] Commit slice on `main` (pending user push)

## Non-goals

- Full `verify_phase_completion` gate in this slice (run before PR if needed)
- New test files
