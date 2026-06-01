# PR-10: UI Contract Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restore and enforce the NovelGuard UI bridge contract across TypeScript and Python so `npm run build`, contract tests, and `BridgeApi` import pass without unbounded rows in `AppSnapshot`.

**Architecture:** Runtime validators live in `web/src/contracts/` (TS) and `src/app/bridge_contract.py` (Python). `mockBridge` and `BridgeApi` call validators on every response. Tests use Vitest (web) and pytest (Python) with shared fixture shapes; no new UI screens.

**Tech Stack:** React 19, TypeScript 6, Vitest 3, Vite 8, Python 3.12, pytest 8.

**Spec reference:** `docs/superpowers/specs/2026-06-01-novelguard-ui-overhaul-design.md` (approved) — Bridge & snapshot contract §.

**Testing permission:**

```text
TEST_ALLOWED — Python + TypeScript contract tests are explicitly allowed for PR-10.

Rationale:
PR-10 fixes missing contract modules that currently break npm build and Python BridgeApi import.
Tests are limited to schema/parity/SelectionScope validation and do not expand UI behavior.
```

**Non-goals (PR-10):** Playwright, E2E, new UI, layout redesign, perf benchmark, preview-token/stale-apply invariants, repair/finalize, pywebview silent-fallback UX redesign.

## Implementation status

| Item | Status | Branch |
|------|--------|--------|
| PR-10 (Tasks 1–11) | **Done** | `feat/web-ui-overhaul` |

**Verification (2026-06-01):** `cd web && npm run build` PASS · `npm run test:contracts` 25/25 PASS · `pytest tests/test_bridge_contract.py` 12/12 PASS · `python scripts/verify_phase_completion.py` PASS

Plan scope freeze holds — PR-11+ handled in `002-2026-06-01-novelguard-ui-e2e-smoke.md`.

---

## File map

| File | Responsibility |
|------|----------------|
| `web/vite.config.ts` | Vitest `test` block |
| `web/package.json` | `vitest` devDep, `test` / `test:contracts` scripts |
| `web/src/contracts/snapshotContract.ts` | Reject forbidden arrays on `AppSnapshot` |
| `web/src/contracts/reviewPageContract.ts` | `ReviewRowsPage` shape + limit ≤ 200 |
| `web/src/contracts/qualityPageContract.ts` | `QualityRowsPage` shape + limit ≤ 200 |
| `web/src/contracts/bridgeParity.ts` | `NovelGuardBridge` method list + pywebview snake_case map |
| `web/src/contracts/fixtures.ts` | Valid/invalid payloads for tests |
| `web/src/contracts/*.test.ts` | Vitest contract tests |
| `web/src/types/selection.test.ts` | `validateSelectionScope` edge cases |
| `web/src/bridge/bridgeParity.test.ts` | mock vs pywebview adapter parity |
| `src/app/bridge_contract.py` | Python validators (mirror TS rules) |
| `tests/test_bridge_contract.py` | pytest for `BridgeApi` + validators |
| `tests/fixtures/bridge_contract_fixtures.py` | Valid/invalid dict fixtures |
| `docs/superpowers/specs/2026-06-01-novelguard-ui-overhaul-design.md` | Changelog line only (audit verified) |

**Unchanged behavior:** `mockBridge` mock data logic, grid UI, `pywebviewBridge` per-method `.catch(() => mockBridge.*)` (PR-11).

---

## Acceptance criteria

```text
✓ npm run build pass
✓ npm run test:contracts pass (or npm test)
✓ pytest tests/test_bridge_contract.py pass
✓ python -c "from app.bridge_api import BridgeApi" pass (pytest pythonpath=src)
✓ validate_app_snapshot rejects unbounded row arrays
✓ validateSelectionScope rejects empty explicit_rows and empty current_query
✓ mockBridge and createPywebviewBridge() expose the same NovelGuardBridge methods
✓ approved spec: single AppSnapshot interface, single fileListSummary block
```

---

### Task 1: Vitest setup

**Files:**
- Modify: `web/package.json`
- Modify: `web/vite.config.ts`
- [ ] **Step 1: Add devDependency and scripts**

In `web/package.json`, add to `devDependencies`:

```json
"vitest": "^3.2.4"
```

Add scripts:

