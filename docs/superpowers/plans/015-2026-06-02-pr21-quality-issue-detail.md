# PR-21: Quality Issue Detail — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship typed `getQualityIssueDetail` with `ok` | `not_found` union, domain-backed evidence, file metadata, read-only repair eligibility, and Quality workspace detail drawer with not-found / stale / error UX.

**Architecture:** `build_quality_issue_detail` in `application/` joins `_quality_rows_cache`, `LibraryIndexPort.quality_issues()`, and `FileRecord`. Bridge validates outbound DTO. Web mirrors PR-18 fetch pattern; client compares `libraryRevision` for stale banner.

**Tech Stack:** Python 3.12, React + TypeScript, pytest (extend existing files only).

**Spec:** [009-2026-06-02-quality-issue-detail-design.md](../specs/009-2026-06-02-quality-issue-detail-design.md) (**approved** 2026-06-02)

**Plan status:** **Implemented** (2026-06-02) — verification: 76 pytest (bridge contract), web lint PASS.

**Parent:** [001 PR-20..25 roadmap](../roadmap/001-2026-06-02-pr20-pr25-development-roadmap.md) — Wave D PR-21

**Depends on:** PR-14c (analyzer + rows), PR-14d (quality bridge rows), PR-18 (detail fetch pattern reference)

**Test policy:** Extend `tests/test_bridge_contract.py`, `mockBridge.ts` only. No new test files without `TEST_ALLOWED`.

---

## Plan-locked decisions (Spec 009 + gate review)

| Lock | Value |
|------|--------|
| Response | `QualityIssueDetailResponse`: `ok` \| `not_found`; `ok` wraps `detail: QualityIssueDetail` |
| Union | No Unknown success placeholder; no server `{ status: "stale" }` |
| Id normalize | Accept `issueId` with/without `quality:` prefix |
| Evidence source | Domain `QualityIssue.evidence` via `index.quality_issues()` |
| Revision | `ok.detail.libraryRevision` at build time |
| Stale | Client compares `detail.libraryRevision` vs `snapshot.libraryRevision` after fetch → `quality-detail-stale` |
| Repair | All `repairEligibility.eligible === false` in PR-21 |
| UTF-8 future | `invalid_utf8` → `futureAction: "utf8_convert"` label only |
| Validation | `validate_quality_issue_detail` on bridge return |
| Dev JSON | Raw evidence `<pre>` only when `import.meta.env.DEV` |

### Implementation notes (approved with plan 2026-06-02)

1. **`normalize_quality_issue_id`** — prefix correction only. Allow `deadbeef` → `quality:deadbeef` and `quality:deadbeef`. Reject malformed → lookup miss → `not_found`: `quality:quality:…`, `""`, whitespace-only. Never promote arbitrary strings to valid ids.
2. **Task 6 stale sync** — `useEffect` on `snapshot.libraryRevision` + open `detail`: `setDetailStale(detail.libraryRevision !== snapshot.libraryRevision)` (clears stale when revision realigns).
3. **`not_found.id`** — always normalized id (contract test: request `deadbeef` → `id == "quality:deadbeef"`).

---

## File map

| File | Action |
|------|--------|
| `src/application/quality_issue_detail.py` | **Create** — normalize id, `build_quality_issue_detail`, evidence + eligibility |
| `src/application/library_session.py` | **Modify** — delegate detail; pass index issues + revision |
| `src/app/bridge_contract.py` | **Modify** — `validate_quality_issue_detail` |
| `src/app/bridge_api.py` | **Modify** — validate on return |
| `web/src/types/quality.ts` | **Modify** — `QualityIssueDetail`, `QualityIssueDetailResponse`, evidence types |
| `web/src/bridge/NovelGuardBridge.ts` | **Modify** — typed `getQualityIssueDetail` |
| `web/src/bridge/pywebviewBridge.ts` | **Modify** — typed call (optional validate helper) |
| `web/src/bridge/mockBridge.ts` | **Modify** — PR-21-shaped detail from `buildQualityRows()` |
| `web/src/features/work/QualityWorkspace.tsx` | **Modify** — not-found, stale, detail error/retry, evidence UI |
| `tests/test_bridge_contract.py` | **Modify** — not_found, evidence shape, revision field |

