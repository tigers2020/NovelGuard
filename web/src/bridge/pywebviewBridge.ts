import type { NovelGuardBridge } from "./NovelGuardBridge";
import type { AppSnapshot } from "../types/snapshot";
import type { ReviewRowsPage, ReviewRowsQuery } from "../types/review";
import type { QualityIssueDetail, QualityRowsPage, QualityRowsQuery } from "../types/quality";
import type { SelectionScope } from "../types/selection";
import type { WorkMode } from "../types/snapshot";
import { mockBridge } from "./mockBridge";

type PyApi = Record<string, (...args: unknown[]) => Promise<unknown>>;

function getApi(): PyApi | null {
  if (typeof window === "undefined") return null;
  const w = window as unknown as { pywebview?: { api?: PyApi } };
  return w.pywebview?.api ?? null;
}

function call<T>(api: PyApi, method: string, ...args: unknown[]): Promise<T> {
  const fn = api[method];
  if (!fn) {
    return Promise.reject(new Error(`pywebview api missing: ${method}`));
  }
  return fn(...args) as Promise<T>;
}

/** Maps Python js_api (snake_case) to NovelGuardBridge. Falls back to mock per method if missing. */
export function createPywebviewBridge(): NovelGuardBridge {
  const api = getApi();
  if (!api) return mockBridge;

  return {
    getSnapshot: () =>
      call<AppSnapshot>(api, "get_snapshot").catch(() => mockBridge.getSnapshot()),
    selectFolder: () => call(api, "select_folder").then(() => undefined).catch(() => mockBridge.selectFolder()),
    startScan: (options) =>
      call(api, "start_scan", options).then(() => undefined).catch(() => mockBridge.startScan(options)),
    cancelRun: () => call(api, "cancel_run").then(() => undefined).catch(() => mockBridge.cancelRun()),
    setWorkMode: (mode: WorkMode) =>
      call(api, "set_work_mode", mode).then(() => undefined).catch(() => mockBridge.setWorkMode(mode)),
    queryReviewRows: (query: ReviewRowsQuery) =>
      call<ReviewRowsPage>(api, "query_review_rows", query).catch(() => mockBridge.queryReviewRows(query)),
    queryQualityRows: (query: QualityRowsQuery) =>
      call<QualityRowsPage>(api, "query_quality_rows", query).catch(() => mockBridge.queryQualityRows(query)),
    getDuplicateGroupDetail: (groupId: string) =>
      call<Record<string, unknown>>(api, "get_duplicate_group_detail", groupId).catch(() =>
        mockBridge.getDuplicateGroupDetail(groupId),
      ),
    getQualityIssueDetail: (issueId: string) =>
      call<QualityIssueDetail>(api, "get_quality_issue_detail", issueId).catch(() =>
        mockBridge.getQualityIssueDetail(issueId),
      ),
    getMovePreview: (selection: SelectionScope) =>
      call<{ rows: unknown[] }>(api, "get_move_preview", selection).catch(() =>
        mockBridge.getMovePreview(selection),
      ),
    applyResolvedActions: (selection: SelectionScope) =>
      call(api, "apply_resolved_actions", selection).then(() => undefined).catch(() =>
        mockBridge.applyResolvedActions(selection),
      ),
  };
}

export function isPywebviewHost(): boolean {
  return getApi() !== null;
}