```json
"test": "vitest run",
"test:contracts": "vitest run src/contracts src/types/selection.test.ts src/bridge/bridgeParity.test.ts"
```

- [ ] **Step 2: Extend Vite config for Vitest**

Replace `web/vite.config.ts` with:

```typescript
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  base: "./",
  plugins: [react(), tailwindcss()],
  server: { port: 5173 },
  build: { outDir: "dist" },
  test: {
    environment: "node",
    include: ["src/**/*.test.ts"],
  },
});
```

- [ ] **Step 3: Install and smoke-run**

Run:

```bash
cd web
npm install
npx vitest run --passWithNoTests
```

Expected: exit 0 (no tests yet).

- [ ] **Step 4: Commit**

```bash
git add web/package.json web/package-lock.json web/vite.config.ts
git commit -m "[web] add Vitest for PR-10 contract tests"
```

---

### Task 2: Shared TS fixtures

**Files:**
- Create: `web/src/contracts/fixtures.ts`

- [ ] **Step 1: Create fixtures module**

Create `web/src/contracts/fixtures.ts`:

```typescript
import type { AppSnapshot } from "../types/snapshot";
import type { ReviewRowsPage } from "../types/review";
import type { QualityRowsPage } from "../types/quality";
import type { SelectionScope } from "../types/selection";

export const validAppSnapshot: AppSnapshot = {
  route: "work",
  theme: "dark",
  locale: "ko-KR",
  connection: "test",
  library: {
    folderPath: "/tmp",
    fileCount: 1,
    totalBytes: 100,
    duplicateGroups: 0,
    integrityIssues: 0,
    lastRun: null,
    scanOptions: [],
  },
  pipeline: {
    phase: "idle",
    percent: 0,
    label: "idle",
    cancellable: false,
  },
  work: {
    activeMode: "resolve",
    scan: { state: "empty", lastRun: null },
    resolve: {
      queueCount: 0,
      groupCount: 0,
      conflictCount: 0,
      approvedCount: 0,
      hasPendingApply: false,
    },
    quality: {
      integrityIssueCount: 0,
      encodingIssueCount: 0,
      smallFileAnomalyCount: 0,
    },
  },
  fileListSummary: {
    totalCount: 1,
    filteredCount: 1,
    issueCount: 0,
    selectedCount: 0,
  },
};

export const validReviewRowsPage: ReviewRowsPage = {
  rows: [
    {
      id: "r1",
      rowKind: "file",
      status: "unreviewed",
      type: "exact",
      name: "a.txt",
      proposedAction: "keep",
      hasChildren: false,
    },
  ],
  pageInfo: {
    cursor: null,
    nextCursor: null,
    hasMore: false,
    totalFiltered: 1,
  },
  summary: {
    selectedCount: 0,
    conflictCount: 0,
    unreviewedCount: 1,
    approvedCount: 0,
  },
};

export const validQualityRowsPage: QualityRowsPage = {
  rows: [],
  pageInfo: {
    cursor: null,
    nextCursor: null,
    hasMore: false,
    totalFiltered: 0,
  },
  summary: { issueCount: 0, warningCount: 0, errorCount: 0 },
};

export const explicitRowsSelection: SelectionScope = {
  type: "explicit_rows",
  rowIds: ["r1"],
};

export const currentQuerySelection: SelectionScope = {
  type: "current_query",
  query: { viewMode: "action" },
  excludeRowIds: [],
};
```

- [ ] **Step 2: Commit**

```bash
git add web/src/contracts/fixtures.ts
git commit -m "[web] add contract test fixtures"
```

---

### Task 3: `snapshotContract` (TDD)

**Files:**
- Create: `web/src/contracts/snapshotContract.test.ts`
- Create: `web/src/contracts/snapshotContract.ts`

- [ ] **Step 1: Write failing tests**

Create `web/src/contracts/snapshotContract.test.ts`:

```typescript
import { describe, expect, it } from "vitest";
import { validAppSnapshot } from "./fixtures";
import { SnapshotContractError, validateAppSnapshot } from "./snapshotContract";

describe("validateAppSnapshot", () => {
  it("accepts a valid snapshot", () => {
    expect(() => validateAppSnapshot(validAppSnapshot)).not.toThrow();
  });

  it.each([
    "fileList",
    "reviewRows",
    "rows",
    "reviewRowsPage",
    "fileRows",
  ])("rejects forbidden array key %s", (key) => {
    const bad = { ...validAppSnapshot, [key]: [{ id: "x" }] };
    expect(() => validateAppSnapshot(bad)).toThrow(SnapshotContractError);
  });

  it("rejects duplicate fileListSummary keys at top level", () => {
    const bad = {
      ...validAppSnapshot,
      fileListSummary: validAppSnapshot.fileListSummary,
      fileList: [],
    };
    expect(() => validateAppSnapshot(bad)).toThrow(SnapshotContractError);
  });
});
```

- [ ] **Step 2: Run tests — expect FAIL**

```bash
cd web
npm run test:contracts -- src/contracts/snapshotContract.test.ts
```

Expected: FAIL — module `snapshotContract` not found.

- [ ] **Step 3: Implement `snapshotContract.ts`**

Create `web/src/contracts/snapshotContract.ts`:

```typescript
import type { AppSnapshot } from "../types/snapshot";

export const FORBIDDEN_SNAPSHOT_ARRAY_KEYS = [
  "fileList",
  "reviewRows",
  "rows",
  "reviewRowsPage",
  "fileRows",
] as const;

export class SnapshotContractError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "SnapshotContractError";
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function assertRequiredFields(snapshot: Record<string, unknown>): void {
  const required = [
    "route",
    "theme",
    "locale",
    "connection",
    "library",
    "pipeline",
    "work",
    "fileListSummary",
  ];
  for (const key of required) {
    if (!(key in snapshot)) {
      throw new SnapshotContractError(`AppSnapshot missing required field: ${key}`);
    }
  }
  if (!isRecord(snapshot.library) || !isRecord(snapshot.pipeline) || !isRecord(snapshot.work)) {
    throw new SnapshotContractError("AppSnapshot nested objects invalid");
  }
  if (!isRecord(snapshot.fileListSummary)) {
    throw new SnapshotContractError("AppSnapshot.fileListSummary must be an object");
  }
}

/** Runtime guard: no unbounded row arrays on snapshot payloads. */
export function validateAppSnapshot(snapshot: unknown): asserts snapshot is AppSnapshot {
  if (!isRecord(snapshot)) {
    throw new SnapshotContractError("AppSnapshot must be an object");
  }
  assertRequiredFields(snapshot);

  for (const key of FORBIDDEN_SNAPSHOT_ARRAY_KEYS) {
    if (key in snapshot && Array.isArray(snapshot[key])) {
      throw new SnapshotContractError(`AppSnapshot must not contain array field: ${key}`);
    }
  }
}
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
cd web
npm run test:contracts -- src/contracts/snapshotContract.test.ts
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add web/src/contracts/snapshotContract.ts web/src/contracts/snapshotContract.test.ts
git commit -m "[web] add AppSnapshot contract validator"
```

---

### Task 4: `reviewPageContract` (TDD)

**Files:**
- Create: `web/src/contracts/reviewPageContract.test.ts`
- Create: `web/src/contracts/reviewPageContract.ts`

- [ ] **Step 1: Write failing tests**

Create `web/src/contracts/reviewPageContract.test.ts`:

```typescript
import { describe, expect, it } from "vitest";
import { validReviewRowsPage } from "./fixtures";
import { PageContractError, clampQueryLimit, validateReviewRowsPage } from "./reviewPageContract";

describe("validateReviewRowsPage", () => {
  it("accepts valid page", () => {
    expect(() => validateReviewRowsPage(validReviewRowsPage)).not.toThrow();
  });

  it("rejects page with more than 200 rows", () => {
    const rows = Array.from({ length: 201 }, (_, i) => ({
      ...validReviewRowsPage.rows[0],
      id: `r${i}`,
    }));
    const bad = { ...validReviewRowsPage, rows };
    expect(() => validateReviewRowsPage(bad)).toThrow(PageContractError);
  });
});

describe("clampQueryLimit", () => {
  it("defaults to 100", () => {
    expect(clampQueryLimit({ viewMode: "action" })).toBe(100);
  });

  it("clamps to 200 max", () => {
    expect(clampQueryLimit({ viewMode: "action", limit: 999 })).toBe(200);
  });
});
```

- [ ] **Step 2: Run — expect FAIL**

```bash
cd web
npm run test:contracts -- src/contracts/reviewPageContract.test.ts
```

