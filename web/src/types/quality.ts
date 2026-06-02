import type { ReviewRowsPage } from "./review";

export type QualityIssueType = "integrity" | "encoding" | "small_file";

export type QualityKind = "empty_file" | "tiny_file" | "invalid_utf8" | "read_error";

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

export interface IssueEvidenceBase {
  kind: QualityKind;
  message: string;
  severity: "warning" | "error";
  sizeBytes: number;
}

export interface IssueEvidenceEmptyFile extends IssueEvidenceBase {
  kind: "empty_file";
}

export interface IssueEvidenceTinyFile extends IssueEvidenceBase {
  kind: "tiny_file";
  thresholdBytes: number;
}

export interface IssueEvidenceInvalidUtf8 extends IssueEvidenceBase {
  kind: "invalid_utf8";
  decodeError?: string;
}

export interface IssueEvidenceReadError extends IssueEvidenceBase {
  kind: "read_error";
  error?: string;
}

export type IssueEvidence =
  | IssueEvidenceEmptyFile
  | IssueEvidenceTinyFile
  | IssueEvidenceInvalidUtf8
  | IssueEvidenceReadError;

export type RepairEligibility =
  | {
      eligible: true;
      reason: "ready";
      futureAction: "utf8_convert";
      label: string;
    }
  | {
      eligible: false;
      reason: "repair_not_implemented" | "issue_not_repairable" | "read_error";
      futureAction?: "utf8_convert";
      label: string;
    };

export interface QualityIssueDetail {
  id: string;
  libraryRevision: number;
  issueType: QualityIssueType;
  name: string;
  path: string;
  encoding: string;
  integrity: string;
  severity: "warning" | "error";
  suggestedAction: string;
  file: {
    fileId: string;
    sizeBytes: number;
    modifiedAtNs: number;
    extension: string;
    contentSha256: string;
  };
  evidence: IssueEvidence;
  repairEligibility: RepairEligibility;
}

export type QualityIssueDetailResponse =
  | {
      status: "ok";
      detail: QualityIssueDetail;
    }
  | {
      status: "not_found";
      id: string;
      message: "quality_issue_not_found";
    };
