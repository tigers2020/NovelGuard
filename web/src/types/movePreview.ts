import type { SelectionScope } from "./selection";

export type PreviewApplyErrorCode =
  | "MISSING_PREVIEW_TOKEN"
  | "INVALID_PREVIEW_TOKEN"
  | "NO_PENDING_APPLY"
  | "STALE_PREVIEW"
  | "SELECTION_CHANGED";

export interface MovePreviewRow {
  id: string;
  action: string;
}

export interface MovePreviewSummary {
  rowCount: number;
  conflictCount?: number;
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
