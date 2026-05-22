# Exact Hash I/O Optimization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cut Exact duplicate detection wall time by reducing redundant hash file I/O, without changing exact group membership, via three isolated PRs (metrics → pruning → fused I/O).

**Architecture:** Instrument `ExactDuplicateDetector` first; add P2-1 small-file prefix-only path and skip redundant full reads in domain; then extend `IHashService` with `read_staged_fingerprints` and a fused `HashServiceAdapter`. Application layer only adds C-lite `wall_ms` + metric logging.

**Tech Stack:** Python 3.12+, `domain` / `application` / `infrastructure`, pytest, `python scripts/verify_phase_completion.py`.

**Spec:** [../specs/2026-05-22-exact-hash-io-optimization-design.md](../specs/2026-05-22-exact-hash-io-optimization-design.md)

---

## Phase overview (three PRs — do not merge phases in one PR)

| Phase | PR title | Primary outcome |
|-------|----------|-----------------|
| **PR-1** | C-lite metrics / baseline | `ExactDetectionResult` + counters; **zero** detection change |
| **PR-2** | Domain pruning | P2-1…P2-5; lower `full_hash_count` |
| **PR-3** | Fused staged I/O | `read_staged_fingerprints`; lower `file_open_count` |

### Per-phase contract

| | **PR-1** | **PR-2** | **PR-3** |
|---|----------|----------|----------|
| **Change files** | See Phase PR-1 table | See Phase PR-2 table | See Phase PR-3 table |
| **Test files** | `tests/unit/domain/services/test_exact_duplicate_detector.py` (baseline golden) | Same + G3 pruning cases | Same + adapter unit test |
| **Rollback** | Revert `ExactDetectionResult` + metrics; restore `list` return from `detect_exact` | Revert `exact_duplicate_detector.py` to PR-1 behavior | Revert port + adapter + detector staged path |
| **Metric fields** | All `ExactDetectMetrics` fields + `wall_ms` in log | Compare `full_hash_count`, `suffix_hash_count` vs PR-1 baseline | Compare `file_open_count` vs PR-2; record `wall_ms` |
| **Non-goals** | No pruning; no port change; no GUI | No fused I/O; no scan index | No Near/GUI/multiprocessing |
| **Verify** | `pytest` narrow + `verify_phase_completion.py` | Same + golden byte-identity | Same + import boundary grep |
| **Merge hard gate** | Golden identical; metrics ≠ detection input | Golden identical; `full_hash_count` ↓ on replay | Golden identical; `file_open_count` ↓; full verify green |
| **Aspirational** | Record 7.5k `wall_ms` baseline | `wall_ms` ↓ or noted neutral | `wall_ms` ≤ 0.7× PR-1 — **PR note only** if missed |

**Baseline reference (manual replay):** 7,491 files, Exact ~25s — `novelguard_logs_20260522_093428.txt` (`duplicate_detection_exact_complete`).

---

## File map (all phases)

| Action | Path | PR |
|--------|------|-----|
| Create | `src/domain/value_objects/exact_detect_metrics.py` | 1 |
| Create | `src/domain/value_objects/exact_detection_result.py` | 1 |
| Modify | `src/domain/services/exact_duplicate_detector.py` | 1, 2, 3 |
| Modify | `src/application/use_cases/duplicate_detection/stages/exact_duplicate_stage.py` | 1 |
| Create | `tests/unit/domain/services/test_exact_duplicate_detector.py` | 1 |
| Create | `tests/unit/domain/services/test_exact_duplicate_detector_pruning.py` | 2 (or same file new class) |
| Modify | `src/domain/ports/content_hash.py` | 3 |
| Modify | `src/infrastructure/hashing/hash_service_adapter.py` | 3 |
| Create | `tests/unit/infrastructure/hashing/test_hash_service_adapter_staged.py` | 3 |
| Modify | `docs/superpowers/README.md` | 1 (index link) |

**Call sites:** Only `ExactDuplicateStage` calls `detect_exact` today — update in PR-1.

---

# Phase PR-1: C-lite metrics / baseline

## PR-1 — change files

