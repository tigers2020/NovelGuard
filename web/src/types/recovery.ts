export type RecoveryBatchKind = "move_apply" | "repair_apply" | "finalize_cleanup";

export type UndoManifestStatus =
  | "pending"
  | "executing"
  | "completed"
  | "partial"
  | "expired"
  | "superseded";

export type UndoDryRunItemStatus = "recoverable" | "blocked" | "manual_required";

export type UndoExecutionItemStatus =
  | "recovered"
  | "already_recovered"
  | "recovery_failed"
  | "excluded";

export interface RecoveryState {
  hasActivePlan: boolean;
  undoPlanId: string | null;
  runId: string | null;
  batchKind: RecoveryBatchKind | null;
  manifestStatus: UndoManifestStatus | null;
  appliedCount: number;
  recoverableCount: number;
  manualRequiredCount: number;
  blockedCount: number;
  unrecoverableCount: number;
  sealedAt: string | null;
}

export interface UndoDryRunItemResult {
  operationId: string;
  sequence: number;
  fromPath: string;
  toPath: string;
  status: UndoDryRunItemStatus;
  reason: string | null;
}

export interface UndoDryRunPlan {
  undoPlanId: string;
  manifestPath: string | null;
  libraryId: string;
  runId: string;
  totalCount: number;
  recoverableCount: number;
  blockedCount: number;
  manualRequiredCount: number;
  items: UndoDryRunItemResult[];
  previewToken: string;
}

export interface UndoExecutionItemResult {
  operationId: string;
  sequence: number;
  status: UndoExecutionItemStatus;
  reason: string | null;
}

export interface UndoExecutionResult {
  undoPlanId: string;
  manifestStatus: UndoManifestStatus;
  noOp: boolean;
  recoveredCount: number;
  alreadyRecoveredCount: number;
  failedCount: number;
  excludedCount: number;
  items: UndoExecutionItemResult[];
}

export interface PreviewUndoPlanRequest {
  undoPlanId: string;
}

export interface ExecuteUndoPlanRequest {
  undoPlanId: string;
  previewToken: string;
}
