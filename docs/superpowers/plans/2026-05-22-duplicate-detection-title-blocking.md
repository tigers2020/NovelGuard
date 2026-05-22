# Duplicate Detection Title Blocking Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Unify filename-variant series keys so updated anthology pairs (same `range_start`, different `range_end`) reach version/containment relation detection without enabling Near or full-library hashing.

**Architecture:** Strengthen `FilenameParser._normalize_series_title` (NFKC + punctuation stripping) so `series_title_norm` is blocking-safe; keep `BlockingService` and `ContainmentDetector` logic; add optional relation-stage cap for very large blocking groups; cover user golden filenames with unit + stage tests.

**Tech Stack:** Python 3.12+, domain/application layers, pytest / ruff / mypy / black via `scripts/verify_phase_completion.py`.

**Spec:** [../specs/2026-05-22-duplicate-detection-title-blocking-design.md](../specs/2026-05-22-duplicate-detection-title-blocking-design.md)

---

## File map (create / modify)

| Action | Path |
|--------|------|
| Modify | `src/domain/services/filename_parser.py` |
| Modify | `src/domain/value_objects/filename_parse_result.py` (docstring only) |
| Modify | `src/domain/value_objects/detection_config.py` |
| Modify | `src/application/use_cases/duplicate_detection/stages/relation_detection_stage.py` |
| Modify | `tests/unit/test_filename_parser.py` |
| Create | `tests/unit/domain/test_filename_parser_title_variants.py` |
| Modify | `tests/unit/domain/test_blocking_service.py` |
| Create | `tests/unit/domain/test_version_updated_anthology.py` |
| Modify | `docs/superpowers/README.md` |

---

### Task 1: Golden normalization tests (TDD)

**Files:**
- Create: `tests/unit/domain/test_filename_parser_title_variants.py`

- [ ] **Step 1: Write failing tests**

Create `tests/unit/domain/test_filename_parser_title_variants.py`:

```python
"""Real-world title variants → unified series_title_norm (blocking key)."""

from pathlib import Path

import pytest

from domain.services.filename_parser import FilenameParser


@pytest.fixture
def parser() -> FilenameParser:
    return FilenameParser()


class TestTitleVariantsSameNorm:
    def test_ampersand_vs_spaces_dungeon_commander(self, parser: FilenameParser) -> None:
        a = parser.parse(Path("던전 & 커맨더 1-2194.txt"))
        b = parser.parse(Path("던전  커맨더 1-2168.txt"))
        assert a.series_title_norm == b.series_title_norm
        assert a.is_same_series(b)
        assert a.range_start == 1 and b.range_start == 1
        assert a.range_end == 2194 and b.range_end == 2168

    def test_fullwidth_exclamation_and_author_tag(self, parser: FilenameParser) -> None:
        plain = parser.parse(Path("너네 스킬 다 내꺼 1-1308.txt"))
        variant = parser.parse(Path("너네 스킬 다 내꺼！ 1-1310@김단풍 (1).txt"))
        assert plain.series_title_norm == variant.series_title_norm
        assert plain.is_same_series(variant)
        assert plain.range_end == 1308
        assert variant.range_end == 1310

    def test_duplicate_plain_titles_identical_norm(self, parser: FilenameParser) -> None:
        a = parser.parse(Path("너네 스킬 다 내꺼 1-1308.txt"))
        b = parser.parse(Path("너네 스킬 다 내꺼 1-1308.txt"))
        assert a.series_title_norm == b.series_title_norm
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/domain/test_filename_parser_title_variants.py -v`  
Expected: FAIL — `a.series_title_norm != b.series_title_norm` for ampersand or fullwidth cases.

- [ ] **Step 3: Commit test only (optional)**

```bash
git add tests/unit/domain/test_filename_parser_title_variants.py
git commit -m "[tests] add title variant golden cases for blocking key"
```

---

### Task 2: Implement normalization

**Files:**
- Modify: `src/domain/services/filename_parser.py` (`_normalize_series_title`)
- Modify: `src/domain/value_objects/filename_parse_result.py` (docstring for `series_title_norm`)

- [ ] **Step 1: Add imports and punctuation pattern at top of `filename_parser.py`**

After existing `import re`, add:

