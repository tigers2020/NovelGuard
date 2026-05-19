# Research: Repo-Wide Cleanup

> Status: approved for implementation
> Date: 2026-04-13

## Background

This pass cleans generated artifacts, duplicated tests, and top-level local clutter without
reverting unrelated user edits already present in the worktree.

## Findings

### Generated artifacts

- `src/**/__pycache__/` and `tests/**/__pycache__/` are local bytecode caches and are already
  ignored by `.gitignore`.
- `src/novelguard.egg-info/` is local packaging metadata and is already ignored by `.gitignore`.
- Root file `src (2).zip` is a local export artifact and is ignored by `*.zip`.

### Root clutter

- `google_python_style.vim` is an untracked editor helper file with no references in the repo.
- `logs/` and `SAVE/` are runtime output directories and should stay ignored; this pass will not
  delete user data inside them unless explicitly requested.

### Test tree

- Active default suite is driven by `pyproject.toml` `testpaths` and currently collects 144 tests.
- `tests/unit/test_filename_parser.py` and `tests/unit/domain/test_filename_parser.py` both cover
  the same `domain.services.filename_parser.FilenameParser` behavior.
- The domain-scoped file adds no unique coverage that must remain separate; its useful intent can
  be represented by the canonical top-level unit test module.
- Legacy and excluded trees remain:
  - `tests/domain/`
  - `tests/infra/`
  - `tests/common/`
  - `tests/app/test_bootstrap.py`
  - `tests/app/test_workflows.py`
  - `tests/_archive/`

### Live code checks

- `src/app/factories.py` is still used by `src/gui/workers/duplicate_detection_worker.py` and must
  stay.
- `src/gui/workers/preview_worker.py`, `file_move_worker.py`, `scan_worker.py`,
  `src/gui/view_models/stats_view_model.py`, `src/application/utils/duplicate_json.py`,
  `scan_json.py`, and `debug_logger.py` are all referenced by active UI or test paths and are not
  dead code candidates for this pass.

## Cleanup Targets

- Delete generated directories under `src/` and `tests/`:
  - all `__pycache__/`
  - `src/novelguard.egg-info/`
- Delete root local clutter:
  - `src (2).zip`
  - `google_python_style.vim`
- Delete duplicated active test:
  - `tests/unit/domain/test_filename_parser.py`
- Update guidance docs:
  - `tests/README.md`
  - `tests/fixtures/README.md`
  - `tests/_archive/README.md`

## Rollback Notes

- Deleted generated artifacts can be recreated by running Python tooling locally.
- Deleted zip/editor-helper files are treated as disposable local artifacts.
- If the duplicate test removal is disputed, restore
  `tests/unit/domain/test_filename_parser.py` from Git history.
