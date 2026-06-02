export type EncodingConfidence = "high" | "low";

export type RepairPreviewErrorCode =
  | "BATCH_LIMIT_EXCEEDED"
  | "EMPTY_SELECTION"
  | "MIXED_OR_INELIGIBLE_SELECTION"
  | "MOVE_PREVIEW_ACTIVE"
  | "REPAIR_PREVIEW_ACTIVE"
  | "LIBRARY_BUSY";

export type RepairApplyErrorCode =
  | "STALE_REPAIR_PREVIEW"
  | "ISSUE_SELECTION_CHANGED"
  | "PLAN_MISMATCH"
  | "NO_PENDING_REPAIR"
  | "MISSING_REPAIR_PREVIEW_TOKEN"
  | "INVALID_REPAIR_PREVIEW_TOKEN"
  | "REPAIR_FAILED"
  | "LIBRARY_BUSY"
  | "MOVE_PREVIEW_ACTIVE";

export interface QualityRepairPreviewRequest {
  issueIds: string[];
}

export interface QualityRepairPreviewRow {
  issueId: string;
  action: "utf8_convert";
  relativePath: string;
  sourceEncoding: string;
  encodingConfidence: EncodingConfidence;
  encodingWarning?: string;
}

export interface QualityRepairPreviewSummary {
  issueCount: number;
  operationCount: number;
}

export interface QualityRepairPreviewResult {
  repairPreviewToken: string;
  libraryRevision: number;
  issueSelectionFingerprint: string;
  hasPendingQualityRepair: true;
  rows: QualityRepairPreviewRow[];
  summary: QualityRepairPreviewSummary;
}

export interface ApplyQualityRepairRequest {
  issueIds: string[];
  repairPreviewToken: string;
}

export interface DiscardQualityRepairPreviewRequest {
  repairPreviewToken: string;
}

export interface RepairFailedDetails {
  partialSuccess?: boolean;
  succeededCount?: number;
  failedIssueId?: string;
}
