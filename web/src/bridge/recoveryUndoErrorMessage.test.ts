import { describe, expect, it } from "vitest";
import { BridgeCallError } from "./bridgeErrors";
import { recoveryUndoErrorMessage } from "./recoveryUndoErrorMessage";

describe("recoveryUndoErrorMessage", () => {
  it("maps stale preview to re-preview guidance", () => {
    const err = new BridgeCallError("rejected", {
      code: "rejected",
      method: "execute_undo_plan",
      reason: "STALE_UNDO_PREVIEW",
    });
    const result = recoveryUndoErrorMessage(err);
    expect(result.requiresRepreview).toBe(true);
    expect(result.message).toContain("다시 미리보기");
  });

  it("maps invalid token to re-preview guidance", () => {
    const err = new BridgeCallError("rejected", {
      code: "rejected",
      method: "execute_undo_plan",
      reason: "INVALID_PREVIEW_TOKEN",
    });
    const result = recoveryUndoErrorMessage(err);
    expect(result.requiresRepreview).toBe(true);
    expect(result.message).toContain("다시 미리보기");
  });

  it("maps in-progress to deferred action", () => {
    const err = new BridgeCallError("rejected", {
      code: "rejected",
      method: "execute_undo_plan",
      reason: "UNDO_IN_PROGRESS",
    });
    const result = recoveryUndoErrorMessage(err);
    expect(result.actionDeferred).toBe(true);
    expect(result.requiresRepreview).toBe(false);
  });

  it("maps library busy to deferred action", () => {
    const err = new BridgeCallError("rejected", {
      code: "rejected",
      method: "preview_undo_plan",
      reason: "LIBRARY_BUSY",
    });
    const result = recoveryUndoErrorMessage(err);
    expect(result.actionDeferred).toBe(true);
  });
});
