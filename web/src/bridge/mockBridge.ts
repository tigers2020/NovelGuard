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
import {
  applyMockReviewCommand,
  applyMockReviewState,
  fileRowStatusCounts,
} from "./mockReviewState";
import type { DuplicateGroupDetail, ReviewRow } from "../types/review";
import { buildMockDuplicateGroupDetail } from "./mockDuplicateGroupDetail";
import { buildMockQualityIssueDetail } from "./mockQualityIssueDetail";
import type { UpdateReviewDecisionsRequest } from "../types/reviewDecisions";

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
let includeRelation = false;

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

function mergedReviewRows(): ReviewRow[] {
  return applyMockReviewState(getAllReviewRows());
}

function buildSnapshot(): AppSnapshot {
  const merged = mergedReviewRows();
  const counts = fileRowStatusCounts(merged);
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
        queueCount: counts.queueCount,
        groupCount: 37,
        conflictCount: counts.conflictCount,
        approvedCount: counts.approvedCount,
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
      filteredCount: merged.length,
      issueCount: qualityRows.length,
      selectedCount: state.selectedCount,
    },
  };
}

function countCurrentQuery(query: ReviewRowsQuery, excludeRowIds: string[]): number {
  return filterReviewRows(mergedReviewRows(), query).filter((row) => !excludeRowIds.includes(row.id))
    .length;
}

function resolveSelectedRows(selection: SelectionScope): ReviewRow[] {
  const ids = resolveSelectionIds(selection);
  const idSet = new Set(ids);
  return mergedReviewRows().filter((row) => idSet.has(row.id));
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
    if (row.status === "approved" || row.status === "excluded" || row.status === "conflict") {
      continue;
    }
    const action = row.proposedAction;
    if (action === "keep" || action === "ignore") continue;
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

  const filtered = filterReviewRows(mergedReviewRows(), selection.query).filter(
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
    const filtered = filterReviewRows(mergedReviewRows(), query);
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

  async getDuplicateGroupDetail(groupId: string): Promise<DuplicateGroupDetail> {
    return buildMockDuplicateGroupDetail(groupId, mergedReviewRows(), buildQualityRows());
  },

  async getQualityIssueDetail(issueId) {
    return buildMockQualityIssueDetail(issueId, buildQualityRows(), libraryRevision);
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
      if (count > 0) {
        libraryRevision += 1;
      }
      console.info("[mockBridge] applyResolvedActions", request.selection, count);
    } finally {
      applyInProgress = false;
    }
  },

  async updateReviewDecisions(request: UpdateReviewDecisionsRequest) {
    const method = "updateReviewDecisions";
    if (request.selection.type !== "explicit_rows" || request.selection.rowIds.length === 0) {
      rejectApply(method, "INVALID_REVIEW_COMMAND");
    }
    validateSelectionScope(request.selection, (query, excludeRowIds) =>
      countCurrentQuery(query, excludeRowIds),
    );
    const selected = resolveSelectedRows(request.selection);
    const updated = applyMockReviewCommand(selected, request.command, request.keeperFileId);
    if (updated > 0) {
      libraryRevision += 1;
      clearPendingPreview();
    }
    return { updatedCount: updated, libraryRevision };
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

  async getAppSetting(key: string) {
    if (key === "include_relation") {
      return includeRelation;
    }
    return false;
  },

  async setAppSetting(key: string, value: boolean) {
    if (key === "include_relation") {
      includeRelation = value;
    }
  },
};