```python
import unicodedata

# Stripped from blocking key (after NFKC). Space-collapsed later.
_TITLE_PUNCT_PATTERN = re.compile(
    r"[&!?.,·…:;|/\\~`\"'+\-=\*#]+"
)
```

- [ ] **Step 2: Replace `_normalize_series_title` body**

```python
def _normalize_series_title(self, title: str) -> str:
    """작품명 정규화 (blocking / is_same_series key)."""
    normalized = unicodedata.normalize("NFKC", title)
    normalized = re.sub(r"[\(\[][^\)\]]*[\)\]]", "", normalized)
    normalized = re.sub(r"@[^\s]+", "", normalized)
    tag_words_pattern = re.compile(
        r"(완결|완전판|완본|완|完|후기|에필로그|에필|epilogue|afterword|complete|finished|end)",
        re.IGNORECASE,
    )
    normalized = tag_words_pattern.sub("", normalized)
    normalized = _TITLE_PUNCT_PATTERN.sub(" ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    normalized = normalized.lower()
    if len(normalized) < 2:
        return title.strip().lower()
    return normalized
```

- [ ] **Step 3: Update `FilenameParseResult.series_title_norm` docstring**

Note: blocking-oriented; strips punctuation and NFKC-unifies fullwidth characters.

- [ ] **Step 4: Run variant tests**

Run: `pytest tests/unit/domain/test_filename_parser_title_variants.py -v`  
Expected: PASS

- [ ] **Step 5: Run full filename parser suite**

Run: `pytest tests/unit/test_filename_parser.py -v`  
Expected: PASS (update assertions if any norm strings changed — e.g. titles with `&`).

- [ ] **Step 6: Commit**

```bash
git add src/domain/services/filename_parser.py src/domain/value_objects/filename_parse_result.py tests/unit/domain/test_filename_parser_title_variants.py tests/unit/test_filename_parser.py
git commit -m "[domain] unify series_title_norm for filename variants"
```

---

### Task 3: Blocking groups merge variants

**Files:**
- Modify: `tests/unit/domain/test_blocking_service.py`

- [ ] **Step 1: Write failing integration-style blocking test**

Append to `tests/unit/domain/test_blocking_service.py`:

```python
def test_title_variants_share_blocking_group(service: BlockingService) -> None:
    """던전 & / 던전  spacing variants → one BlockingGroup for version pairing."""
    parser = FilenameParser()
    files = [
        (
            _entry(1, "던전 & 커맨더 1-2194.txt"),
            parser.parse(Path("던전 & 커맨더 1-2194.txt")),
        ),
        (
            _entry(2, "던전  커맨더 1-2168.txt"),
            parser.parse(Path("던전  커맨더 1-2168.txt")),
        ),
    ]
    groups = service.create_blocking_groups(files)
    assert len(groups) == 1
    assert set(groups[0].file_ids) == {1, 2}
```

- [ ] **Step 2: Run test**

Run: `pytest tests/unit/domain/test_blocking_service.py::test_title_variants_share_blocking_group -v`  
Expected: PASS after Task 2 (FAIL before Task 2).

- [ ] **Step 3: Commit**

```bash
git add tests/unit/domain/test_blocking_service.py
git commit -m "[tests] blocking merges punctuation title variants"
```

---

### Task 4: Version detection for updated anthologies

**Files:**
- Create: `tests/unit/domain/test_version_updated_anthology.py`

- [ ] **Step 1: Write version relation tests**

Create `tests/unit/domain/test_version_updated_anthology.py`:

```python
"""Updated anthology: same range_start, different range_end → VersionRelation."""

from datetime import datetime
from pathlib import Path

from domain.entities.file_entry import FileEntry
from domain.services.containment_detector import ContainmentDetector
from domain.services.filename_parser import FilenameParser


def _file(file_id: int, path: str, size: int = 10_000) -> FileEntry:
    return FileEntry(
        path=Path(path),
        size=size,
        mtime=datetime(2025, 6, 1),
        extension=".txt",
        file_id=file_id,
    )


def test_version_dungeon_commander_newer_end() -> None:
    parser = FilenameParser()
    det = ContainmentDetector()
    a = _file(1, "던전 & 커맨더 1-2194.txt", size=20_000)
    b = _file(2, "던전  커맨더 1-2168.txt", size=18_000)
    pa = parser.parse(a.path)
    pb = parser.parse(b.path)
    rel = det.detect_version(a, pa, b, pb)
    assert rel is not None
    assert rel.newer_file_id == 1
    assert rel.older_file_id == 2
    assert pa.range_end == 2194
    assert pb.range_end == 2168


def test_version_skill_title_fullwidth_punctuation() -> None:
    parser = FilenameParser()
    det = ContainmentDetector()
    older = _file(1, "너네 스킬 다 내꺼 1-1308.txt", size=9_000)
    newer = _file(2, "너네 스킬 다 내꺼！ 1-1310@김단풍 (1).txt", size=9_500)
    p_old = parser.parse(older.path)
    p_new = parser.parse(newer.path)
    rel = det.detect_version(older, p_old, newer, p_new)
    assert rel is not None
    assert rel.newer_file_id == 2
    assert rel.older_file_id == 1
```

- [ ] **Step 2: Run tests**

Run: `pytest tests/unit/domain/test_version_updated_anthology.py -v`  
Expected: PASS after Task 2.

- [ ] **Step 3: Commit**

```bash
git add tests/unit/domain/test_version_updated_anthology.py
git commit -m "[tests] version relation for updated anthology filenames"
```

---

### Task 5: Relation stage large-group guard

**Files:**
- Modify: `src/domain/value_objects/detection_config.py`
- Modify: `src/application/use_cases/duplicate_detection/stages/relation_detection_stage.py`

- [ ] **Step 1: Add constant**

In `detection_config.py`:

```python
MAX_FILES_PER_BLOCKING_GROUP_FOR_VERSION_PAIRS: Final[int] = 500
"""Version 쌍 비교 상한. 초과 시 버킷별 비교만 수행하고 경고 로그."""
```

- [ ] **Step 2: Guard in `_compute_version_groups`**

At start of `_compute_version_groups`, after building `by_range_start`, if `len(file_ids_list) > DetectionDefaults.MAX_FILES_PER_BLOCKING_GROUP_FOR_VERSION_PAIRS`:

- call `debug_step(log_sink, "relation_version_pair_cap", {"file_count": len(file_ids_list), "cap": ...})` — pass `log_sink` into helper via stage `execute` (thread `self._log_sink` on stage if not already available; `RelationDetectionStage` already has `log_sink` in `__init__`).

- skip buckets where `len(ids) < 2` unchanged; for oversized **whole group**, still process buckets but do not add all-to-all across different `range_start` (already the case). Cap: skip version collection for buckets with `len(ids) > cap` individually.

Add test in `tests/application/use_cases/duplicate_detection/stages/test_relation_detection_stage.py`: mock 501 files in one `range_start` bucket → assert no hang / completes (smoke with mocked detector).

Minimal smoke test:

```python
def test_version_pairs_skipped_when_bucket_over_cap(monkeypatch):
    # construct context with 501 ids same range_start, enable_version True
    # assert results empty or debug_step called — match implementation
```

- [ ] **Step 3: Run relation stage tests**

Run: `pytest tests/application/use_cases/duplicate_detection/stages/test_relation_detection_stage.py -v`  
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add src/domain/value_objects/detection_config.py src/application/use_cases/duplicate_detection/stages/relation_detection_stage.py tests/application/use_cases/duplicate_detection/stages/test_relation_detection_stage.py
git commit -m "[application] cap version pair work in oversized blocking groups"
```

---

### Task 6: Docs index + full verification

**Files:**
- Modify: `docs/superpowers/README.md`

- [ ] **Step 1: Register spec and plan under Active artifacts**

Add bullets:

- Spec: `2026-05-22-duplicate-detection-title-blocking-design.md`
- Plan: `2026-05-22-duplicate-detection-title-blocking.md`

- [ ] **Step 2: Full verification gate**

Run: `python scripts/verify_phase_completion.py`  
Expected: pytest pass, ruff clean, mypy clean, black check pass.

- [ ] **Step 3: Commit docs**

```bash
git add docs/superpowers/README.md docs/superpowers/specs/2026-05-22-duplicate-detection-title-blocking-design.md docs/superpowers/plans/2026-05-22-duplicate-detection-title-blocking.md
git commit -m "[docs] add duplicate title blocking spec and plan"
```

---

## Plan self-review

| Spec requirement | Task |
|------------------|------|
| NFKC + punctuation norm | Task 2 |
| Same blocking for variants | Tasks 1–3 |
| Version for B (2168/2194, 1308/1310) | Task 4 |
| No Near/hash v1 change | (no task — by omission) |
| 500-file version cap | Task 5 |
| Golden acceptance | Tasks 1, 3, 4 |
| verify script | Task 6 |

No TBD placeholders in task steps.

---

## Execution handoff

**Plan saved to** `docs/superpowers/plans/2026-05-22-duplicate-detection-title-blocking.md`.

**Spec saved to** `docs/superpowers/specs/2026-05-22-duplicate-detection-title-blocking-design.md`.

Two execution options:

1. **Subagent-Driven (recommended)** — fresh subagent per task, review between tasks  
2. **Inline Execution** — run tasks in this session with `executing-plans` checkpoints  

Which approach do you want?