- [ ] **Step 3: Implement `reviewPageContract.ts`**

```typescript
import type { ReviewRowsPage, ReviewRowsQuery } from "../types/review";

export const MAX_QUERY_LIMIT = 200;
export const DEFAULT_QUERY_LIMIT = 100;

export class PageContractError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "PageContractError";
  }
}

export function clampQueryLimit(query: ReviewRowsQuery): number {
  const raw = query.limit ?? DEFAULT_QUERY_LIMIT;
  return Math.min(Math.max(1, raw), MAX_QUERY_LIMIT);
}

export function validateReviewRowsPage(page: unknown): asserts page is ReviewRowsPage {
  if (typeof page !== "object" || page === null) {
    throw new PageContractError("ReviewRowsPage must be an object");
  }
  const p = page as ReviewRowsPage;
  if (!Array.isArray(p.rows)) {
    throw new PageContractError("ReviewRowsPage.rows must be an array");
  }
  if (p.rows.length > MAX_QUERY_LIMIT) {
    throw new PageContractError(`ReviewRowsPage.rows exceeds limit ${MAX_QUERY_LIMIT}`);
  }
  if (!p.pageInfo || typeof p.pageInfo.totalFiltered !== "number") {
    throw new PageContractError("ReviewRowsPage.pageInfo invalid");
  }
  if (!p.summary || typeof p.summary.unreviewedCount !== "number") {
    throw new PageContractError("ReviewRowsPage.summary invalid");
  }
}
```

- [ ] **Step 4: Run — expect PASS**

- [ ] **Step 5: Commit**

```bash
git commit -m "[web] add ReviewRowsPage contract validator"
```

---

### Task 5: `qualityPageContract` (TDD)

**Files:**
- Create: `web/src/contracts/qualityPageContract.test.ts`
- Create: `web/src/contracts/qualityPageContract.ts`

- [ ] **Step 1: Write failing tests**

```typescript
import { describe, expect, it } from "vitest";
import { validQualityRowsPage } from "./fixtures";
import { PageContractError, validateQualityRowsPage } from "./qualityPageContract";

describe("validateQualityRowsPage", () => {
  it("accepts valid page", () => {
    expect(() => validateQualityRowsPage(validQualityRowsPage)).not.toThrow();
  });

  it("rejects more than 200 rows", () => {
    const rows = Array.from({ length: 201 }, (_, i) => ({
      id: `q${i}`,
      issueType: "integrity" as const,
      name: "x",
      integrity: "ok",
      severity: "warning" as const,
    }));
    expect(() => validateQualityRowsPage({ ...validQualityRowsPage, rows })).toThrow(
      PageContractError,
    );
  });
});
```

- [ ] **Step 2: Implement `qualityPageContract.ts`**

Reuse `PageContractError` and `MAX_QUERY_LIMIT` from `reviewPageContract.ts`:

```typescript
import type { QualityRowsPage } from "../types/quality";
import { MAX_QUERY_LIMIT, PageContractError } from "./reviewPageContract";

export function validateQualityRowsPage(page: unknown): asserts page is QualityRowsPage {
  if (typeof page !== "object" || page === null) {
    throw new PageContractError("QualityRowsPage must be an object");
  }
  const p = page as QualityRowsPage;
  if (!Array.isArray(p.rows) || p.rows.length > MAX_QUERY_LIMIT) {
    throw new PageContractError(`QualityRowsPage.rows invalid or exceeds ${MAX_QUERY_LIMIT}`);
  }
  if (!p.pageInfo || !p.summary) {
    throw new PageContractError("QualityRowsPage.pageInfo or summary invalid");
  }
}
```

- [ ] **Step 3: Run tests — PASS**

- [ ] **Step 4: Commit**

---

### Task 6: `bridgeParity` + tests

**Files:**
- Create: `web/src/contracts/bridgeParity.ts`
- Create: `web/src/bridge/bridgeParity.test.ts`

- [ ] **Step 1: Write failing parity test**

Create `web/src/bridge/bridgeParity.test.ts`:

```typescript
import { describe, expect, it } from "vitest";
import { mockBridge } from "./mockBridge";
import { createPywebviewBridge } from "./pywebviewBridge";
import {
  NOVEL_GUARD_BRIDGE_METHODS,
  PYWEBVIEW_API_METHODS,
  assertBridgeParity,
} from "../contracts/bridgeParity";

describe("bridge parity", () => {
  it("mockBridge implements all NovelGuardBridge methods", () => {
    assertBridgeParity(mockBridge);
  });

  it("pywebview adapter implements all NovelGuardBridge methods", () => {
    const fakeApi = Object.fromEntries(
      PYWEBVIEW_API_METHODS.map((m) => [m, async () => ({})]),
    );
    const w = globalThis as unknown as { window?: { pywebview?: { api?: unknown } } };
    const prev = w.window;
    w.window = {
      pywebview: { api: fakeApi },
    };
    try {
      assertBridgeParity(createPywebviewBridge());
    } finally {
      w.window = prev;
    }
  });

  it("exports stable method list", () => {
    expect(NOVEL_GUARD_BRIDGE_METHODS).toContain("getSnapshot");
    expect(NOVEL_GUARD_BRIDGE_METHODS).toContain("applyResolvedActions");
    expect(PYWEBVIEW_API_METHODS).toContain("get_snapshot");
  });
});
```

- [ ] **Step 2: Implement `bridgeParity.ts`**

```typescript
import type { NovelGuardBridge } from "../bridge/NovelGuardBridge";

export const NOVEL_GUARD_BRIDGE_METHODS = [
  "getSnapshot",
  "selectFolder",
  "startScan",
  "cancelRun",
  "setWorkMode",
  "queryReviewRows",
  "queryQualityRows",
  "getDuplicateGroupDetail",
  "getQualityIssueDetail",
  "getMovePreview",
  "applyResolvedActions",
] as const satisfies readonly (keyof NovelGuardBridge)[];

export const PYWEBVIEW_API_METHODS = [
  "get_snapshot",
  "select_folder",
  "start_scan",
  "cancel_run",
  "set_work_mode",
  "query_review_rows",
  "query_quality_rows",
  "get_duplicate_group_detail",
  "get_quality_issue_detail",
  "get_move_preview",
  "apply_resolved_actions",
] as const;

export function assertBridgeParity(bridge: NovelGuardBridge): void {
  for (const method of NOVEL_GUARD_BRIDGE_METHODS) {
    if (typeof bridge[method] !== "function") {
      throw new Error(`Bridge missing method: ${method}`);
    }
  }
}
```

- [ ] **Step 3: Run — PASS**

- [ ] **Step 4: Commit**

---

### Task 7: `selection` contract tests

**Files:**
- Create: `web/src/types/selection.test.ts`

- [ ] **Step 1: Write tests**

```typescript
import { describe, expect, it } from "vitest";
import {
  EmptySelectionError,
  InvalidSelectionScopeError,
  validateSelectionScope,
} from "./selection";
import { currentQuerySelection, explicitRowsSelection } from "../contracts/fixtures";

describe("validateSelectionScope", () => {
  it("accepts explicit_rows with ids", () => {
    expect(() => validateSelectionScope(explicitRowsSelection)).not.toThrow();
  });

  it("rejects empty explicit_rows", () => {
    expect(() =>
      validateSelectionScope({ type: "explicit_rows", rowIds: [] }),
    ).toThrow(EmptySelectionError);
  });

  it("rejects current_query without viewMode", () => {
    expect(() =>
      validateSelectionScope({
        type: "current_query",
        query: {} as { viewMode: "action" },
        excludeRowIds: [],
      }),
    ).toThrow(InvalidSelectionScopeError);
  });

  it("rejects empty current_query when resolver returns 0", () => {
    expect(() =>
      validateSelectionScope(currentQuerySelection, () => 0),
    ).toThrow(EmptySelectionError);
  });

  it("accepts current_query when resolver returns > 0", () => {
    expect(() =>
      validateSelectionScope(currentQuerySelection, () => 5),
    ).not.toThrow();
  });

  it("supports excludeRowIds on current_query", () => {
    const scope = {
      type: "current_query" as const,
      query: { viewMode: "action" as const },
      excludeRowIds: ["r99"],
    };
    expect(() => validateSelectionScope(scope, (_q, exclude) => {
      expect(exclude).toEqual(["r99"]);
      return 1;
    })).not.toThrow();
  });
});
```

- [ ] **Step 2: Run — PASS** (implementation already in `selection.ts`)

- [ ] **Step 3: Commit**

---