- `src/domain/value_objects/exact_detect_metrics.py` (new)
- `src/domain/value_objects/exact_detection_result.py` (new)
- `src/domain/services/exact_duplicate_detector.py`
- `src/application/use_cases/duplicate_detection/stages/exact_duplicate_stage.py`
- `tests/unit/domain/services/test_exact_duplicate_detector.py` (new)
- `docs/superpowers/README.md` (plan/spec links if missing)

## PR-1 — metric fields (logged on `duplicate_detection_exact_complete`)

| Field | Source |
|-------|--------|
| `wall_ms` | `ExactDuplicateStage` (`time.perf_counter`) |
| `size_bucket_count` | `ExactDetectMetrics` |
| `files_considered` | `ExactDetectMetrics` |
| `prefix_hash_count` | increment on each `calculate_prefix_hash` |
| `suffix_hash_count` | increment on each `calculate_suffix_hash` |
| `full_hash_count` | increment on each `calculate_hash` |
| `file_open_count` | same as sum of hash calls in PR-1 (1 per method call) |
| `exact_groups_count` | existing |
| `total_exact_files` | existing |

## PR-1 — non-goals

- No P2-1 pruning
- No `read_staged_fingerprints`
- No `ExactDuplicateStage` behavior branches on metrics

## PR-1 — rollback

Revert PR-1 commit(s): `detect_exact` returns `list[ExactDuplicateRelation]` again; remove VOs; remove extra log keys. Golden tests removed or adapted.

---

### Task PR1-1: Value objects

**Files:**
- Create: `src/domain/value_objects/exact_detect_metrics.py`
- Create: `src/domain/value_objects/exact_detection_result.py`

- [ ] **Step 1: Add `ExactDetectMetrics`**

```python
"""Exact duplicate detection instrumentation counters."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ExactDetectMetrics:
    size_bucket_count: int = 0
    files_considered: int = 0
    prefix_hash_count: int = 0
    suffix_hash_count: int = 0
    full_hash_count: int = 0
    file_open_count: int = 0

    def merged(self, other: "ExactDetectMetrics") -> "ExactDetectMetrics":
        return ExactDetectMetrics(
            size_bucket_count=self.size_bucket_count + other.size_bucket_count,
            files_considered=self.files_considered + other.files_considered,
            prefix_hash_count=self.prefix_hash_count + other.prefix_hash_count,
            suffix_hash_count=self.suffix_hash_count + other.suffix_hash_count,
            full_hash_count=self.full_hash_count + other.full_hash_count,
            file_open_count=self.file_open_count + other.file_open_count,
        )
```

- [ ] **Step 2: Add `ExactDetectionResult`**

```python
"""Exact duplicate detection outcome + metrics."""

from dataclasses import dataclass

from domain.value_objects.duplicate_relation import ExactDuplicateRelation
from domain.value_objects.exact_detect_metrics import ExactDetectMetrics


@dataclass(frozen=True)
class ExactDetectionResult:
    relations: list[ExactDuplicateRelation]
    metrics: ExactDetectMetrics
```

- [ ] **Step 3: Commit**

```bash
git add src/domain/value_objects/exact_detect_metrics.py src/domain/value_objects/exact_detection_result.py
git commit -m "[domain] add ExactDetectionResult and ExactDetectMetrics"
```

---

### Task PR1-2: Golden tests with counting fake hash (TDD baseline)

**Files:**
- Create: `tests/unit/domain/services/test_exact_duplicate_detector.py`

- [ ] **Step 1: Write tests + fake port**

