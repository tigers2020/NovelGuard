import type { NovelGuardBridge } from "./NovelGuardBridge";
import type { AppSnapshot, WorkMode } from "../types/snapshot";
import type { SelectionScope } from "../types/selection";
import { EmptySelectionError } from "../types/selection";
import {
  buildQualityRows,
  filterReviewRows,
  getAllReviewRows,
  paginateRows,
  summarizeReviewRows,
} from "./mockData";

const state = {
  activeMode: "resolve" as WorkMode,
  folderPath: "D:/Novels/Library/raw",
  pipelineRunning: false,
  hasPendingApply: false,
  selectedCount: 0,
};

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

function resolveSelectionIds(selection: SelectionScope): string[] {
  if (selection.type === "explicit_rows") {
    if (selection.rowIds.length === 0) throw new EmptySelectionError();
    return selection.rowIds;
  }

  const filtered = filterReviewRows(getAllReviewRows(), selection.query).filter(
    (row) => !selection.excludeRowIds.includes(row.id),
  );
  if (filtered.length === 0) throw new EmptySelectionError();
  return filtered.map((row) => row.id);
}

export const mockBridge: NovelGuardBridge = {
  async getSnapshot() {
    return buildSnapshot();
  },

  async selectFolder() {
    state.folderPath = "D:/Novels/Library/selected";
  },

  async startScan() {
    state.pipelineRunning = true;
  },

  async cancelRun() {
    state.pipelineRunning = false;
  },

  async setWorkMode(mode) {
    state.activeMode = mode;
  },

  async queryReviewRows(query) {
    const limit = Math.min(query.limit ?? 100, 200);
    const filtered = filterReviewRows(getAllReviewRows(), query);
    const { slice, nextCursor, hasMore } = paginateRows(filtered, query.cursor, limit);
    const summary = summarizeReviewRows(filtered);

    return {
      rows: slice,
      pageInfo: {
        cursor: query.cursor ?? null,
        nextCursor,
        hasMore,
        totalFiltered: filtered.length,
      },
      summary: {
        ...summary,
        selectedCount: state.selectedCount,
      },
    };
  },

  async queryQualityRows(query) {
    const all = buildQualityRows().filter((row) => row.issueType === query.issueType);
    const search = query.filters?.search?.toLowerCase();
    const filtered = all.filter((row) => {
      if (query.filters?.severity && row.severity !== query.filters.severity) return false;
      if (search && !row.name.toLowerCase().includes(search)) return false;
      return true;
    });
    const limit = Math.min(query.limit ?? 100, 200);
    const { slice, nextCursor, hasMore } = paginateRows(filtered, query.cursor, limit);

    return {
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
    const ids = resolveSelectionIds(selection);
    state.hasPendingApply = true;
    console.info("[mockBridge] getMovePreview", selection, ids.length);
    return {
      rows: ids.map((id) => ({ id, action: "move_organized" })),
    };
  },

  async applyResolvedActions(selection) {
    const ids = resolveSelectionIds(selection);
    state.hasPendingApply = false;
    console.info("[mockBridge] applyResolvedActions", selection, ids.length);
  },
};
