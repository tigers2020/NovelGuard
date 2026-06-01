export interface PipelineSnapshot {
  phase: string;
  percent: number;
  label: string;
  cancellable: boolean;
}

export interface ScanSnapshot {
  state: "empty" | "ready" | "running" | "success" | "error";
  lastRun: string | null;
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
  };
  fileListSummary: {
    totalCount: number;
    filteredCount: number;
    issueCount: number;
    selectedCount: number;
  };
}