```python
"""Exact duplicate detector — golden behavior and hash call counts."""

from dataclasses import dataclass, field
from pathlib import Path

import pytest

from domain.entities.file_entry import FileEntry
from domain.services.exact_duplicate_detector import ExactDuplicateDetector
from domain.value_objects.blocking_group import BlockingGroup
from domain.value_objects.detection_config import DetectionDefaults


@dataclass
class _CountingHashService:
    prefix_calls: int = 0
    suffix_calls: int = 0
    full_calls: int = 0

    def calculate_hash(self, file_path: Path) -> str:
        self.full_calls += 1
        return f"full:{file_path.name}"

    def calculate_prefix_hash(self, file_path: Path, size: int = DetectionDefaults.SAMPLE_SIZE) -> str:
        self.prefix_calls += 1
        return f"pre:{file_path.name}"

    def calculate_suffix_hash(self, file_path: Path, size: int = DetectionDefaults.SAMPLE_SIZE) -> str:
        self.suffix_calls += 1
        return f"suf:{file_path.name}"


def _entry(fid: int, name: str, size: int) -> FileEntry:
    return FileEntry(
        file_id=fid,
        path=Path(name),
        size=size,
        mtime=1.0,
        extension=".txt",
    )


def _groups(result) -> list[frozenset[int]]:
    return [frozenset(r.file_ids) for r in result.relations]


class TestExactGoldenBaseline:
    def test_two_large_identical_paths_same_size(self) -> None:
        hs = _CountingHashService()
        hs.calculate_prefix_hash = lambda p, size=65536: "same-pre"  # type: ignore[method-assign]
        hs.calculate_suffix_hash = lambda p, size=65536: "same-suf"  # type: ignore[method-assign]
        hs.calculate_hash = lambda p: "same-full"  # type: ignore[method-assign]
        det = ExactDuplicateDetector(hs)
        entries = {1: _entry(1, "a.txt", 100_000), 2: _entry(2, "b.txt", 100_000)}
        bg = BlockingGroup(series_title_norm="", extension="", file_ids=[1, 2], range_start=None)
        result = det.detect_exact(bg, entries)
        assert _groups(result) == [frozenset({1, 2})]
        assert result.metrics.prefix_hash_count == 2
        assert result.metrics.full_hash_count == 2

    def test_large_same_pre_suf_different_full_no_group(self) -> None:
        hs = _CountingHashService()

        def prefix(_p: Path, size: int = 65536) -> str:
            return "same-pre"

        def suffix(_p: Path, size: int = 65536) -> str:
            return "same-suf"

        def full(p: Path) -> str:
            return "full-a" if p.name == "a.txt" else "full-b"

        hs.calculate_prefix_hash = prefix  # type: ignore[method-assign]
        hs.calculate_suffix_hash = suffix  # type: ignore[method-assign]
        hs.calculate_hash = full  # type: ignore[method-assign]
        det = ExactDuplicateDetector(hs)
        entries = {1: _entry(1, "a.txt", 200_000), 2: _entry(2, "b.txt", 200_000)}
        bg = BlockingGroup(series_title_norm="", extension="", file_ids=[1, 2], range_start=None)
        result = det.detect_exact(bg, entries)
        assert result.relations == []
```

- [ ] **Step 2: Run — expect FAIL** (return type not yet `ExactDetectionResult`)

Run: `pytest tests/unit/domain/services/test_exact_duplicate_detector.py -v`  
Expected: FAIL (AttributeError or type mismatch).

---

### Task PR1-3: Instrument detector + return `ExactDetectionResult`

**Files:**
- Modify: `src/domain/services/exact_duplicate_detector.py`

- [ ] **Step 1: Add metrics accumulator helper on detector**

Private methods `_inc_prefix`, `_inc_suffix`, `_inc_full` wrapping hash service calls; increment `file_open_count` equally in PR-1.

At start of `detect_exact`, init `ExactDetectMetrics()`; set `files_considered = len(valid ids)`; increment `size_bucket_count` by 1 per call (stage calls per bucket — detector sees one blocking group per invocation).

Return:

```python
return ExactDetectionResult(relations=exact_relations, metrics=metrics)
```

- [ ] **Step 2: Run golden tests**

Run: `pytest tests/unit/domain/services/test_exact_duplicate_detector.py -v`  
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add src/domain/services/exact_duplicate_detector.py tests/unit/domain/services/test_exact_duplicate_detector.py
git commit -m "[domain] return ExactDetectionResult with hash I/O metrics"
```

---

### Task PR1-4: Stage logging + aggregate metrics across size buckets

**Files:**
- Modify: `src/application/use_cases/duplicate_detection/stages/exact_duplicate_stage.py`

- [ ] **Step 1: Update stage loop**

```python
import time
from domain.value_objects.exact_detect_metrics import ExactDetectMetrics

