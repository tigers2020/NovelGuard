import type { NovelGuardBridge } from "./NovelGuardBridge";
import { BridgeCallError } from "./bridgeErrors";
import { mockBridge } from "./mockBridge";

export type TestBridgeFailMode =
  | "none"
  | "snapshot"
  | "queryReviewRows"
  | "queryQualityRows"
  | "getMovePreview"
  | "setWorkMode";

export function createTestBridge(fail: TestBridgeFailMode): NovelGuardBridge {
  const base = mockBridge;
  const failCall = (method: string): never => {
    throw new BridgeCallError(`E2E forced failure: ${method}`, { code: "rejected", method });
  };

  return {
    ...base,
    async getSnapshot() {
      if (fail === "snapshot") {
        failCall("get_snapshot");
      }
      return base.getSnapshot();
    },
    async queryReviewRows(query) {
      if (fail === "queryReviewRows") {
        failCall("query_review_rows");
      }
      return base.queryReviewRows(query);
    },
    async queryQualityRows(query) {
      if (fail === "queryQualityRows") {
        failCall("query_quality_rows");
      }
      return base.queryQualityRows(query);
    },
    async getMovePreview(selection) {
      if (fail === "getMovePreview") {
        failCall("get_move_preview");
      }
      return base.getMovePreview(selection);
    },
    async setWorkMode(mode) {
      if (fail === "setWorkMode") {
        failCall("set_work_mode");
      }
      return base.setWorkMode(mode);
    },
  };
}

export function readTestBridgeFailMode(): TestBridgeFailMode {
  if (typeof window === "undefined") {
    return "none";
  }
  const mode = (window as unknown as { __NOVELGUARD_TEST_BRIDGE_FAIL__?: string })
    .__NOVELGUARD_TEST_BRIDGE_FAIL__;
  if (
    mode === "snapshot" ||
    mode === "queryReviewRows" ||
    mode === "queryQualityRows" ||
    mode === "getMovePreview" ||
    mode === "setWorkMode"
  ) {
    return mode;
  }
  return "none";
}
