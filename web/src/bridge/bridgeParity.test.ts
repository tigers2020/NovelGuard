import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { afterEach, describe, expect, it, vi } from "vitest";
import { createInvalidationScheduler } from "./snapshotInvalidationSchedule";
import {
  BRIDGE_ERROR_CODES,
  BridgeUnavailableError,
} from "./bridgeErrors";
import { resolveBridge, resolveBridgeAsync } from "./bridgeFactory";
import { PYWEBVIEW_READY_EVENT } from "./waitForPywebviewApi";
import { bumpLibraryRevisionForTest, mockBridge } from "./mockBridge";
import { textSortKey } from "./mockFileRows";
import { getAllReviewRows, sortQualityRows } from "./mockData";
import { reviewRowGroupId } from "../types/review";
import { createPywebviewBridge } from "./pywebviewBridge";
import {
  NOVEL_GUARD_BRIDGE_METHODS,
  PYWEBVIEW_API_METHODS,
  assertBridgeParity,
} from "../contracts/bridgeParity";

const webRoot = join(dirname(fileURLToPath(import.meta.url)), "..");

describe("bridge parity", () => {
  it("mockBridge implements all NovelGuardBridge methods", () => {
    assertBridgeParity(mockBridge);
  });

  it("pywebview adapter implements all NovelGuardBridge methods", () => {
    const fakeApi = Object.fromEntries(
      PYWEBVIEW_API_METHODS.map((m) => [m, async () => ({})]),
    );
    assertBridgeParity(createPywebviewBridge(fakeApi));
  });

  it("exports stable method list", () => {
    expect(NOVEL_GUARD_BRIDGE_METHODS).toContain("getAppInfo");
    expect(NOVEL_GUARD_BRIDGE_METHODS).toContain("getSnapshot");
    expect(NOVEL_GUARD_BRIDGE_METHODS).toContain("queryQualityRows");
    expect(NOVEL_GUARD_BRIDGE_METHODS).toContain("applyResolvedActions");
    expect(NOVEL_GUARD_BRIDGE_METHODS).toContain("discardMovePreview");
    expect(PYWEBVIEW_API_METHODS).toContain("get_app_info");
    expect(PYWEBVIEW_API_METHODS).toContain("get_snapshot");
    expect(PYWEBVIEW_API_METHODS).toContain("query_file_rows");
    expect(PYWEBVIEW_API_METHODS).toContain("query_quality_rows");
    expect(PYWEBVIEW_API_METHODS).toContain("discard_move_preview");
    expect(PYWEBVIEW_API_METHODS).toContain("update_review_decisions");
    expect(PYWEBVIEW_API_METHODS.length).toBe(NOVEL_GUARD_BRIDGE_METHODS.length);
  });

  it("QualityWorkspace does not import mockData or buildQualityRows", () => {
    const src = readFileSync(join(webRoot, "features/work/QualityWorkspace.tsx"), "utf8");
    expect(src).not.toMatch(/mockData/);
    expect(src).not.toMatch(/buildQualityRows/);
    expect(src).toMatch(/bridge\.queryQualityRows/);
  });

  it("pywebviewBridge does not import or call mockBridge", () => {
    const src = readFileSync(join(webRoot, "bridge/pywebviewBridge.ts"), "utf8");
    expect(src).not.toMatch(/import\s+.*mockBridge/);
    expect(src).not.toMatch(/\bmockBridge\s*\(/);
  });

  it("resolveBridge in PROD without pywebview throws PRODUCTION_BRIDGE_UNAVAILABLE", () => {
    expect(() =>
      resolveBridge({ PROD: true, DEV: false }, {}),
    ).toThrowError(
      new BridgeUnavailableError(BRIDGE_ERROR_CODES.productionUnavailable),
    );
  });

  it("resolveBridgeAsync in PROD waits for pywebviewready before resolving", async () => {
    const fakeApi = Object.fromEntries(
      PYWEBVIEW_API_METHODS.map((m) => [m, async () => ({})]),
    );
    const win: { pywebview?: { api?: typeof fakeApi } } = {};
    const listeners = new Map<string, Set<() => void>>();
    const eventTarget = {
      addEventListener(event: string, listener: () => void) {
        const set = listeners.get(event) ?? new Set();
        set.add(listener);
        listeners.set(event, set);
      },
      removeEventListener(event: string, listener: () => void) {
        listeners.get(event)?.delete(listener);
      },
      dispatchEvent() {
        return true;
      },
    };

    const pending = resolveBridgeAsync({ PROD: true, DEV: false }, win, eventTarget);

    await new Promise((r) => setTimeout(r, 20));
    win.pywebview = { api: fakeApi };
    listeners.get(PYWEBVIEW_READY_EVENT)?.forEach((listener) => listener());

    const { bridge, kind } = await pending;
    expect(kind).toBe("pywebview");
    expect(bridge.getSnapshot).toBeTypeOf("function");
  });

  it("resolveBridge in DEV without flag throws DEV_BRIDGE_UNAVAILABLE", () => {
    expect(() =>
      resolveBridge({ PROD: false, DEV: true, VITE_USE_MOCK_BRIDGE: "false" }, {}),
    ).toThrowError(new BridgeUnavailableError(BRIDGE_ERROR_CODES.devUnavailable));
  });

  it("resolveBridge in DEV with VITE_USE_MOCK_BRIDGE=true returns mockBridge", () => {
    const { bridge, kind } = resolveBridge(
      { PROD: false, DEV: true, VITE_USE_MOCK_BRIDGE: "true" },
      {},
    );
    expect(bridge).toBe(mockBridge);
    expect(kind).toBe("mock");
  });

  it("mockBridge returns empty page for unknown issueType", async () => {
    const page = await mockBridge.queryQualityRows({
      issueType: "near" as "integrity",
      limit: 10,
    });
    expect(page.rows).toEqual([]);
    expect(page.pageInfo.totalFiltered).toBe(0);
  });

  it("mockBridge queryQualityRows sorts by name asc", async () => {
    const page = await mockBridge.queryQualityRows({
      issueType: "encoding",
      limit: 50,
      sort: { field: "name", direction: "asc" },
    });
    const names = page.rows.map((row) => row.name);
    const sorted = [...names].sort((a, b) =>
      textSortKey(a).localeCompare(textSortKey(b), "en-US"),
    );
    expect(names).toEqual(sorted);
  });

  it("mockBridge queryQualityRows rejects invalid sort field", async () => {
    await expect(
      mockBridge.queryQualityRows({
        issueType: "encoding",
        sort: { field: "notAllowed", direction: "asc" },
      }),
    ).rejects.toMatchObject({ reason: "INVALID_SORT_FIELD" });
  });

  it("mockBridge queryQualityRows stable order for identical queries", async () => {
    const query = {
      issueType: "integrity" as const,
      limit: 20,
      sort: { field: "severity" as const, direction: "desc" as const },
    };
    const first = await mockBridge.queryQualityRows(query);
    const second = await mockBridge.queryQualityRows(query);
    expect(first.rows.map((row) => row.id)).toEqual(second.rows.map((row) => row.id));
  });

  it("sortQualityRows matches stable tie-break by id", () => {
    const rows = [
      {
        id: "quality:b",
        issueType: "small_file" as const,
        name: "same",
        severity: "warning" as const,
        encoding: "UTF-8",
        integrity: "Tiny",
      },
      {
        id: "quality:a",
        issueType: "small_file" as const,
        name: "same",
        severity: "warning" as const,
        encoding: "UTF-8",
        integrity: "Tiny",
      },
    ];
    const sorted = sortQualityRows(rows, { field: "name", direction: "asc" });
    expect(sorted.map((row) => row.id)).toEqual(["quality:b", "quality:a"]);
  });

  it("queryQualityRows rejects when pywebview api method is missing", async () => {
    const fakeApi = Object.fromEntries(
      PYWEBVIEW_API_METHODS.filter((m) => m !== "query_quality_rows").map((m) => [
        m,
        async () => ({}),
      ]),
    );
    const bridge = createPywebviewBridge(fakeApi);
    await expect(
      bridge.queryQualityRows({ issueType: "integrity", limit: 10 }),
    ).rejects.toMatchObject({ method: "query_quality_rows" });
  });

  it("apply without previewToken rejects MISSING_PREVIEW_TOKEN", async () => {
    await expect(
      mockBridge.applyResolvedActions({
        selection: { type: "explicit_rows", rowIds: ["row-1"] },
        previewToken: "",
      }),
    ).rejects.toMatchObject({
      reason: "MISSING_PREVIEW_TOKEN",
    });
  });

  it("apply after discard rejects NO_PENDING_APPLY", async () => {
    const sel = { type: "explicit_rows" as const, rowIds: ["row-1"] };
    const preview = await mockBridge.getMovePreview(sel);
    await mockBridge.discardMovePreview({ previewToken: preview.previewToken });
    await expect(mockBridge.applyResolvedActions({ selection: sel, previewToken: preview.previewToken })).rejects.toMatchObject({
      reason: "NO_PENDING_APPLY",
    });
  });

  it("getMovePreview returns token fields", async () => {
    const preview = await mockBridge.getMovePreview({
      type: "explicit_rows",
      rowIds: ["row-1"],
    });
    expect(preview.previewToken).toMatch(/^preview-/);
    expect(preview.hasPendingApply).toBe(true);
    expect(typeof preview.libraryRevision).toBe("number");
    expect(preview.selectionFingerprint).toMatch(/^[a-f0-9]{64}$/);
  });

  it("apply after library revision bump rejects STALE_PREVIEW", async () => {
    const sel = { type: "explicit_rows" as const, rowIds: ["row-1"] };
    const preview = await mockBridge.getMovePreview(sel);
    bumpLibraryRevisionForTest({ clearPending: false });
    await expect(
      mockBridge.applyResolvedActions({ selection: sel, previewToken: preview.previewToken }),
    ).rejects.toMatchObject({ reason: "STALE_PREVIEW" });
    const snap = await mockBridge.getSnapshot();
    expect(snap.work.resolve.hasPendingApply).toBe(false);
  });

  it("apply with changed selection rejects SELECTION_CHANGED", async () => {
    const preview = await mockBridge.getMovePreview({
      type: "explicit_rows",
      rowIds: ["row-1"],
    });
    await expect(
      mockBridge.applyResolvedActions({
        selection: { type: "explicit_rows", rowIds: ["row-2"] },
        previewToken: preview.previewToken,
      }),
    ).rejects.toMatchObject({ reason: "SELECTION_CHANGED" });
    const snap = await mockBridge.getSnapshot();
    expect(snap.work.resolve.hasPendingApply).toBe(false);
  });

  it("setWorkMode rejects finalize mode", async () => {
    await expect(mockBridge.setWorkMode("finalize")).rejects.toMatchObject({
      reason: "INVALID_WORK_MODE",
    });
    const snap = await mockBridge.getSnapshot();
    expect(snap.work.activeMode).toBe("resolve");
  });

  it("getMovePreview executable rows are move_duplicate only", async () => {
    const moveIds = getAllReviewRows()
      .filter((row) => row.rowKind === "file" && row.proposedAction === "move_duplicate")
      .slice(0, 5)
      .map((row) => row.id);
    const preview = await mockBridge.getMovePreview({
      type: "explicit_rows",
      rowIds: moveIds,
    });
    for (const row of preview.rows) {
      expect(row.action).toBe("move_duplicate");
    }
    expect(preview.summary.operationCount).toBe(moveIds.length);
  });

  it("textSortKey case-folds file-row search fixtures", () => {
    expect(textSortKey("File.TXT")).toBe(textSortKey("file.txt"));
    expect(textSortKey("café")).toBe(textSortKey("CAFÉ"));
    expect(textSortKey("토끼.txt")).toBe(textSortKey("토끼.txt"));
    expect(textSortKey(".Md")).toBe(textSortKey(".md"));
  });

  it("queryFileRows returns empty page shape when search matches nothing", async () => {
    const page = await mockBridge.queryFileRows({
      search: "__no_match_pr25__",
      cursor: null,
      limit: 50,
    });
    expect(page.rows).toEqual([]);
    expect(page.pageInfo.totalFiltered).toBe(0);
    expect(page.pageInfo.hasMore).toBe(false);
  });

  it("queryFileRows filters by name case-insensitively", async () => {
    const page = await mockBridge.queryFileRows({
      search: "토끼",
      cursor: null,
      limit: 100,
    });
    expect(page.rows.length).toBeGreaterThan(0);
    expect(page.pageInfo.totalFiltered).toBeGreaterThan(0);
    for (const row of page.rows) {
      expect(`${row.name} ${row.path}`.toLowerCase()).toContain("토끼");
    }
  });

  it("queryFileRows clamps limit to 500", async () => {
    const page = await mockBridge.queryFileRows({ cursor: null, limit: 999 });
    expect(page.rows.length).toBeLessThanOrEqual(500);
  });

  it("queryFileRows rejects invalid sort field", async () => {
    await expect(
      mockBridge.queryFileRows({
        cursor: null,
        sort: { field: "notAllowed" as "name", direction: "asc" },
      }),
    ).rejects.toMatchObject({ reason: "INVALID_SORT_FIELD" });
  });

  it("queryFileRows rejects invalid filter value", async () => {
    await expect(
      mockBridge.queryFileRows({
        cursor: null,
        filters: { duplicateGroup: "maybe" as "any" },
      }),
    ).rejects.toMatchObject({ reason: "INVALID_FILTER_VALUE" });
  });

  it("queryFileRows sort changes first row", async () => {
    const asc = await mockBridge.queryFileRows({
      cursor: null,
      limit: 5,
      sort: { field: "name", direction: "asc" },
    });
    const desc = await mockBridge.queryFileRows({
      cursor: null,
      limit: 5,
      sort: { field: "name", direction: "desc" },
    });
    expect(asc.rows[0]?.name).not.toBe(desc.rows[0]?.name);
  });
});

describe("logs and settings", () => {
  it("queryLogEntries filters by minimum severity inclusive", async () => {
    const page = await mockBridge.queryLogEntries({ level: "WARNING", limit: 50 });
    const messages = page.entries.map((entry) => entry.message);
    expect(messages).not.toContain("mock log seed debug");
    expect(messages).not.toContain("mock log seed info");
  });

  it("getAppSetting returns typed response", async () => {
    const payload = await mockBridge.getAppSetting("scan.includeHidden");
    expect(payload.key).toBe("scan.includeHidden");
    expect(typeof payload.value).toBe("boolean");
    expect(payload.source).toMatch(/default|persisted/);
  });
});

describe("snapshot invalidation", () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  it("coalesces scanProgress invalidations", () => {
    vi.useFakeTimers();
    const refreshes: number[] = [];
    const scheduler = createInvalidationScheduler({
      debounceMs: 200,
      onRefresh: () => {
        refreshes.push(1);
      },
    });
    for (let i = 1; i <= 5; i++) {
      scheduler.handle({
        type: "snapshotInvalidated",
        reason: "scanProgress",
        sequence: i,
      });
    }
    expect(refreshes).toHaveLength(0);
    vi.advanceTimersByTime(200);
    expect(refreshes).toHaveLength(1);
    scheduler.dispose();
  });

  it("immediate invalidation collapses pending debounce into one refresh", () => {
    vi.useFakeTimers();
    const refreshes: number[] = [];
    const scheduler = createInvalidationScheduler({
      debounceMs: 200,
      onRefresh: () => {
        refreshes.push(1);
        return Promise.resolve();
      },
    });
    scheduler.handle({
      type: "snapshotInvalidated",
      reason: "scanProgress",
      sequence: 1,
    });
    scheduler.handle({
      type: "snapshotInvalidated",
      reason: "libraryRevision",
      sequence: 2,
    });
    vi.advanceTimersByTime(0);
    expect(refreshes).toHaveLength(1);
    scheduler.dispose();
  });

  it("mockBridge getDuplicateGroupDetail returns ok for exact review row", async () => {
    const row = getAllReviewRows().find((candidate) => candidate.id === "row-2");
    expect(row?.type).toBe("exact");
    const groupId = reviewRowGroupId(row!);
    expect(groupId).toBe("group-02");
    if (!groupId) {
      throw new Error("expected exact review row to resolve a group id");
    }

    const detail = await mockBridge.getDuplicateGroupDetail(groupId);
    expect(detail.status).toBe("ok");
    if (detail.status === "ok" && detail.type === "exact") {
      expect(detail.type).toBe("exact");
      expect(detail.members.length).toBeGreaterThan(0);
      expect(detail.movePlan.targetFolder).toBeTruthy();
    }
  });

  it("mockBridge getDuplicateGroupDetail returns not_found for unknown group", async () => {
    const detail = await mockBridge.getDuplicateGroupDetail("group-unknown-999");
    expect(detail.status).toBe("not_found");
    expect(detail.members).toEqual([]);
  });

  it("mockBridge getDuplicateGroupDetail near row yields ok detail without move plan when typed near", async () => {
    const row = getAllReviewRows().find((candidate) => candidate.type === "near");
    expect(row).toBeDefined();
    const groupId = reviewRowGroupId(row!);
    expect(groupId).toBeTruthy();

    const detail = await mockBridge.getDuplicateGroupDetail(groupId!);
    expect(detail.status).toBe("ok");
    if (detail.status === "ok" && detail.type === "near") {
      expect(detail).not.toHaveProperty("movePlan");
      expect(detail.evidence.matchKind).toBe("near_ngram_v1");
    }
  });

  it("mockBridge getFinalizeSummary returns summary shape", async () => {
    const summary = await mockBridge.getFinalizeSummary();
    expect(summary).toHaveProperty("blockers");
    expect(summary).toHaveProperty("warnings");
    expect(Array.isArray(summary.blockers)).toBe(true);
    expect(Array.isArray(summary.warnings)).toBe(true);
  });

  it("mockBridge runFinalizeVerification returns report id and getFinalizeReport round-trips", async () => {
    const result = await mockBridge.runFinalizeVerification({ includeCleanup: false });
    expect(result.reportId).toBeTruthy();
    expect(["complete", "complete_with_warnings", "blocked"]).toContain(result.status);

    const report = await mockBridge.getFinalizeReport(result.reportId);
    expect(report.reportId).toBe(result.reportId);
    expect(report.summary).toBeDefined();
  });

  it("mockBridge getFinalizeReport rejects unknown report id", async () => {
    await expect(mockBridge.getFinalizeReport("missing-report-id")).rejects.toThrow();
  });

  it("mockBridge subscribe emits and unsubscribe stops delivery", async () => {
    vi.useFakeTimers();
    const seen: number[] = [];
    const unsub = mockBridge.subscribeSnapshotInvalidation((e) => {
      seen.push(e.sequence);
    });
    await mockBridge.startScan();
    vi.advanceTimersByTime(300);
    expect(seen.length).toBeGreaterThan(0);
    const last = seen.length;
    unsub();
    vi.advanceTimersByTime(1000);
    expect(seen.length).toBe(last);
    await mockBridge.cancelRun();
  });
});
