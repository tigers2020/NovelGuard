import { describe, expect, it } from "vitest";
import { BridgeCallError } from "./bridgeErrors";
import { callBridge } from "./callBridge";

describe("callBridge", () => {
  it("resolves successful promises", async () => {
    await expect(callBridge(() => Promise.resolve(42), { method: "test" })).resolves.toBe(42);
  });

  it("wraps rejection in BridgeCallError", async () => {
    await expect(
      callBridge(() => Promise.reject(new Error("boom")), { method: "get_snapshot", timeoutMs: 50 }),
    ).rejects.toBeInstanceOf(BridgeCallError);
  });

  it("maps PreviewApplyError reason from pywebview message", async () => {
    await expect(
      callBridge(() => Promise.reject(new Error("STALE_PREVIEW")), {
        method: "apply_resolved_actions",
        timeoutMs: 50,
      }),
    ).rejects.toMatchObject({ reason: "STALE_PREVIEW", code: "rejected" });
  });

  it("maps ApplyFailedError JSON payload with details", async () => {
    const payload = JSON.stringify({
      reason: "APPLY_FAILED",
      details: { partialSuccess: true, succeededCount: 2 },
    });
    await expect(
      callBridge(() => Promise.reject(new Error(payload)), {
        method: "apply_resolved_actions",
        timeoutMs: 50,
      }),
    ).rejects.toMatchObject({
      reason: "APPLY_FAILED",
      details: { partialSuccess: true, succeededCount: 2 },
    });
  });

  it("times out slow calls", async () => {
    await expect(
      callBridge(
        () => new Promise((resolve) => setTimeout(() => resolve(1), 500)),
        { method: "get_snapshot", timeoutMs: 30 },
      ),
    ).rejects.toMatchObject({ code: "timeout" });
  });
});