### Task 8: Wire `mockBridge` to use `clampQueryLimit`

**Files:**
- Modify: `web/src/bridge/mockBridge.ts`

- [ ] **Step 1: Import clamp from contract**

At top of `mockBridge.ts`, add:

```typescript
import { clampQueryLimit } from "../contracts/reviewPageContract";
```

Replace inline `Math.min(query.limit ?? 100, 200)` in `queryReviewRows` and `queryQualityRows` with:

```typescript
const limit = clampQueryLimit(query);
```

(and for quality, pass a synthetic query shape or duplicate a small `clampQualityLimit` that uses same MAX — simplest: import `MAX_QUERY_LIMIT` and use `Math.min(query.limit ?? 100, MAX_QUERY_LIMIT)` in quality only, or add `clampQualityLimit` mirroring review).

Preferred: add to `qualityPageContract.ts`:

```typescript
import type { QualityRowsQuery } from "../types/quality";
import { DEFAULT_QUERY_LIMIT, MAX_QUERY_LIMIT } from "./reviewPageContract";

export function clampQualityQueryLimit(query: QualityRowsQuery): number {
  const raw = query.limit ?? DEFAULT_QUERY_LIMIT;
  return Math.min(Math.max(1, raw), MAX_QUERY_LIMIT);
}
```

Use in `mockBridge.queryQualityRows`.

- [ ] **Step 2: Verify build**

```bash
cd web
npm run build
```

Expected: PASS (contracts exist).

- [ ] **Step 3: Run all contract tests**

```bash
npm run test:contracts
```

- [ ] **Step 4: Commit**

---

### Task 9: Python `bridge_contract` (TDD)

**Files:**
- Create: `tests/__init__.py` (empty)
- Create: `tests/fixtures/__init__.py` (empty)
- Create: `tests/fixtures/bridge_contract_fixtures.py`
- Create: `tests/test_bridge_contract.py`
- Create: `src/app/bridge_contract.py`

- [ ] **Step 1: Write failing pytest**

Create empty `tests/__init__.py` and `tests/fixtures/__init__.py` so `from tests.fixtures...` imports work.

Create `tests/fixtures/bridge_contract_fixtures.py`:

```python
from __future__ import annotations

from typing import Any

VALID_SNAPSHOT: dict[str, Any] = {
    "route": "work",
    "theme": "dark",
    "locale": "ko-KR",
    "connection": "test",
    "library": {
        "folderPath": "/tmp",
        "fileCount": 1,
        "totalBytes": 100,
        "duplicateGroups": 0,
        "integrityIssues": 0,
        "lastRun": None,
        "scanOptions": [],
    },
    "pipeline": {
        "phase": "idle",
        "percent": 0,
        "label": "idle",
        "cancellable": False,
    },
    "work": {
        "activeMode": "resolve",
        "scan": {"state": "empty", "lastRun": None},
        "resolve": {
            "queueCount": 0,
            "groupCount": 0,
            "conflictCount": 0,
            "approvedCount": 0,
            "hasPendingApply": False,
        },
        "quality": {
            "integrityIssueCount": 0,
            "encodingIssueCount": 0,
            "smallFileAnomalyCount": 0,
        },
    },
    "fileListSummary": {
        "totalCount": 1,
        "filteredCount": 1,
        "issueCount": 0,
        "selectedCount": 0,
    },
}
```

Create `tests/test_bridge_contract.py`:

