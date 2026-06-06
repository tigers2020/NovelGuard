/** Bridge rejection reasons for recovery undo preview/execute. */
export type RecoveryUndoReason =
  | "MISSING_PREVIEW_TOKEN"
  | "NO_PENDING_UNDO_PREVIEW"
  | "INVALID_PREVIEW_TOKEN"
  | "STALE_UNDO_PREVIEW"
  | "UNDO_IN_PROGRESS"
  | "UNDO_PLAN_NOT_FOUND"
  | "UNDO_BLOCKED"
  | "LIBRARY_BUSY"
  | "NO_LIBRARY"
  | "INVALID_REQUEST";

export const RECOVERY_UNDO_REASONS: readonly RecoveryUndoReason[] = [
  "MISSING_PREVIEW_TOKEN",
  "NO_PENDING_UNDO_PREVIEW",
  "INVALID_PREVIEW_TOKEN",
  "STALE_UNDO_PREVIEW",
  "UNDO_IN_PROGRESS",
  "UNDO_PLAN_NOT_FOUND",
  "UNDO_BLOCKED",
  "LIBRARY_BUSY",
  "NO_LIBRARY",
  "INVALID_REQUEST",
];

export function isRecoveryUndoReason(value: string): value is RecoveryUndoReason {
  return (RECOVERY_UNDO_REASONS as readonly string[]).includes(value);
}

/** Preview token stale/invalid — user must run preview again. */
export const RECOVERY_REPREVIEW_REASONS: readonly RecoveryUndoReason[] = [
  "MISSING_PREVIEW_TOKEN",
  "NO_PENDING_UNDO_PREVIEW",
  "INVALID_PREVIEW_TOKEN",
  "STALE_UNDO_PREVIEW",
];

export function isRecoveryRepreviewReason(
  reason: string,
): reason is RecoveryUndoReason {
  return (RECOVERY_REPREVIEW_REASONS as readonly string[]).includes(reason);
}
