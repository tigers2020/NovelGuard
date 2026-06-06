import type {
  ExecuteUndoPlanRequest,
  PreviewUndoPlanRequest,
  RecoveryState,
  UndoDryRunPlan,
  UndoExecutionResult,
} from "../types/recovery";

export type {
  ExecuteUndoPlanRequest,
  PreviewUndoPlanRequest,
  RecoveryState,
  UndoDryRunPlan,
  UndoExecutionResult,
};

export const EMPTY_RECOVERY_STATE: RecoveryState = {
  hasActivePlan: false,
  undoPlanId: null,
  runId: null,
  batchKind: null,
  manifestStatus: null,
  appliedCount: 0,
  recoverableCount: 0,
  manualRequiredCount: 0,
  blockedCount: 0,
  unrecoverableCount: 0,
  sealedAt: null,
};

export function validateRecoveryState(payload: unknown): asserts payload is RecoveryState {
  if (typeof payload !== "object" || payload === null) {
    throw new Error("RecoveryState must be an object");
  }
  const state = payload as RecoveryState;
  if (typeof state.hasActivePlan !== "boolean") {
    throw new Error("RecoveryState.hasActivePlan must be boolean");
  }
}

export function validateUndoDryRunPlan(payload: unknown): asserts payload is UndoDryRunPlan {
  if (typeof payload !== "object" || payload === null) {
    throw new Error("UndoDryRunPlan must be an object");
  }
  const plan = payload as UndoDryRunPlan;
  if (typeof plan.previewToken !== "string" || !plan.previewToken.trim()) {
    throw new Error("UndoDryRunPlan.previewToken required");
  }
}

export function validateUndoExecutionResult(
  payload: unknown,
): asserts payload is UndoExecutionResult {
  if (typeof payload !== "object" || payload === null) {
    throw new Error("UndoExecutionResult must be an object");
  }
  const result = payload as UndoExecutionResult;
  if (typeof result.noOp !== "boolean") {
    throw new Error("UndoExecutionResult.noOp must be boolean");
  }
}