---

## Task 0: Plan gate checklist

- [x] Spec 009 **approved** (2026-06-02) — G1 + G2 locked.
- [x] Human approves this plan (status → **Approved** 2026-06-02).
- [x] Grill-me **G1** (2026-06-02) — `not_found`; `message: "quality_issue_not_found"`.
- [x] Grill-me **G2** (2026-06-02) — `ok.detail.libraryRevision`; client stale; no server `stale`.
- [x] Implementation approved — proceed Tasks 1–7.

---

## Task 1: Python detail builder

**Files:** `src/application/quality_issue_detail.py`, `src/application/library_session.py`

- [ ] **Step 1:** Create `normalize_quality_issue_id` per spec.

- [ ] **Step 2:** Create `_repair_eligibility_for_kind(kind: QualityKind) -> dict` static table (all `eligible: false`).

- [ ] **Step 3:** Create `_build_evidence(issue: QualityIssue, record: FileRecord) -> dict` mapping four kinds.

- [ ] **Step 4:** Implement `build_quality_issue_detail`:

```python
def build_quality_issue_detail(
    issue_id: str,
    *,
    quality_rows: list[dict[str, Any]],
    quality_issues: list[QualityIssue],
    files_by_id: dict[str, FileRecord],
    library_revision: int,
) -> dict[str, Any]:
    normalized = normalize_quality_issue_id(issue_id)
    row = next((r for r in quality_rows if r.get("id") == normalized), None)
    if row is None:
        return {
            "status": "not_found",
            "id": normalized,
            "message": "quality_issue_not_found",
        }
    domain_id = normalized.removeprefix("quality:")
    issue = next((i for i in quality_issues if i.issue_id == domain_id), None)
    if issue is None:
        return {
            "status": "not_found",
            "id": normalized,
            "message": "quality_issue_not_found",
        }
    record = files_by_id.get(issue.file_id)
    if record is None:
        return {
            "status": "not_found",
            "id": normalized,
            "message": "quality_issue_not_found",
        }
    return {
        "status": "ok",
        "detail": {
            "id": normalized,
            "libraryRevision": library_revision,
            # ... issueType, name, path, encoding, integrity, severity,
            # suggestedAction, file, evidence, repairEligibility
        },
    }
```

- [ ] **Step 5:** Replace `LibrarySession.get_quality_issue_detail` body:

```python
def get_quality_issue_detail(self, issue_id: str) -> dict[str, Any]:
    with self._lock:
        return build_quality_issue_detail(
            issue_id,
            quality_rows=self._quality_rows_cache,
            quality_issues=self._index.quality_issues(),
            files_by_id=self._files_by_id,
            library_revision=self._library_revision,
        )
```

Run: `python -m pytest tests/test_bridge_contract.py -k quality_issue_detail -v`

---

## Task 2: Bridge contract validation

**Files:** `src/app/bridge_contract.py`, `src/app/bridge_api.py`

- [ ] **Step 1:** Add `validate_quality_issue_detail(payload: Any) -> None`:

  - Require `status` in `{"ok", "not_found"}`
  - `not_found`: `id`, `message` strings
  - `ok`: `detail` object with required keys from spec § Field rules
  - Reject `status == "stale"` or any unknown status
  - `detail.repairEligibility.eligible` must be `False` for PR-21

- [ ] **Step 2:** `BridgeApi.get_quality_issue_detail`:

```python
def get_quality_issue_detail(self, issue_id: str) -> dict[str, Any]:
    payload = self._session.get_quality_issue_detail(issue_id)
    validate_quality_issue_detail(payload)
    return payload
```

