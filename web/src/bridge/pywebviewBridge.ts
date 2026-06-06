import type { NovelGuardBridge } from "./NovelGuardBridge";
import type { AppSnapshot } from "../types/snapshot";
import type { AutoSelectKeepersSummary } from "../types/autoSelectSummary";
import type { ResolveAutoApproveSummary } from "../types/resolveAutoApproveSummary";
import type { DuplicateGroupDetail, ReviewRowsPage, ReviewRowsQuery } from "../types/review";
import type { QualityIssueDetailResponse, QualityRowsPage, QualityRowsQuery } from "../types/quality";
import { validateQualityRowsPage } from "../contracts/qualityPageContract";
import type {
  ApplyResolvedActionsRequest,
  DiscardMovePreviewRequest,
  MovePreviewResult,
} from "../types/movePreview";
import type {
  UpdateReviewDecisionsRequest,
  UpdateReviewDecisionsResult,
} from "../types/reviewDecisions";
import type { SelectionScope } from "../types/selection";
import type { FinalizeReportDocument, FinalizeResult, FinalizeSummary, RunFinalizeRequest } from "../types/finalize";
import type { AppInfo } from "../types/appInfo";
import type { WorkMode } from "../types/snapshot";
import type { FileRowsPage, FileRowsQuery } from "../types/fileRows";
import { validateFileRowsPage } from "../contracts/fileRowsPageContract";
import { BridgeCallError } from "./bridgeErrors";
import { callBridge } from "./callBridge";

type PyApi = Record<string, (...args: unknown[]) => Promise<unknown>>;

export type PywebviewState = "none" | "ready" | "broken";

function call<T>(api: PyApi, method: string, ...args: unknown[]): Promise<T> {
  const fn = api[method];
  if (!fn) {
    return Promise.reject(
      new BridgeCallError(`pywebview api missing: ${method}`, {
        code: "missing_method",
        method,
      }),
    );
  }
  return fn(...args) as Promise<T>;
}

export function getPywebviewState(): PywebviewState {
  if (typeof window === "undefined") {
    return "none";
  }
  const w = window as unknown as { pywebview?: { api?: PyApi } };
  if (!w.pywebview) {
    return "none";
  }
  if (!w.pywebview.api) {
    return "broken";
  }
  return "ready";
}

export function getPywebviewApi(): PyApi | null {
  if (getPywebviewState() !== "ready") {
    return null;
  }
  const w = window as unknown as { pywebview?: { api?: PyApi } };
  return w.pywebview?.api ?? null;
}