# inside execute(), before size loop:
t0 = time.perf_counter()
total_metrics = ExactDetectMetrics()

# per size bucket:
out = self._exact_detector.detect_exact(synthetic_group, context.file_entries_map)
total_metrics = total_metrics.merged(out.metrics)
for rel in out.relations:
    ...

wall_ms = int((time.perf_counter() - t0) * 1000)
debug_step(..., {
    "exact_groups_count": len(exact_results),
    "total_exact_files": sum(len(r.file_ids) for r in exact_results),
    "wall_ms": wall_ms,
    "size_bucket_count": total_metrics.size_bucket_count,
    "files_considered": total_metrics.files_considered,
    "prefix_hash_count": total_metrics.prefix_hash_count,
    "suffix_hash_count": total_metrics.suffix_hash_count,
    "full_hash_count": total_metrics.full_hash_count,
    "file_open_count": total_metrics.file_open_count,
})
```

Note: `size_bucket_count` in detector increments once per `detect_exact` call; stage calls once per multi-file size bucket — align counter semantics in detector (increment once at start of `detect_exact`).

- [ ] **Step 2: Run verification**

Run: `python scripts/verify_phase_completion.py`  
Expected: all stages PASS

- [ ] **Step 3: Record baseline (manual)**

Run duplicate detection on ~7.5k folder; paste `duplicate_detection_exact_complete` JSON into PR-1 description.

- [ ] **Step 4: Commit**

```bash
git add src/application/use_cases/duplicate_detection/stages/exact_duplicate_stage.py
git commit -m "[application] log Exact hash I/O metrics and wall_ms"
```

## PR-1 — P-gate checklist

- [ ] `pytest tests/unit/domain/services/test_exact_duplicate_detector.py` PASS
- [ ] `python scripts/verify_phase_completion.py` PASS
- [ ] Golden groups unchanged vs pre-PR-1 (capture snapshot in PR description)
- [ ] Baseline `wall_ms` + hash counts recorded

---

# Phase PR-2: Domain pruning + small-file fast path

## PR-2 — change files

- `src/domain/services/exact_duplicate_detector.py` (P2-1…P2-5)
- `tests/unit/domain/services/test_exact_duplicate_detector.py` (extend)

## PR-2 — metric fields (compare to PR-1 baseline)

Expect **`full_hash_count` ↓** and often **`suffix_hash_count` ↓** on same corpus; `prefix_hash_count` may stay similar. Record deltas in PR-2 note.

## PR-2 — non-goals

- No `read_staged_fingerprints`
- No adapter fusion (except optional P2-5 comment-only in domain)
- No change to `ExactDuplicateStage` size-bucketing

## PR-2 — rollback

Single revert of detector + tests restores PR-1 hash call pattern; golden tests from PR-1 must pass again.

---

### Task PR2-1: P2-1 small-file prefix-only tests (TDD)

**Files:**
- Modify: `tests/unit/domain/services/test_exact_duplicate_detector.py`

- [ ] **Step 1: Add small-file tests**

```python
S = DetectionDefaults.SAMPLE_SIZE


class TestExactPruningSmallFiles:
    def test_small_identical_prefix_only_one_group(self) -> None:
        hs = _CountingHashService()
        hs.calculate_prefix_hash = lambda p, size=65536: "small-same"  # type: ignore[method-assign]
        det = ExactDuplicateDetector(hs)
        entries = {
            1: _entry(1, "a.txt", S),
            2: _entry(2, "b.txt", S),
        }
        bg = BlockingGroup(series_title_norm="", extension="", file_ids=[1, 2], range_start=None)
        result = det.detect_exact(bg, entries)
        assert _groups(result) == [frozenset({1, 2})]
        assert result.metrics.suffix_hash_count == 0
        assert result.metrics.full_hash_count == 0
        assert result.metrics.prefix_hash_count == 2

    def test_small_different_prefix_no_group(self) -> None:
        hs = _CountingHashService()
        det = ExactDuplicateDetector(hs)
        entries = {1: _entry(1, "a.txt", 100), 2: _entry(2, "b.txt", 100)}
        bg = BlockingGroup(series_title_norm="", extension="", file_ids=[1, 2], range_start=None)
        result = det.detect_exact(bg, entries)
        assert result.relations == []