Run: `python -m pytest tests/test_bridge_contract.py -k quality_issue_detail -v`

---

## Task 3: Contract tests

**Files:** `tests/test_bridge_contract.py`

- [ ] **Step 1:** Update `test_get_quality_issue_detail_from_cache`:

```python
assert detail["status"] == "ok"
assert isinstance(detail["detail"]["libraryRevision"], int)
assert detail["detail"]["evidence"]["kind"] in (
    "empty_file", "tiny_file", "invalid_utf8", "read_error",
)
assert detail.get("status") != "stale"
```

- [ ] **Step 2:** Add `test_get_quality_issue_detail_not_found`:

```python
def test_get_quality_issue_detail_not_found(tmp_path: Path) -> None:
    session = create_library_session(MemoryLibraryIndex())
    session.select_folder(str(tmp_path))
    api = create_bridge_api(session)
    detail = api.get_quality_issue_detail("quality:deadbeef")
    assert detail["status"] == "not_found"
    assert detail["message"] == "quality_issue_not_found"
```

- [ ] **Step 3:** Add encoding fixture — `detail.evidence.kind == "invalid_utf8"`, `detail.repairEligibility.futureAction == "utf8_convert"`.

- [ ] **Step 4:** Add id normalization test — bare hex id without `quality:` prefix resolves when row exists.

Run: `python -m pytest tests/test_bridge_contract.py -q`

---

## Task 4: TypeScript DTOs + bridge typing

**Files:** `web/src/types/quality.ts`, `web/src/bridge/NovelGuardBridge.ts`, `web/src/bridge/pywebviewBridge.ts`

- [ ] **Step 1:** Add `QualityIssueDetail` (inner) + `QualityIssueDetailResponse` from spec 009.

- [ ] **Step 2:** `NovelGuardBridge.getQualityIssueDetail(issueId: string): Promise<QualityIssueDetailResponse>`.

- [ ] **Step 3:** `pywebviewBridge` — typed return (no mock fallback).

Run: `cd web && npm run lint`

---

## Task 5: mockBridge parity

**Files:** `web/src/bridge/mockBridge.ts`

- [ ] **Step 1:** Build detail from row + synthetic domain evidence (mirror Python shapes).

- [ ] **Step 2:** Unknown id → `{ status: "not_found", … }`.

- [ ] **Step 3:** `ok` returns `{ status: "ok", detail: { libraryRevision, … } }` from snapshot revision.

Run: `cd web && npm run lint`

---

## Task 6: QualityWorkspace detail UX

**Files:** `web/src/features/work/QualityWorkspace.tsx`

- [ ] **Step 1:** State: `detailError: string | null`, `detailStale: boolean`.

- [ ] **Step 2:** `loadDetail` — handle union:

```typescript
void bridge.getQualityIssueDetail(row.id).then((payload) => {
  if (payload.status === "not_found") {
    setDetail(null);
    setDetailError("Issue not found");
    setDetailStale(false);
    return;
  }
  const inner = payload.detail;
  setDetail(inner);
  setDetailError(null);
  setDetailStale(inner.libraryRevision !== snapshot.libraryRevision);
}).catch((err) => {
  setDetail(null);
  setDetailError(err instanceof Error ? err.message : "Failed to load detail");
  setDetailStale(false);
});
```

- [ ] **Step 3:** UI blocks:

  - Evidence summary (kind, message, severity, size)
  - File card (path, size, mtime, extension)
  - Repair eligibility badge
  - `quality-detail-error` + retry
  - `quality-detail-stale` when `detailStale` — read-only body; refetch/refresh CTA
  - Dev-only raw JSON toggle

- [ ] **Step 4:** `useEffect` on `snapshot.libraryRevision` — if detail open and stale, set `detailStale` true.

Run: `cd web && npm run lint`

---

