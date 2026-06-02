export type FinalizeBlockerCode =
  | "PENDING_MOVE_PREVIEW"
  | "PENDING_REPAIR_PREVIEW"
  | "SCAN_NOT_SUCCESS"
  | "UNRESOLVED_DUPLICATE_QUEUE"
  | "QUALITY_ERROR_ISSUES";

export type FinalizeWarningCode =
  | "SMALL_FILE_ANOMALIES"
  | "UNREVIEWED_RELATION"
  | "NEAR_GROUPS_PRESENT";

export interface FinalizeBlocker {
  code: FinalizeBlockerCode;
  message: string;
  count?: number;
}

export interface FinalizeWarning {
  code: FinalizeWarningCode;
  message: string;
  count?: number;
}

export interface FinalizeSummary {
  libraryRevision: number;
  scanState: string;
  resolve: {
    queueCount: number;
    exactUnresolvedQueueCount: number;
    conflictCount: number;
    approvedCount: number;
    hasPendingApply: boolean;
  };
  quality: {
    encodingIssueCount: number;
    integrityIssueCount: number;
    smallFileAnomalyCount: number;
    hasPendingQualityRepair: boolean;
  };
  auditTail: {
    lastMoveApplyAt: string | null;
    lastRepairApplyAt: string | null;
    moveApplyCount: number;
    repairApplyCount: number;
  };
  blockers: FinalizeBlocker[];
  warnings: FinalizeWarning[];
}

export interface RunFinalizeRequest {
  includeCleanup: boolean;
}

export interface FinalizeCleanupResult {
  previewedEmptyDirs: string[];
  removedEmptyDirs: string[];
}

export type FinalizeResultStatus =
  | "complete"
  | "complete_with_warnings"
  | "blocked"
  | "cancelled"
  | "error";

export type FinalizeResult =
  | {
      status: "complete" | "complete_with_warnings" | "blocked";
      reportId: string;
      reportPath: string;
      libraryRevision: number;
      blockers: FinalizeBlocker[];
      warnings: FinalizeWarning[];
      cleanup: FinalizeCleanupResult;
    }
  | {
      status: "cancelled" | "error";
      reportId: null;
      reportPath: null;
      libraryRevision: number;
      blockers: FinalizeBlocker[];
      warnings: FinalizeWarning[];
      cleanup: FinalizeCleanupResult;
      errorMessage?: string;
    };

export interface FinalizeReportDocument {
  reportId: string;
  sessionId: string;
  createdAt: string;
  libraryRevision: number;
  status: FinalizeResultStatus;
  blockers: FinalizeBlocker[];
  warnings: FinalizeWarning[];
  summary: FinalizeSummary;
  audit: FinalizeSummary["auditTail"];
  cleanup: FinalizeCleanupResult;
}
