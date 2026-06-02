export type LogLevel = "DEBUG" | "INFO" | "WARNING" | "ERROR";

export type LogEntry = {
  timestamp: string;
  level: LogLevel;
  message: string;
  logger?: string;
  context?: Record<string, unknown>;
};

export type LogEntriesQuery = {
  level?: LogLevel;
  limit?: number;
};

export type LogEntriesPage = {
  entries: LogEntry[];
  pageInfo: {
    limit: number;
    hasMore: false;
  };
};

export type LogsArtifactKind =
  | "audit_tail"
  | "finalize_report"
  | "packaging_log"
  | "unknown";

export type LogsArtifact = {
  id: string;
  kind: LogsArtifactKind;
  label: string;
  path: string;
  createdAt?: string;
  sizeBytes?: number;
};

export type LogsArtifactsResponse = {
  artifacts: LogsArtifact[];
};
