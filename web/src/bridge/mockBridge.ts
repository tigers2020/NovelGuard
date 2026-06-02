import type { NovelGuardBridge } from "./NovelGuardBridge";
import type { FileRowsQuery } from "../types/fileRows";
import { validateFileRowsPage, clampFileRowsLimit } from "../contracts/fileRowsPageContract";
import { queryMockFileRows } from "./mockFileRows";
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
  sortQualityRows,
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
import type {
  ApplyQualityRepairRequest,
  DiscardQualityRepairPreviewRequest,
  QualityRepairPreviewRequest,
  QualityRepairPreviewResult,
  RepairApplyErrorCode,
  RepairPreviewErrorCode,
} from "../types/qualityRepair";
import { issueSelectionFingerprint, normalizeRepairIssueIds } from "./issueSelectionFingerprint";
import type {
  FinalizeReportDocument,
  FinalizeResult,
  FinalizeSummary,
  RunFinalizeRequest,
} from "../types/finalize";
import type {
  SnapshotInvalidationEvent,
  SnapshotInvalidationReason,
} from "../types/snapshotInvalidation";
import type { LogEntry, LogEntriesPage, LogEntriesQuery, LogsArtifactsResponse } from "../types/logs";
import type { AppSettingKey, AppSettingResponse, AppSettingValue } from "../types/settings";
import { filterByMinLevel } from "./logLevel";

const state = {
  activeMode: "resolve" as WorkMode,
  folderPath: "D:/Novels/Library/raw",
  pipelineRunning: false,
  hasPendingApply: false,
  selectedCount: 0,
};

let libraryRevision = 0;

let invalidationSequence = 0;
const invalidationListeners = new Set<(event: SnapshotInvalidationEvent) => void>();
let scanSimulationTimer: ReturnType<typeof setInterval> | undefined;

function emitSnapshotInvalidation(
  reason: SnapshotInvalidationReason,
  partial?: Pick<SnapshotInvalidationEvent, "libraryRevision" | "pipelinePhase">,
): void {
  invalidationSequence += 1;
  const event: SnapshotInvalidationEvent = {
    type: "snapshotInvalidated",
    reason,
    sequence: invalidationSequence,
    ...partial,
  };
  for (const listener of invalidationListeners) {
    listener(event);
  }
}

function stopScanSimulation(): void {
  if (scanSimulationTimer !== undefined) {
    clearInterval(scanSimulationTimer);
    scanSimulationTimer = undefined;
  }
}

let pendingPreview: {
  token: string;
  libraryRevision: number;
  selectionFingerprint: string;
  rows: MovePreviewRow[];
  planFingerprint: string;
} | null = null;

let applyInProgress = false;
let includeRelation = false;

const mockSettingDefaults: Record<AppSettingKey, AppSettingValue> = {
  include_relation: false,
  "scan.extensionFilter": ".txt,.md",
  "scan.includeSubdirs": true,
  "scan.includeHidden": false,
  "scan.incrementalScan": false,
  "scan.includeSymlinks": false,
};

const mockSettingValues: Record<string, AppSettingValue> = { ...mockSettingDefaults };
const mockSettingPersisted = new Set<string>();

const mockLogBuffer: LogEntry[] = [];

function appendMockLog(level: LogEntry["level"], message: string): void {
  mockLogBuffer.push({
    timestamp: new Date().toISOString().replace(/\.\d{3}Z$/, "Z"),
    level,
    message,
    logger: "mockBridge",
  });
  if (mockLogBuffer.length > 2000) {
    mockLogBuffer.splice(0, mockLogBuffer.length - 2000);
  }
}

function mockScanOptionsLabels(): string[] {
  const extensionFilter = String(mockSettingValues["scan.extensionFilter"] ?? ".txt,.md");
  const includeHidden = Boolean(mockSettingValues["scan.includeHidden"]);
  return [
    extensionFilter,
    "하위 폴더 포함",
    includeHidden ? "숨김 파일 포함" : "숨김 제외",
  ];
}

let pendingRepair: {
  token: string;
  libraryRevision: number;
  issueSelectionFingerprint: string;
  issueIds: string[];
} | null = null;

let lastFinalizeReport: FinalizeReportDocument | null = null;

function rejectApply(method: string, reason: PreviewApplyErrorCode): never {
  throw new BridgeCallError(`Apply rejected: ${reason}`, {
    code: "rejected",
    method,
    reason,
  });
}