## Task 7: Verification + docs

- [ ] **Step 1:** `python scripts/verify_phase_completion.py`

- [ ] **Step 2:** Update plan status → **Implemented** with date + pytest count.

- [ ] **Step 3:** Roadmap 001 — PR-21 row → Done (after merge/closure).

- [ ] **Step 4:** Spec 009 status → implemented reference in changelog.

- [ ] **Step 5:** Plan scope freeze — no repair execution, no new bridge methods.

---

## Verification commands

```bash
python scripts/verify_phase_completion.py
```

```bash
python -m pytest tests/test_bridge_contract.py -k "quality_issue" -v
```

```bash
cd web && npm run lint
```

---

## Risk register

| Risk | Mitigation |
|------|------------|
| Breaking Unknown placeholder | Document in spec; update tests + mockBridge together |
| Missing domain issue for row | Treat as `not_found` (index/cache drift) |
| Stale false positive during scan | Compare revision only after fetch completes; rescan clears |
| Evidence schema drift | Bridge validator + kind-specific contract tests |

---

## Test plan (G1 + G2)

**Contract (pytest):**

- `getQualityIssueDetail(existingId)` → `status: "ok"`, `detail.libraryRevision` present
- `getQualityIssueDetail(unknownId)` → `status: "not_found"`, `message: "quality_issue_not_found"`
- No response with `status: "stale"` in PR-21

**UI (lint / manual / future Vitest if allowed):**

- `detail.libraryRevision === snapshot.libraryRevision` → no `quality-detail-stale`
- `detail.libraryRevision !== snapshot.libraryRevision` → `quality-detail-stale` visible; detail read-only
- Refetch/refresh guidance shown when stale

## Gate reviewer checklist

| # | Fixture | Task |
|---|---------|------|
| 1 | Known row → `ok.detail.libraryRevision` | Task 3 |
| 2 | Unknown id → `not_found` | Task 3 |
| 3 | `invalid_utf8` in `detail.evidence` + `futureAction` | Task 3 |
| 4 | Id without `quality:` prefix | Task 3 |
| 5 | No `status: "stale"` in bridge | Task 2, 3 |
| 6 | Stale banner testid when revision drifts | Task 6 |

---

## Commit plan (after implementation)

```text
feat(application): build quality issue detail from domain evidence
feat(bridge): validate QualityIssueDetail union
feat(ui): quality detail drawer not-found stale error UX
test(quality): contract tests for detail ok and not_found
docs(superpowers): PR-21 spec/plan closure
```

---

## Acceptance criteria

PR-21 matches spec 009 when all are true:

- [ ] `QualityIssueDetailResponse` validated; `ok.detail` nested shape
- [ ] Domain evidence on `ok.detail`; file metadata present
- [ ] No server `stale` union
- [ ] `repairEligibility.eligible` always false
- [ ] Quality workspace: evidence, eligibility, not-found, stale, detail error
- [ ] `queryQualityRows` regression-free
- [ ] `verify_phase_completion.py` PASS

---

## Changelog

| Date | Change |
|------|--------|
| 2026-06-02 | Initial plan 015 from draft spec 009 + PR-20 closure handoff |
| 2026-06-02 | G2 locked — `ok.detail` wrapper; client stale; test plan added |
| 2026-06-02 | **Implemented** — 76 pytest; stale via `useMemo` (revision compare) |

---

## Plan closure (PR-21 slice)

**Closed:** 2026-06-02  
**Verification:** `python scripts/verify_phase_completion.py` — **5/5 PASS** (pytest, ruff, mypy, black, npm lint); bridge contract **76** tests; npm lint 0 errors / 1 pre-existing TanStack warning  

**Delivered:** `quality_issue_detail.py`, bridge validator, 5 new/updated contract tests, TS `QualityIssueDetailResponse`, mock parity, QualityWorkspace detail UX (not-found, stale, error/retry, evidence, repair label).
