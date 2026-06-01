import type { NovelGuardBridge } from "./NovelGuardBridge";
import type { AppSnapshot, WorkMode } from "../types/snapshot";
import type { ReviewRowsQuery } from "../types/review";
import type { SelectionScope } from "../types/selection";
import type {
  ApplyResolvedActionsRequest,
  DiscardMovePreviewRequest,
  MovePreviewRow,
  MovePreviewResult,
  PreviewApplyErrorCode,
} from "../types/movePreview";
import { validateSelectionScope } from "../types/selection";
import { validateAppSnapshot } from "../contracts/snapshotContract";
import { validateMovePreviewResult } from "../contracts/movePreviewContract";
import {
  clampQualityQueryLimit,
  validateQualityRowsPage,
} from "../contracts/qualityPageContract";
import { clampQueryLimit, validateReviewRowsPage } from "../contracts/reviewPageContract";
import {
  buildQualityRows,
  filterReviewRows,
  getAllReviewRows,
  paginateRows,
  sortReviewRows,
  summarizeReviewRows,
} from "./mockData";
import { BridgeCallError } from "./bridgeErrors";
import { selectionFingerprint, sha256HexUtf8 } from "./selectionFingerprint";
import type { ReviewRow } from "../types/review";

const state = {
  activeMode: "resolve" as WorkMode,
  folderPath: "D:/Novels/Library/raw",
  pipelineRunning: false,
  hasPendingApply: false,
  selectedCount: 0,
};

let libraryRevision = 0;

let pendingPreview: {
  token: string;
  libraryRevision: number;
  selectionFingerprint: string;
  rows: MovePreviewRow[];
  planFingerprint: string;
} | null = null;

let applyInProgress = false;

function rejectApply(method: string, reason: PreviewApplyErrorCode): never {
  throw new BridgeCallError(`Apply rejected: ${reason}`, {
    code: "rejected",
    method,
    reason,
  });
}

function clearPendingPreview(): void {
  pendingPreview = null;
  state.hasPendingApply = false;
}

export function bumpLibraryRevisionForTest(): void {
  libraryRevision += 1;
  clearPendingPreview();
}

if (typeof window !== "undefined") {
  (window as unknown as { __NOVELGUARD_TEST_BUMP_REVISION__?: () => void }).__NOVELGUARD_TEST_BUMP_REVISION__ =
    bumpLibraryRevisionForTest;
}

function buildSnapshot(): AppSnapshot {
  const allRows = getAllReviewRows();
  const summary = summarizeReviewRows(allRows);
  const qualityRows = buildQualityRows();

  return {
    route: "work",
    theme: "dark",
    locale: "ko-KR",
    connection: "Bridge ready (mock)",
    library: {
      folderPath: state.folderPath,
      fileCount: 1284,
      totalBytes: 2_840_000_000,
      duplicateGroups: 37,
      integrityIssues: 12,
      lastRun: "2026-06-01 10:42",
      scanOptions: [".txt", "하위 폴더 포함", "숨김 제외", "증분 스캔"],
    },
    pipeline: {
      phase: state.pipelineRunning ? "scan" : "idle",
      percent: state.pipelineRunning ? 42 : 0,
      label: state.pipelineRunning ? "스캔 중" : "대기 중",
      cancellable: state.pipelineRunning,
    },
    work: {
      activeMode: state.activeMode,
      scan: {
        state: state.pipelineRunning ? "running" : "success",
        lastRun: "2026-06-01 10:42",
      },
      resolve: {
        queueCount: summary.unreviewedCount + summary.conflictCount,
        groupCount: 37,
        conflictCount: summary.conflictCount,
        approvedCount: summary.approvedCount,
        hasPendingApply: state.hasPendingApply,
        libraryRevision,
      },
      quality: {
        integrityIssueCount: qualityRows.filter((r) => r.issueType === "integrity").length,
        encodingIssueCount: qualityRows.filter((r) => r.issueType === "encoding").length,
        smallFileAnomalyCount: qualityRows.filter((r) => r.issueType === "small_file").length,
      },
    },
    fileListSummary: {
      totalCount: 1284,
      filteredCount: allRows.length,
      issueCount: qualityRows.length,
      selectedCount: state.selectedCount,
    },
  };
}

