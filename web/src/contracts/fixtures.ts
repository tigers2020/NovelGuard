import type { AppSnapshot } from "../types/snapshot";
import type { ReviewRowsPage } from "../types/review";
import type { QualityRowsPage } from "../types/quality";
import type { SelectionScope } from "../types/selection";

export const validAppSnapshot: AppSnapshot = {
  route: "work",
  theme: "dark",
  locale: "ko-KR",
  connection: "test",
  library: {
    folderPath: "/tmp",
    fileCount: 1,
    totalBytes: 100,
    duplicateGroups: 0,
    integrityIssues: 0,
    lastRun: null,
    scanOptions: [],
  },
  pipeline: {
    phase: "idle",
    percent: 0,
    label: "idle",
    cancellable: false,
  },
  work: {
    activeMode: "resolve",
    scan: { state: "empty", lastRun: null },
    resolve: {
      queueCount: 0,
      groupCount: 0,
      conflictCount: 0,
      approvedCount: 0,
      hasPendingApply: false,
    },
    quality: {
      integrityIssueCount: 0,
      encodingIssueCount: 0,
      smallFileAnomalyCount: 0,
    },
  },
  fileListSummary: {
    totalCount: 1,
    filteredCount: 1,
    issueCount: 0,
    selectedCount: 0,
  },
};

export const validReviewRowsPage: ReviewRowsPage = {
  rows: [
    {
      id: "r1",
      rowKind: "file",
      status: "unreviewed",
      type: "exact",
      name: "a.txt",
      proposedAction: "keep",
      hasChildren: false,
    },
  ],
  pageInfo: {
    cursor: null,
    nextCursor: null,
    hasMore: false,
    totalFiltered: 1,
  },
  summary: {
    selectedCount: 0,
    conflictCount: 0,
    unreviewedCount: 1,
    approvedCount: 0,
  },
};

export const validQualityRowsPage: QualityRowsPage = {
  rows: [],
  pageInfo: {
    cursor: null,
    nextCursor: null,
    hasMore: false,
    totalFiltered: 0,
  },
  summary: { issueCount: 0, warningCount: 0, errorCount: 0 },
};

export const explicitRowsSelection: SelectionScope = {
  type: "explicit_rows",
  rowIds: ["r1"],
};

export const currentQuerySelection: SelectionScope = {
  type: "current_query",
  query: { viewMode: "action" },
  excludeRowIds: [],
};
