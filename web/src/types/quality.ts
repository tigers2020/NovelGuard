import type { ReviewRowsPage } from "./review";

export type QualityIssueType = "integrity" | "encoding" | "small_file";

export interface QualityRowsQuery {
  issueType: QualityIssueType;
  filters?: { search?: string; severity?: "warning" | "error" };
  sort?: { field: string; direction: "asc" | "desc" };
  cursor?: string | null;
  limit?: number;
}

export interface QualityRow {
  id: string;
  issueType: QualityIssueType;
  name: string;
  path?: string;
  encoding?: string;
  integrity: string;
  severity: "warning" | "error";
  suggestedAction?: string;
}

export interface QualityRowsPage {
  rows: QualityRow[];
  pageInfo: ReviewRowsPage["pageInfo"];
  summary: { issueCount: number; warningCount: number; errorCount: number };
}

export interface QualityIssueDetail {
  id: string;
  issueType: QualityIssueType;
  name: string;
  path?: string;
  encoding?: string;
  integrity: string;
  evidence?: Record<string, unknown>;
}