function countCurrentQuery(query: ReviewRowsQuery, excludeRowIds: string[]): number {
  return filterReviewRows(getAllReviewRows(), query).filter((row) => !excludeRowIds.includes(row.id))
    .length;
}

function resolveSelectedRows(selection: SelectionScope): ReviewRow[] {
  const ids = resolveSelectionIds(selection);
  const idSet = new Set(ids);
  return getAllReviewRows().filter((row) => idSet.has(row.id));
}

function buildMockPreviewPlan(selection: SelectionScope): {
  rows: MovePreviewRow[];
  summary: {
    rowCount: number;
    operationCount: number;
    conflictCount?: number;
    blockedCount?: number;
  };
  planFingerprint: string;
} {
  const selectedRows = resolveSelectedRows(selection);
  const rows: MovePreviewRow[] = [];
  let blockedCount = 0;

  for (const row of selectedRows) {
    if (row.rowKind !== "file") continue;
    const action = row.proposedAction;
    if (action === "keep" || action === "ignore" || action === "delete") continue;
    if (action === "move_organized") {
      blockedCount += 1;
      continue;
    }
    if (action === "move_duplicate") {
      rows.push({ id: row.id, action: "move_duplicate" });
    } else {
      blockedCount += 1;
    }
  }

  const operations = rows.map((r) => ({ rowId: r.id, action: r.action }));
  const planFingerprint = sha256HexUtf8(JSON.stringify(operations));

  const summary: {
    rowCount: number;
    operationCount: number;
    conflictCount?: number;
    blockedCount?: number;
  } = {
    rowCount: rows.length,
    operationCount: rows.length,
  };
  if (blockedCount > 0) summary.blockedCount = blockedCount;

  return { rows, summary, planFingerprint };
}

function resolveSelectionIds(selection: SelectionScope): string[] {
  validateSelectionScope(selection, (query, excludeRowIds) =>
    countCurrentQuery(query, excludeRowIds),
  );

  if (selection.type === "explicit_rows") {
    return selection.rowIds;
  }

  const filtered = filterReviewRows(getAllReviewRows(), selection.query).filter(
    (row) => !selection.excludeRowIds.includes(row.id),
  );
  return filtered.map((row) => row.id);
}