```

- [ ] **Step 2: Run — expect FAIL**

Run: `pytest tests/unit/domain/services/test_exact_duplicate_detector.py::TestExactPruningSmallFiles -v`  
Expected: FAIL (`suffix_hash_count` still > 0).

---

### Task PR2-2: Implement P2-1 … P2-5 in detector

**Files:**
- Modify: `src/domain/services/exact_duplicate_detector.py`

- [ ] **Step 1: Branch in `_relations_for_size_group`**

After building prefix groups, for bucket file size `size` (from `FileEntry.size` of first id in `file_ids`):

- If `size <= DetectionDefaults.SAMPLE_SIZE`: for each prefix group with `len >= 2`, emit `_make_exact_relation` using prefix hash as `full_hash` evidence key; **do not** call suffix/full helpers.
- Else: existing suffix → full pipeline; enforce P2-2 (never skip full when suffix group len >= 2).

- [ ] **Step 2: P2-5** — if any legacy path still hits suffix+full for `size <= S`, reuse suffix digest as full key without second `calculate_hash`.

- [ ] **Step 3: Run all exact detector tests**

Run: `pytest tests/unit/domain/services/test_exact_duplicate_detector.py -v`  
Expected: PASS

- [ ] **Step 4: Run full verify**

Run: `python scripts/verify_phase_completion.py`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/domain/services/exact_duplicate_detector.py tests/unit/domain/services/test_exact_duplicate_detector.py
git commit -m "[domain] exact pruning P2-1 small-file prefix-only path"
```

## PR-2 — P-gate checklist

- [ ] Golden tests G1–G5 (spec table) PASS
- [ ] G3 large same pre/suf different full — still **no** group
- [ ] `full_hash_count` lower than PR-1 baseline on replay (PR note)
- [ ] `verify_phase_completion.py` PASS

---

# Phase PR-3: Fused I/O / staged fingerprint port

## PR-3 — change files

- `src/domain/ports/content_hash.py`
- `src/infrastructure/hashing/hash_service_adapter.py`
- `src/domain/services/exact_duplicate_detector.py`
- `tests/unit/infrastructure/hashing/test_hash_service_adapter_staged.py` (new)
- `tests/unit/domain/services/test_exact_duplicate_detector.py` (update counting fake)

## PR-3 — metric fields

**`file_open_count`** must drop vs PR-2 (one increment per `read_staged_fingerprints`). `prefix_hash_count` / `suffix_hash_count` may map to staged reads — document mapping in PR-3 note.

## PR-3 — non-goals

- Scan-time index
- Deprecating legacy `calculate_*` methods (keep for other callers/tests)

## PR-3 — rollback

Revert port method + adapter implementation; detector uses `calculate_*` again. PR-2 pruning logic remains.

---

### Task PR3-1: Port + staged VO

**Files:**
- Modify: `src/domain/ports/content_hash.py`

- [ ] **Step 1: Add types and protocol method**

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class StagedContentFingerprints:
    prefix_hash: str
    suffix_hash: str
    full_hash: str | None

class IHashService(Protocol):
    ...
    def read_staged_fingerprints(
        self,
        file_path: Path,
        file_size: int,
        *,
        need_full: bool = False,
    ) -> StagedContentFingerprints:
        ...