```python
from __future__ import annotations

import pytest

from app.bridge_api import BridgeApi
from app.bridge_contract import (
    EmptySelectionError,
    InvalidSelectionScopeError,
    SnapshotContractError,
    clamp_query_limit,
    validate_app_snapshot,
    validate_selection_scope,
)
from tests.fixtures.bridge_contract_fixtures import VALID_SNAPSHOT


@pytest.mark.parametrize(
    "forbidden_key",
    ["fileList", "reviewRows", "rows", "reviewRowsPage", "fileRows"],
)
def test_validate_app_snapshot_rejects_forbidden_arrays(forbidden_key: str) -> None:
    bad = {**VALID_SNAPSHOT, forbidden_key: [{"id": "x"}]}
    with pytest.raises(SnapshotContractError):
        validate_app_snapshot(bad)


def test_validate_app_snapshot_accepts_valid() -> None:
    validate_app_snapshot(VALID_SNAPSHOT)


def test_empty_explicit_rows_rejected() -> None:
    with pytest.raises(EmptySelectionError):
        validate_selection_scope({"type": "explicit_rows", "rowIds": []})


def test_current_query_requires_view_mode() -> None:
    with pytest.raises(InvalidSelectionScopeError):
        validate_selection_scope(
            {"type": "current_query", "query": {}, "excludeRowIds": []}
        )


def test_clamp_query_limit_max_200() -> None:
    assert clamp_query_limit({"viewMode": "action", "limit": 999}) == 200


def test_bridge_api_get_snapshot_valid() -> None:
    api = BridgeApi()
    snap = api.get_snapshot()
    validate_app_snapshot(snap)


def test_bridge_api_query_review_rows_valid() -> None:
    api = BridgeApi()
    page = api.query_review_rows({"viewMode": "action", "limit": 50})
    assert len(page["rows"]) <= 200


def test_bridge_api_get_move_preview_requires_selection() -> None:
    api = BridgeApi()
    preview = api.get_move_preview(
        {"type": "explicit_rows", "rowIds": ["row-1"]}
    )
    assert "rows" in preview
```

- [ ] **Step 2: Run — expect FAIL**

```bash
pytest tests/test_bridge_contract.py -v
```

Expected: `ModuleNotFoundError: app.bridge_contract`

- [ ] **Step 3: Implement `src/app/bridge_contract.py`**

```python
"""Runtime bridge DTO validators (mirror web/src/contracts)."""

from __future__ import annotations

from typing import Any

FORBIDDEN_SNAPSHOT_ARRAY_KEYS = (
    "fileList",
    "reviewRows",
    "rows",
    "reviewRowsPage",
    "fileRows",
)

MAX_QUERY_LIMIT = 200
DEFAULT_QUERY_LIMIT = 100


class SnapshotContractError(ValueError):
    pass


class PageContractError(ValueError):
    pass


class EmptySelectionError(ValueError):
    pass


class InvalidSelectionScopeError(ValueError):
    pass


def validate_app_snapshot(snapshot: Any) -> None:
    if not isinstance(snapshot, dict):
        raise SnapshotContractError("AppSnapshot must be a dict")
    for key in (
        "route",
        "theme",
        "locale",
        "connection",
        "library",
        "pipeline",
        "work",
        "fileListSummary",
    ):
        if key not in snapshot:
            raise SnapshotContractError(f"AppSnapshot missing required field: {key}")
    for forbidden in FORBIDDEN_SNAPSHOT_ARRAY_KEYS:
        if forbidden in snapshot and isinstance(snapshot[forbidden], list):
            raise SnapshotContractError(
                f"AppSnapshot must not contain array field: {forbidden}"
            )


def clamp_query_limit(query: dict[str, Any]) -> int:
    raw = int(query.get("limit") or DEFAULT_QUERY_LIMIT)
    return min(max(1, raw), MAX_QUERY_LIMIT)


def validate_review_rows_page(page: Any) -> None:
    if not isinstance(page, dict):
        raise PageContractError("ReviewRowsPage must be a dict")
    rows = page.get("rows")
    if not isinstance(rows, list) or len(rows) > MAX_QUERY_LIMIT:
        raise PageContractError("ReviewRowsPage.rows invalid or exceeds limit")
    if not isinstance(page.get("pageInfo"), dict) or not isinstance(page.get("summary"), dict):
        raise PageContractError("ReviewRowsPage.pageInfo or summary invalid")


def validate_quality_rows_page(page: Any) -> None:
    if not isinstance(page, dict):
        raise PageContractError("QualityRowsPage must be a dict")
    rows = page.get("rows")
    if not isinstance(rows, list) or len(rows) > MAX_QUERY_LIMIT:
        raise PageContractError("QualityRowsPage.rows invalid or exceeds limit")


def validate_move_preview(payload: Any) -> None:
    if not isinstance(payload, dict) or not isinstance(payload.get("rows"), list):
        raise PageContractError("Move preview must include rows array")


def validate_selection_scope(selection: Any) -> None:
    if not isinstance(selection, dict):
        raise InvalidSelectionScopeError("SelectionScope must be a dict")
    scope_type = selection.get("type")
    if scope_type == "explicit_rows":
        row_ids = selection.get("rowIds")
        if not isinstance(row_ids, list) or len(row_ids) == 0:
            raise EmptySelectionError()
        return
    if scope_type == "current_query":
        query = selection.get("query")
        if not isinstance(query, dict) or not query.get("viewMode"):
            raise InvalidSelectionScopeError(
                "current_query requires a ReviewRowsQuery with viewMode"
            )
        if not isinstance(selection.get("excludeRowIds"), list):
            raise InvalidSelectionScopeError("excludeRowIds must be an array")
        return
    raise InvalidSelectionScopeError(f"Unknown SelectionScope type: {scope_type}")
```