export const mockBridge: NovelGuardBridge = {
  async getSnapshot() {
    const snapshot = buildSnapshot();
    validateAppSnapshot(snapshot);
    return snapshot;
  },

  async selectFolder() {
    if (applyInProgress) {
      rejectApply("select_folder", "LIBRARY_BUSY");
    }
    state.folderPath = "D:/Novels/Library/selected";
  },

  async startScan() {
    if (applyInProgress) {
      rejectApply("start_scan", "LIBRARY_BUSY");
    }
    state.pipelineRunning = true;
  },

  async cancelRun() {
    if (state.pipelineRunning) {
      state.pipelineRunning = false;
      libraryRevision += 1;
      clearPendingPreview();
    } else {
      state.pipelineRunning = false;
    }
  },

  async setWorkMode(mode) {
    state.activeMode = mode;
  },

  async queryReviewRows(query) {
    const limit = clampQueryLimit(query);
    const filtered = filterReviewRows(getAllReviewRows(), query);
    const sorted = sortReviewRows(filtered, query.sort);
    const { slice, nextCursor, hasMore } = paginateRows(sorted, query.cursor, limit);
    const summary = summarizeReviewRows(sorted);

    const page = {
      rows: slice,
      pageInfo: {
        cursor: query.cursor ?? null,
        nextCursor,
        hasMore,
        totalFiltered: sorted.length,
      },
      summary: {
        ...summary,
        selectedCount: state.selectedCount,
      },
    };
    validateReviewRowsPage(page);
    return page;
  },

  async queryQualityRows(query) {
    const validIssueTypes = ["integrity", "encoding", "small_file"] as const;
    if (!validIssueTypes.includes(query.issueType)) {
      const empty = {
        rows: [],
        pageInfo: {
          cursor: query.cursor ?? null,
          nextCursor: null,
          hasMore: false,
          totalFiltered: 0,
        },
        summary: { issueCount: 0, warningCount: 0, errorCount: 0 },
      };
      validateQualityRowsPage(empty);
      return empty;
    }
    const all = buildQualityRows().filter((row) => row.issueType === query.issueType);
    const search = query.filters?.search?.toLowerCase();
    const filtered = all.filter((row) => {
      if (query.filters?.severity && row.severity !== query.filters.severity) return false;
      if (search && !row.name.toLowerCase().includes(search)) return false;
      return true;
    });
    const limit = clampQualityQueryLimit(query);
    const { slice, nextCursor, hasMore } = paginateRows(filtered, query.cursor, limit);

    const page = {
      rows: slice,
      pageInfo: {
        cursor: query.cursor ?? null,
        nextCursor,
        hasMore,
        totalFiltered: filtered.length,
      },
      summary: {
        issueCount: filtered.length,
        warningCount: filtered.filter((r) => r.severity === "warning").length,
        errorCount: filtered.filter((r) => r.severity === "error").length,
      },
    };
    validateQualityRowsPage(page);
    return page;
  },

  async getDuplicateGroupDetail(groupId) {
    const row = getAllReviewRows().find((r) => r.groupId === groupId || r.id === groupId);
    return { groupId, row: row ?? null };
  },

  async getQualityIssueDetail(issueId) {
    const row = buildQualityRows().find((r) => r.id === issueId);
    if (!row) {
      return {
        id: issueId,
        issueType: "integrity",
        name: "Unknown",
        integrity: "Unknown",
      };
    }
    return {
      id: row.id,
      issueType: row.issueType,
      name: row.name,
      path: row.path,
      encoding: row.encoding,
      integrity: row.integrity,
      evidence: { severity: row.severity },
    };
  },

  async getMovePreview(selection) {
    const fp = selectionFingerprint(selection);
    const token = `preview-${globalThis.crypto.randomUUID()}`;
    const rev = libraryRevision;
    const plan = buildMockPreviewPlan(selection);

    pendingPreview = {
      token,
      libraryRevision: rev,
      selectionFingerprint: fp,
      rows: plan.rows,
      planFingerprint: plan.planFingerprint,
    };
    state.hasPendingApply = true;

    const result: MovePreviewResult = {
      previewToken: token,
      libraryRevision: rev,
      selectionFingerprint: fp,
      hasPendingApply: true,
      rows: plan.rows,
      summary: plan.summary,
    };
    validateMovePreviewResult(result);
    console.info("[mockBridge] getMovePreview", selection, plan.rows.length);
    return result;
  },

  async applyResolvedActions(request: ApplyResolvedActionsRequest) {
    const method = "applyResolvedActions";
    const token = request.previewToken?.trim() ?? "";
    if (!token) {
      rejectApply(method, "MISSING_PREVIEW_TOKEN");
    }
    if (!pendingPreview) {
      rejectApply(method, "NO_PENDING_APPLY");
    }
    if (token !== pendingPreview.token) {
      rejectApply(method, "INVALID_PREVIEW_TOKEN");
    }
    if (libraryRevision !== pendingPreview.libraryRevision) {
      clearPendingPreview();
      rejectApply(method, "STALE_PREVIEW");
    }
    const fp = selectionFingerprint(request.selection);
    if (fp !== pendingPreview.selectionFingerprint) {
      clearPendingPreview();
      rejectApply(method, "SELECTION_CHANGED");
    }

    applyInProgress = true;
    try {
      const count = pendingPreview.rows.length;
      clearPendingPreview();
      console.info("[mockBridge] applyResolvedActions", request.selection, count);
    } finally {
      applyInProgress = false;
    }
  },

  async discardMovePreview(request: DiscardMovePreviewRequest) {
    // Lifecycle cleanup — idempotent; never throws on mismatch.
    if (pendingPreview && request.previewToken === pendingPreview.token) {
      clearPendingPreview();
    } else {
      state.hasPendingApply = false;
      pendingPreview = null;
    }
  },
};
