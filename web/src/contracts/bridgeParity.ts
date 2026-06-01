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
  "discardMovePreview",
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
  "discard_move_preview",
] as const;

export function assertBridgeParity(bridge: NovelGuardBridge): void {
  for (const method of NOVEL_GUARD_BRIDGE_METHODS) {
    if (typeof bridge[method] !== "function") {
      throw new Error(`Bridge missing method: ${method}`);
    }
  }
}
