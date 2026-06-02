import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import {
  BRIDGE_ERROR_CODES,
  BridgeUnavailableError,
} from "./bridgeErrors";
import { resolveBridge } from "./bridgeFactory";
import { mockBridge } from "./mockBridge";
import { getAllReviewRows } from "./mockData";
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
});
