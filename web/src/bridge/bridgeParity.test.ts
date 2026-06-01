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
    assertBridgeParity(createPywebviewBridge(fakeApi));
  });

  it("exports stable method list", () => {
    expect(NOVEL_GUARD_BRIDGE_METHODS).toContain("getSnapshot");
    expect(NOVEL_GUARD_BRIDGE_METHODS).toContain("applyResolvedActions");
    expect(NOVEL_GUARD_BRIDGE_METHODS).toContain("discardMovePreview");
    expect(PYWEBVIEW_API_METHODS).toContain("get_snapshot");
    expect(PYWEBVIEW_API_METHODS).toContain("discard_move_preview");
    expect(PYWEBVIEW_API_METHODS.length).toBe(NOVEL_GUARD_BRIDGE_METHODS.length);
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
});