```

- [ ] **Step 2: Commit**

```bash
git add src/domain/ports/content_hash.py
git commit -m "[domain] add read_staged_fingerprints to IHashService"
```

---

### Task PR3-2: Adapter tests (TDD)

**Files:**
- Create: `tests/unit/infrastructure/hashing/test_hash_service_adapter_staged.py`

- [ ] **Step 1: Write tests using `tmp_path`**

- Small file (≤64KiB): one open, `prefix_hash` equals full-content hash, `need_full=False` → `full_hash` None or equal per spec.
- Large file: prefix + suffix from samples; `need_full=True` → `full_hash` populated; assert single open via mock or read counter pattern.

- [ ] **Step 2: Run — FAIL**

Run: `pytest tests/unit/infrastructure/hashing/test_hash_service_adapter_staged.py -v`

---

### Task PR3-3: Implement fused adapter

**Files:**
- Modify: `src/infrastructure/hashing/hash_service_adapter.py`

- [ ] **Step 1: Implement `read_staged_fingerprints`**

Single `with open(file_path, "rb") as f:`:

- Read up to `SAMPLE_SIZE` for prefix hash.
- If `file_size <= SAMPLE_SIZE`: suffix_hash = prefix over whole file (or hash entire buffer once).
- Else: seek `file_size - SAMPLE_SIZE` for suffix.
- If `need_full`: stream full file in same open (or reuse buffer when small).

Legacy methods delegate to staged for DRY **or** duplicate minimal logic — prefer delegate to avoid drift.

- [ ] **Step 2: Run adapter tests PASS**

- [ ] **Step 3: Commit**

```bash
git add src/infrastructure/hashing/hash_service_adapter.py tests/unit/infrastructure/hashing/test_hash_service_adapter_staged.py
git commit -m "[infra] fused read_staged_fingerprints for exact hashing"
```

---

### Task PR3-4: Migrate detector to staged reads

**Files:**
- Modify: `src/domain/services/exact_duplicate_detector.py`
- Modify: `tests/unit/domain/services/test_exact_duplicate_detector.py` (`_CountingHashService` implements `read_staged_fingerprints`)

- [ ] **Step 1: Replace per-method hash calls with staged API**

For each file in a size bucket:

- `need_full = (size > S) and (file will be in suffix group with >=2 members)` — compute suffix groups first from staged prefix/suffix only, then second pass for `need_full` on collision groups only (or batch plan in one pass per file with deferred full).

Simpler approach: one `read_staged_fingerprints` per file with `need_full=False` first to collect prefix/suffix; then `need_full=True` only for files in multi-member suffix groups when `size > S`.

- [ ] **Step 2: Metrics** — `file_open_count` += 1 per staged call.

- [ ] **Step 3: Run all tests + verify**

Run: `python scripts/verify_phase_completion.py`  
Expected: PASS

- [ ] **Step 4: 7.5k replay + PR note**

Record: `wall_ms`, `file_open_count`, ratio vs PR-1. If wall_ms > 0.7 × PR-1, document OS cache / disk / antivirus — **still merge if hard gates pass**.

- [ ] **Step 5: Layer boundary check**

Run: `rg "infrastructure" src/domain`  
Expected: no matches.

- [ ] **Step 6: Commit**

```bash
git add src/domain/services/exact_duplicate_detector.py tests/unit/domain/services/test_exact_duplicate_detector.py
git commit -m "[domain] use staged fingerprint reads for exact duplicate detection"
```

## PR-3 — P-gate checklist

- [ ] Golden identical vs PR-2
- [ ] `file_open_count` ↓ vs PR-2 on replay
- [ ] `verify_phase_completion.py` PASS
- [ ] No `infrastructure` import in `domain`
- [ ] Aspirational wall_ms documented

---

## Plan self-review (spec coverage)

| Spec requirement | Task |
|------------------|------|
| `ExactDetectionResult` dataclass | PR1-1 |
| P2-1 preconditions | PR2-2 + spec updated |
| PR-3 aspirational wall_ms | PR3-4 note |
| PR-3 hard gates | Phase overview table |
| Golden G1–G5 | PR1-2, PR2-1, PR2-2 |
| `read_staged_fingerprints` | PR3-1–PR3-4 |
| C-lite `wall_ms` | PR1-4 |
| Non-goals unchanged | Per-phase tables |

No TBD placeholders remain in task steps.

---

## Execution handoff

Plan complete and saved to `docs/superpowers/plans/2026-05-22-exact-hash-io-optimization.md`.

**Two execution options:**

1. **Subagent-Driven (recommended)** — fresh subagent per task, review between tasks  
2. **Inline Execution** — same session with `executing-plans`, batched checkpoints  

**Which approach do you want for PR-1?**
