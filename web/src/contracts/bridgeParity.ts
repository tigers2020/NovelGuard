import type { NovelGuardBridge } from "../bridge/NovelGuardBridge";

export const NOVEL_GUARD_BRIDGE_METHODS = [
  "getAppInfo",
  "getSnapshot",
  "selectFolder",
  "startScan",
  "cancelRun",
  "setWorkMode",
  "queryReviewRows",
  "queryFileRows",
  "queryQualityRows",
  "getDuplicateGroupDetail",
  "getQualityIssueDetail",
  "getQualityRepairPreview",
  "applyQualityRepair",
  "discardQualityRepairPreview",
  "getMovePreview",
  "applyResolvedActions",
  "discardMovePreview",
  "updateReviewDecisions",
  "summarizeAutoSelectKeepers",
  "summarizeResolveAutoApprove",
  "getAppSetting",
  "setAppSetting",
  "queryLogEntries",
  "getLogsArtifacts",
  "getFinalizeSummary",
  "previewFinalizeCleanup",
  "runFinalizeVerification",
  "getFinalizeReport",
  "cancelFinalize",
] as const satisfies readonly (keyof NovelGuardBridge)[];

export const PYWEBVIEW_API_METHODS = [
  "get_app_info",
  "get_snapshot",
  "select_folder",
  "start_scan",
  "cancel_run",
  "set_work_mode",
  "query_review_rows",
  "query_file_rows",
  "query_quality_rows",
  "get_duplicate_group_detail",
  "get_quality_issue_detail",
  "get_quality_repair_preview",
  "apply_quality_repair",
  "discard_quality_repair_preview",
  "get_move_preview",
  "apply_resolved_actions",
  "discard_move_preview",
  "update_review_decisions",
  "summarize_auto_select_keepers",
  "summarize_resolve_auto_approve",
  "get_app_setting",
  "set_app_setting",
  "query_log_entries",
  "get_logs_artifacts",
  "get_finalize_summary",
  "preview_finalize_cleanup",
  "run_finalize_verification",
  "get_finalize_report",
  "cancel_finalize",
] as const;

export function assertBridgeParity(bridge: NovelGuardBridge): void {
  for (const method of NOVEL_GUARD_BRIDGE_METHODS) {
    if (typeof bridge[method] !== "function") {
      throw new Error(`Bridge missing method: ${method}`);
    }
  }
}
