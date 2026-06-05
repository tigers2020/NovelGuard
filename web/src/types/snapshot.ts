export interface PipelineBackgroundSnapshot {
  active: boolean;
  phase: string;
  label: string;
  step: number;
  stepTotal: number;
  percent: number;
}

export interface PipelineSnapshot {
  phase: string;
  percent: number;
  label: string;
  cancellable: boolean;
  background: PipelineBackgroundSnapshot | null;
}

export type DeepAnalysisStatus = "idle" | "running" | "complete" | "error";

export interface ScanSnapshot {
  state: "empty" | "ready" | "running" | "success" | "error";
  lastRun: string | null;
  exactAutoApprovedCount: number;
  indexReady: boolean;
  deepAnalysisComplete: boolean;
  deepAnalysisStatus: DeepAnalysisStatus;
  deepAnalysisError: string | null;
}

export interface ResolveSnapshot {
  queueCount: number;
  groupCount: number;
  conflictCount: number;
  approvedCount: number;
  hasPendingApply: boolean;
  libraryRevision: number;
}

export interface QualitySnapshot {
  integrityIssueCount: number;
  encodingIssueCount: number;
  smallFileAnomalyCount: number;
  hasPendingQualityRepair: boolean;
}

export type FinalizeLastStatus =
  | "idle"
  | "running"
  | "complete"
  | "complete_with_warnings"
  | "blocked"
  | "error";

export interface FinalizeSnapshot {
  lastReportId: string | null;
  lastStatus: FinalizeLastStatus;
  lastRunAt: string | null;
  blockerCount: number;
  warningCount: number;
}

export type WorkMode = "scan" | "resolve" | "quality";

export interface AppSnapshot {
  route: "work" | "settings" | "logs";
  theme: "dark" | "light";
  locale: string;
  connection: string;
  library: {
    folderPath: string | null;
    fileCount: number;
    totalBytes: number;
    duplicateGroups: number;
    integrityIssues: number;
    lastRun: string | null;
    scanOptions: string[];
  };
  pipeline: PipelineSnapshot;
  work: {
    activeMode: WorkMode;
    scan: ScanSnapshot;
    resolve: ResolveSnapshot;
    quality: QualitySnapshot;
    finalize: FinalizeSnapshot;
  };
  fileListSummary: {
    totalCount: number;
    filteredCount: number;
    issueCount: number;
    selectedCount: number;
  };
}