- [ ] **Step 4: Run pytest — PASS**

```bash
pytest tests/test_bridge_contract.py -v
```

- [ ] **Step 5: Commit**

```bash
git add src/app/bridge_contract.py tests/test_bridge_contract.py tests/fixtures/bridge_contract_fixtures.py
git commit -m "[app] add bridge contract validators and tests"
```

---

### Task 10: Spec audit + docs

**Files:**
- Modify: `docs/superpowers/specs/2026-06-01-novelguard-ui-overhaul-design.md` (changelog only)
- Modify: `docs/entry_points.md`

- [ ] **Step 1: Verify spec has single `AppSnapshot`**

Run:

```bash
rg "interface AppSnapshot" docs/superpowers/specs/2026-06-01-novelguard-ui-overhaul-design.md
```

Expected: **one** match.

- [ ] **Step 2: Add changelog line to spec**

Under spec changelog table, add:

```markdown
| 2026-06-01 | PR-10 contract audit: validators + tests; forbidden snapshot arrays enforced |
```

- [ ] **Step 3: Add contract test commands to `docs/entry_points.md`**

After Verification section, append:

```markdown
## Contract tests (PR-10)

```bash
cd web && npm run test:contracts
pytest tests/test_bridge_contract.py -v
```
```

- [ ] **Step 4: Commit**

```bash
git commit -m "[docs] PR-10 contract audit verification notes"
```

---

### Task 11: Full verification

- [ ] **Step 1: Web**

```bash
cd web
npm run lint
npm run build
npm run test:contracts
```

Expected: lint PASS; build PASS; all Vitest PASS.

- [ ] **Step 2: Python gate**

```bash
pip install -e ".[dev]"
python scripts/verify_phase_completion.py
```

Expected: pytest includes new bridge tests; ruff/mypy/black pass.

- [ ] **Step 3: Import smoke**

```bash
python -c "from app.bridge_api import BridgeApi; BridgeApi().get_snapshot()"
```

(with repo root + `pythonpath=src` via pytest.ini or `PYTHONPATH=src`)

- [ ] **Step 4: Final commit if formatting changed**

```bash
git status
# if black modified files:
git add -u && git commit -m "[app] format after PR-10 verification"
```

---

## Spec coverage self-review

| Spec requirement | Plan task |
|------------------|-----------|
| AppSnapshot summaries only, no row arrays | Task 3, 9 |
| `queryReviewRows` / `ReviewRowsPage` | Task 4, 9 |
| `queryQualityRows` / `QualityRowsPage` | Task 5, 9 |
| `limit` max 200 | Task 4, 5, 8, 9 |
| `SelectionScope` + empty reject | Task 7, 9 |
| `getMovePreview` / `applyResolvedActions` accept SelectionScope | Task 9 (shape); no preview-token logic |
| mock + pywebview same bridge surface | Task 6 |
| No new UI | Non-goals |
| Destructive preview→confirm→apply | Not implemented in PR-10 (PR-13) |
| Single AppSnapshot in spec | Task 10 |

**Gaps intentionally deferred:** Playwright (PR-11), perf benchmark (PR-12), apply invariants (PR-13), packaging (PR-14).

---

## Plan changelog

| Date | Note |
|------|------|
| 2026-06-01 | Initial PR-10 plan; TEST_ALLOWED Python + TS; Plan style A |

---

## Execution handoff

Plan complete and saved to `docs/superpowers/plans/2026-06-01-novelguard-ui-contract-hardening.md`.

**Two execution options:**

1. **Subagent-Driven (recommended)** — fresh subagent per task, spec compliance review then code quality review between tasks (`subagent-driven-development`).

2. **Inline Execution** — run tasks in this session with checkpoints (`executing-plans`).

Which approach?