/** Maps Python js_api (snake_case) to NovelGuardBridge. Does not fall back to mockBridge. */
export function createPywebviewBridge(api: PyApi): NovelGuardBridge {
  return {
    getAppInfo: () =>
      callBridge(() => call<AppInfo>(api, "get_app_info"), { method: "get_app_info" }),
    getSnapshot: () =>
      callBridge(() => call<AppSnapshot>(api, "get_snapshot"), { method: "get_snapshot" }),
    selectFolder: () =>
      callBridge(() => call(api, "select_folder").then(() => undefined), { method: "select_folder" }),
    startScan: (options) =>
      callBridge(() => call(api, "start_scan", options).then(() => undefined), {
        method: "start_scan",
      }),
    cancelRun: () =>
      callBridge(() => call(api, "cancel_run").then(() => undefined), { method: "cancel_run" }),
    setWorkMode: (mode: WorkMode) =>
      callBridge(() => call(api, "set_work_mode", mode).then(() => undefined), {
        method: "set_work_mode",
      }),
    queryReviewRows: (query: ReviewRowsQuery) =>
      callBridge(() => call<ReviewRowsPage>(api, "query_review_rows", query), {
        method: "query_review_rows",
      }),
    queryFileRows: (query: FileRowsQuery) =>
      callBridge(async () => {
        const page = await call<FileRowsPage>(api, "query_file_rows", query);
        validateFileRowsPage(page);
        return page;
      }, { method: "query_file_rows" }),
    queryQualityRows: (query: QualityRowsQuery) =>
      callBridge(async () => {
        const page = await call<QualityRowsPage>(api, "query_quality_rows", query);
        validateQualityRowsPage(page);
        return page;
      }, { method: "query_quality_rows" }),
    getDuplicateGroupDetail: (groupId: string) =>
      callBridge(() => call<DuplicateGroupDetail>(api, "get_duplicate_group_detail", groupId), {
        method: "get_duplicate_group_detail",
      }),
    getQualityIssueDetail: (issueId: string) =>
      callBridge(() => call<QualityIssueDetailResponse>(api, "get_quality_issue_detail", issueId), {
        method: "get_quality_issue_detail",
      }),
    getQualityRepairPreview: (request) =>
      callBridge(() => call(api, "get_quality_repair_preview", request), {
        method: "get_quality_repair_preview",
      }),
    applyQualityRepair: (request) =>
      callBridge(() => call(api, "apply_quality_repair", request).then(() => undefined), {
        method: "apply_quality_repair",
      }),
    discardQualityRepairPreview: (request) =>
      callBridge(() => call(api, "discard_quality_repair_preview", request).then(() => undefined), {
        method: "discard_quality_repair_preview",
      }),
    getMovePreview: (selection: SelectionScope) =>
      callBridge(() => call<MovePreviewResult>(api, "get_move_preview", selection), {
        method: "get_move_preview",
      }),
    applyResolvedActions: (request: ApplyResolvedActionsRequest) =>
      callBridge(() => call(api, "apply_resolved_actions", request).then(() => undefined), {
        method: "apply_resolved_actions",
      }),
    discardMovePreview: (request: DiscardMovePreviewRequest) =>
      callBridge(() => call(api, "discard_move_preview", request).then(() => undefined), {
        method: "discard_move_preview",
      }),
    updateReviewDecisions: (request: UpdateReviewDecisionsRequest) =>
      callBridge(() => call<UpdateReviewDecisionsResult>(api, "update_review_decisions", request), {
        method: "update_review_decisions",
      }),
    summarizeAutoSelectKeepers: (query: ReviewRowsQuery) =>
      callBridge(() => call<AutoSelectKeepersSummary>(api, "summarize_auto_select_keepers", query), {
        method: "summarize_auto_select_keepers",
      }),
    summarizeResolveAutoApprove: (query: ReviewRowsQuery) =>
      callBridge(
        () => call<ResolveAutoApproveSummary>(api, "summarize_resolve_auto_approve", query),
        { method: "summarize_resolve_auto_approve" },
      ),
    getAppSetting: (key) =>
      callBridge(() => call(api, "get_app_setting", key), { method: "get_app_setting" }),
    setAppSetting: (key, value) =>
      callBridge(() => call(api, "set_app_setting", key, value), { method: "set_app_setting" }),
    queryLogEntries: (query) =>
      callBridge(() => call(api, "query_log_entries", query), { method: "query_log_entries" }),
    getLogsArtifacts: () =>
      callBridge(() => call(api, "get_logs_artifacts"), { method: "get_logs_artifacts" }),
    getFinalizeSummary: () =>
      callBridge(() => call<FinalizeSummary>(api, "get_finalize_summary"), {
        method: "get_finalize_summary",
      }),
    previewFinalizeCleanup: () =>
      callBridge(() => call(api, "preview_finalize_cleanup"), {
        method: "preview_finalize_cleanup",
      }),
    runFinalizeVerification: (request: RunFinalizeRequest) =>
      callBridge(() => call<FinalizeResult>(api, "run_finalize_verification", request), {
        method: "run_finalize_verification",
      }),
    getFinalizeReport: (reportId: string) =>
      callBridge(() => call<FinalizeReportDocument>(api, "get_finalize_report", reportId), {
        method: "get_finalize_report",
      }),
    cancelFinalize: () =>
      callBridge(() => call(api, "cancel_finalize").then(() => undefined), {
        method: "cancel_finalize",
      }),
    subscribeSnapshotInvalidation: () => () => {},
  };
}

export function isPywebviewHost(): boolean {
  return getPywebviewState() === "ready";
}
