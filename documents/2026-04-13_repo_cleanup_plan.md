# Plan: Repo-Wide Cleanup

> Status: approved

## Background

The repository contains ignored runtime artifacts, one duplicated active test module, and root
files that do not belong to the project source of truth. The cleanup should reduce noise without
touching unrelated user edits.

## Change Scope

| Layer | File/Module | Change |
|--------|-------------|--------|
| docs | `documents/2026-04-13_repo_cleanup_research.md` | Record evidence and deletion criteria |
| docs | `tests/README.md` | Clarify active suite, excluded legacy suite, and canonical filename parser test |
| docs | `tests/fixtures/README.md` | Clarify fixture role versus active default suite |
| docs | `tests/_archive/README.md` | Clarify archive expectations and exclusion from default runs |
| tests | `tests/unit/domain/test_filename_parser.py` | Remove duplicated active test module |
| runtime | `src/**/__pycache__/`, `tests/**/__pycache__/`, `src/novelguard.egg-info/` | Remove generated artifacts |
| root | `src (2).zip`, `google_python_style.vim` | Remove disposable local clutter |

## Approach

1. Capture findings and exact targets in `documents/`.
2. Remove generated artifacts and disposable root files.
3. Remove the duplicated filename parser test and keep `tests/unit/test_filename_parser.py` as the
   canonical active unit test.
4. Update test documentation so active versus archived/excluded paths are explicit.
5. Run repo verification in standard order and report any failures without reverting unrelated work.

## Impact Analysis

- Existing tests impacted:
  - Duplicate filename parser coverage is consolidated into one active file.
- DTO/port contract changes:
  - None.
- DB migration required:
  - No.
- UI changes:
  - No.

## Verification Plan

- [x] `pytest`
- [x] `ruff check .`
- [x] `mypy src`
- [x] `black --check .`

## Assumptions

- Current dirty tracked files outside this target set belong to ongoing user work and must be left
  intact.
- Generated caches and packaging metadata are safe to remove because they are ignored and
  reproducible.
- Root files removed in this pass are local artifacts, not project deliverables.
