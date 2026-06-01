import type { NovelGuardBridge } from "./NovelGuardBridge";
import type { AppSnapshot } from "../types/snapshot";
import type { ReviewRowsPage, ReviewRowsQuery } from "../types/review";
import type { QualityIssueDetail, QualityRowsPage, QualityRowsQuery } from "../types/quality";
import type {
  ApplyResolvedActionsRequest,
  DiscardMovePreviewRequest,
  MovePreviewResult,
} from "../types/movePreview";
import type { SelectionScope } from "../types/selection";
import type { WorkMode } from "../types/snapshot";
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
    queryQualityRows: (query: QualityRowsQuery) =>
      callBridge(() => call<QualityRowsPage>(api, "query_quality_rows", query), {
        method: "query_quality_rows",
      }),
    getDuplicateGroupDetail: (groupId: string) =>
      callBridge(() => call<Record<string, unknown>>(api, "get_duplicate_group_detail", groupId), {
        method: "get_duplicate_group_detail",
      }),
    getQualityIssueDetail: (issueId: string) =>
      callBridge(() => call<QualityIssueDetail>(api, "get_quality_issue_detail", issueId), {
        method: "get_quality_issue_detail",
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
  };
}

export function isPywebviewHost(): boolean {
  return getPywebviewState() === "ready";
}
