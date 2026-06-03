import type { SelectionScope } from "./selection";

export type PreviewApplyErrorCode =
  | "REPAIR_PREVIEW_ACTIVE"
  | "MISSING_PREVIEW_TOKEN"
  | "INVALID_PREVIEW_TOKEN"
  | "NO_PENDING_APPLY"
  | "STALE_PREVIEW"
  | "SELECTION_CHANGED"
  | "APPLY_FAILED"
  | "LIBRARY_BUSY"
  | "INVALID_REVIEW_COMMAND"
  | "NEAR_DUPLICATE_APPLY_UNSUPPORTED"
  | "RELATION_APPLY_UNSUPPORTED"
  | "INVALID_SETTING_VALUE";

/** Optional payload on APPLY_FAILED (PR-15 backend; PR-16 UI). */
export interface ApplyFailedDetails {
  partialSuccess?: boolean;
  succeededCount?: number;
  failedRowId?: string;
  refreshError?: string;
}

export interface MovePreviewRow {
  id: string;
  action: string;
}

export interface MovePreviewSummary {
  rowCount: number;
  conflictCount?: number;
  operationCount?: number;
  blockedCount?: number;
}

export interface MovePreviewResult {
  previewToken: string;
  libraryRevision: number;
  selectionFingerprint: string;
  hasPendingApply: true;
  rows: MovePreviewRow[];
  summary: MovePreviewSummary;
}

export interface ApplyResolvedActionsRequest {
  selection: SelectionScope;
  previewToken: string;
}

export interface DiscardMovePreviewRequest {
  previewToken: string;
}
