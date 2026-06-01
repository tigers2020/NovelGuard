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

  it("times out slow calls", async () => {
    await expect(
      callBridge(
        () => new Promise((resolve) => setTimeout(() => resolve(1), 500)),
        { method: "get_snapshot", timeoutMs: 30 },
      ),
    ).rejects.toMatchObject({ code: "timeout" });
  });
});