function rejectRepair(
  method: string,
  reason: RepairApplyErrorCode | RepairPreviewErrorCode,
): never {
  throw new BridgeCallError(`Repair rejected: ${reason}`, {
    code: "rejected",
    method,
    reason,
  });
}

function clearPendingRepair(): void {
  pendingRepair = null;
}

function clearPendingPreview(): void {
  pendingPreview = null;
  state.hasPendingApply = false;
}

export function bumpLibraryRevisionForTest(): void {
  libraryRevision += 1;
  clearPendingPreview();
  emitSnapshotInvalidation("libraryRevision", { libraryRevision });
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
      scanOptions: mockScanOptionsLabels(),
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
        hasPendingQualityRepair: pendingRepair !== null,
      },
      finalize: {
        lastReportId: null,
        lastStatus: "idle",
        lastRunAt: null,
        blockerCount: 0,
        warningCount: 0,
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

function buildMockFinalizeSummary(): FinalizeSummary {
  const merged = mergedReviewRows();
  const counts = fileRowStatusCounts(merged);
  const qualityRows = buildQualityRows();
  const exactUnresolved = merged.filter(
    (row) =>
      row.rowKind === "file" &&
      row.type === "exact" &&
      (row.status === "unreviewed" || row.status === "conflict"),
  ).length;
  const blockers: FinalizeSummary["blockers"] = [];
  if (state.hasPendingApply) {
    blockers.push({
      code: "PENDING_MOVE_PREVIEW",
      message: "이동 미리보기가 적용되지 않았거나 해제되지 않았습니다.",
    });
  }
  if (pendingRepair) {
    blockers.push({
      code: "PENDING_REPAIR_PREVIEW",
      message: "품질 복구 미리보기가 적용되지 않았거나 해제되지 않았습니다.",
    });
  }
  const scanState = state.pipelineRunning ? "running" : "success";
  if (scanState !== "success") {
    blockers.push({ code: "SCAN_NOT_SUCCESS", message: "스캔이 성공적으로 완료되지 않았습니다." });
  }
  if (exactUnresolved > 0) {
    blockers.push({
      code: "UNRESOLVED_DUPLICATE_QUEUE",
      message: "미해결 exact 중복 파일이 남아 있습니다.",
      count: exactUnresolved,
    });
  }
  const encodingCount = qualityRows.filter((r) => r.issueType === "encoding").length;
  const integrityCount = qualityRows.filter((r) => r.issueType === "integrity").length;
  if (encodingCount + integrityCount > 0) {
    blockers.push({
      code: "QUALITY_ERROR_ISSUES",
      message: "인코딩 또는 무결성 품질 오류가 남아 있습니다.",
      count: encodingCount + integrityCount,
    });
  }
  const warnings: FinalizeSummary["warnings"] = [];
  const smallCount = qualityRows.filter((r) => r.issueType === "small_file").length;
  if (smallCount > 0) {
    warnings.push({
      code: "SMALL_FILE_ANOMALIES",
      message: "소용량 파일 이상이 남아 있습니다.",
      count: smallCount,
    });
  }
  return {
    libraryRevision,
    scanState,
    resolve: {
      queueCount: counts.queueCount,
      exactUnresolvedQueueCount: exactUnresolved,
      conflictCount: counts.conflictCount,
      approvedCount: counts.approvedCount,
      hasPendingApply: state.hasPendingApply,
    },
    quality: {
      encodingIssueCount: encodingCount,
      integrityIssueCount: integrityCount,
      smallFileAnomalyCount: smallCount,
      hasPendingQualityRepair: pendingRepair !== null,
    },
    auditTail: {
      lastMoveApplyAt: null,
      lastRepairApplyAt: null,
      moveApplyCount: 0,
      repairApplyCount: 0,
    },
    blockers,
    warnings,
  };
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
    libraryRevision += 1;
    emitSnapshotInvalidation("libraryRevision", { libraryRevision });
  },

  async startScan() {
    if (applyInProgress) {
      rejectApply("start_scan", "LIBRARY_BUSY");
    }
    stopScanSimulation();
    state.pipelineRunning = true;
    emitSnapshotInvalidation("pipelinePhase", { pipelinePhase: "scan" });
    let pct = 0;
    scanSimulationTimer = setInterval(() => {
      pct = Math.min(100, pct + 10);
      emitSnapshotInvalidation("scanProgress", { pipelinePhase: "scan" });
      if (pct >= 100) {
        stopScanSimulation();
        state.pipelineRunning = false;
        libraryRevision += 1;
        emitSnapshotInvalidation("libraryRevision", { libraryRevision });
      }
    }, 300);
  },

  async cancelRun() {
    stopScanSimulation();
    if (state.pipelineRunning) {
      state.pipelineRunning = false;
      libraryRevision += 1;
      clearPendingPreview();
      emitSnapshotInvalidation("pipelinePhase", { pipelinePhase: "idle" });
      emitSnapshotInvalidation("libraryRevision", { libraryRevision });
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

  async queryFileRows(query: FileRowsQuery) {
    clampFileRowsLimit(query);
    const page = queryMockFileRows(query);
    validateFileRowsPage(page);
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
    const sorted = sortQualityRows(filtered, query.sort);
    const { slice, nextCursor, hasMore } = paginateRows(sorted, query.cursor, limit);

    const page = {
      rows: slice,
      pageInfo: {
        cursor: query.cursor ?? null,
        nextCursor,
        hasMore,
        totalFiltered: sorted.length,
      },
      summary: {
        issueCount: sorted.length,
        warningCount: sorted.filter((r) => r.severity === "warning").length,
        errorCount: sorted.filter((r) => r.severity === "error").length,
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

  async getQualityRepairPreview(request: QualityRepairPreviewRequest) {
    const method = "getQualityRepairPreview";
    if (pendingPreview) {
      rejectRepair(method, "MOVE_PREVIEW_ACTIVE");
    }
    const ids = request.issueIds ?? [];
    if (ids.length < 1) {
      rejectRepair(method, "EMPTY_SELECTION");
    }
    if (ids.length > 10) {
      rejectRepair(method, "BATCH_LIMIT_EXCEEDED");
    }
    const normalized = normalizeRepairIssueIds(ids.map(String));
    if (normalized.length !== ids.length) {
      rejectRepair(method, "MIXED_OR_INELIGIBLE_SELECTION");
    }
    const rows = buildQualityRows().filter((r) => normalized.includes(r.id));
    if (rows.length !== normalized.length) {
      rejectRepair(method, "MIXED_OR_INELIGIBLE_SELECTION");
    }
    for (const row of rows) {
      if (row.issueType !== "encoding") {
        rejectRepair(method, "MIXED_OR_INELIGIBLE_SELECTION");
      }
    }
    const token = `repair-preview-${globalThis.crypto.randomUUID()}`;
    const fp = issueSelectionFingerprint(normalized);
    pendingRepair = {
      token,
      libraryRevision,
      issueSelectionFingerprint: fp,
      issueIds: normalized,
    };
    const result: QualityRepairPreviewResult = {
      repairPreviewToken: token,
      libraryRevision,
      issueSelectionFingerprint: fp,
      hasPendingQualityRepair: true,
      rows: rows.map((row) => ({
        issueId: row.id,
        action: "utf8_convert",
        relativePath: row.path ?? row.name,
        sourceEncoding: "cp949",
        encodingConfidence: "high",
      })),
      summary: { issueCount: rows.length, operationCount: rows.length },
    };
    console.info("[mockBridge] getQualityRepairPreview", normalized);
    return result;
  },

  async applyQualityRepair(request: ApplyQualityRepairRequest) {
    const method = "applyQualityRepair";
    const token = request.repairPreviewToken?.trim() ?? "";
    if (!token) {
      rejectRepair(method, "MISSING_REPAIR_PREVIEW_TOKEN");
    }
    if (!pendingRepair) {
      rejectRepair(method, "NO_PENDING_REPAIR");
    }
    if (token !== pendingRepair.token) {
      rejectRepair(method, "INVALID_REPAIR_PREVIEW_TOKEN");
    }
    const fp = issueSelectionFingerprint((request.issueIds ?? []).map(String));
    if (fp !== pendingRepair.issueSelectionFingerprint) {
      clearPendingRepair();
      rejectRepair(method, "ISSUE_SELECTION_CHANGED");
    }
    if (libraryRevision !== pendingRepair.libraryRevision) {
      clearPendingRepair();
      rejectRepair(method, "STALE_REPAIR_PREVIEW");
    }
    clearPendingRepair();
    libraryRevision += 1;
    emitSnapshotInvalidation("repairComplete", { libraryRevision });
    console.info("[mockBridge] applyQualityRepair", request.issueIds);
  },

  async discardQualityRepairPreview(request: DiscardQualityRepairPreviewRequest) {
    if (pendingRepair && request.repairPreviewToken === pendingRepair.token) {
      clearPendingRepair();
    } else {
      pendingRepair = null;
    }
  },

  async getMovePreview(selection) {
    if (pendingRepair) {
      rejectApply("getMovePreview", "REPAIR_PREVIEW_ACTIVE" as PreviewApplyErrorCode);
    }
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
        emitSnapshotInvalidation("applyComplete", { libraryRevision });
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
      emitSnapshotInvalidation("libraryRevision", { libraryRevision });
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

  async getAppSetting(key: AppSettingKey): Promise<AppSettingResponse> {
    if (key === "include_relation") {
      return {
        key,
        value: includeRelation,
        source: mockSettingPersisted.has(key) ? "persisted" : "default",
      };
    }
    const value = mockSettingValues[key] ?? mockSettingDefaults[key];
    return {
      key,
      value,
      source: mockSettingPersisted.has(key) ? "persisted" : "default",
    };
  },

  async setAppSetting(key: AppSettingKey, value: AppSettingValue): Promise<AppSettingResponse> {
    if (key === "include_relation") {
      if (typeof value !== "boolean") {
        throw new BridgeCallError("INVALID_SETTING_VALUE", "include_relation requires boolean");
      }
      includeRelation = value;
    } else {
      mockSettingValues[key] = value;
    }
    mockSettingPersisted.add(key);
    return {
      key,
      value: key === "include_relation" ? includeRelation : mockSettingValues[key],
      source: "persisted",
    };
  },

  async queryLogEntries(query: LogEntriesQuery): Promise<LogEntriesPage> {
    const limit = Math.min(Math.max(query.limit ?? 200, 1), 500);
    const filtered = filterByMinLevel(mockLogBuffer, query.level);
    const entries = filtered.slice(-limit);
    return { entries, pageInfo: { limit, hasMore: false } };
  },

  async getLogsArtifacts(): Promise<LogsArtifactsResponse> {
    if (!state.folderPath) {
      return { artifacts: [] };
    }
    return {
      artifacts: [
        {
          id: "mock-audit",
          kind: "audit_tail",
          label: "Apply audit log (mock)",
          path: `${state.folderPath}/.novelguard/apply-audit.jsonl`,
        },
        {
          id: "mock-finalize",
          kind: "finalize_report",
          label: "finalize_mock.json",
          path: `${state.folderPath}/SAVE/finalize/mock/finalize_mock.json`,
        },
      ],
    };
  },

  async getFinalizeSummary() {
    return buildMockFinalizeSummary();
  },

  async runFinalizeVerification(request: RunFinalizeRequest) {
    const summary = buildMockFinalizeSummary();
    const status =
      summary.blockers.length > 0
        ? "blocked"
        : summary.warnings.length > 0
          ? "complete_with_warnings"
          : "complete";
    const reportId = `finalize-mock-${Date.now()}`;
    const cleanup: FinalizeResult["cleanup"] = {
      previewedEmptyDirs: [],
      removedEmptyDirs: [],
    };
    if (request.includeCleanup && summary.blockers.length === 0) {
      cleanup.previewedEmptyDirs = ["duplicate/empty-slot"];
    }
    const doc: FinalizeReportDocument = {
      reportId,
      sessionId: "mock-session",
      createdAt: new Date().toISOString(),
      libraryRevision,
      status,
      blockers: summary.blockers,
      warnings: summary.warnings,
      summary,
      audit: summary.auditTail,
      cleanup,
    };
    lastFinalizeReport = doc;
    return {
      status,
      reportId,
      reportPath: `finalize/${reportId}.json`,
      libraryRevision,
      blockers: summary.blockers,
      warnings: summary.warnings,
      cleanup,
    } as FinalizeResult;
  },

  async getFinalizeReport(reportId: string) {
    if (!lastFinalizeReport || lastFinalizeReport.reportId !== reportId) {
      throw new BridgeCallError("REPORT_NOT_FOUND", { code: "rejected", method: "get_finalize_report" });
    }
    return lastFinalizeReport;
  },

  async cancelFinalize() {
    state.pipelineRunning = false;
  },

  async getAppInfo() {
    return {
      appName: "NovelGuard",
      version: "0.24.0",
      buildType: "dev",
      gitCommit: null,
      builtAt: null,
      frontendBuild: "web/build",
      pythonRuntime: "3.12.0",
    };
  },

  subscribeSnapshotInvalidation(listener) {
    invalidationListeners.add(listener);
    return () => {
      invalidationListeners.delete(listener);
    };
  },
};
