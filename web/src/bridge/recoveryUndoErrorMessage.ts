import type { RecoveryUndoReason } from "../types/recoveryUndo";
import { isRecoveryRepreviewReason, isRecoveryUndoReason } from "../types/recoveryUndo";
import { BridgeCallError } from "./bridgeErrors";

export const RECOVERY_UNDO_ERROR_MESSAGES: Record<RecoveryUndoReason, string> = {
  MISSING_PREVIEW_TOKEN: "미리보기 토큰이 없습니다. 다시 미리보기하세요.",
  NO_PENDING_UNDO_PREVIEW: "적용 가능한 되돌리기 미리보기가 없습니다. 다시 미리보기하세요.",
  INVALID_PREVIEW_TOKEN: "미리보기 토큰이 유효하지 않습니다. 다시 미리보기하세요.",
  STALE_UNDO_PREVIEW: "되돌리기 계획이 변경되었습니다. 다시 미리보기하세요.",
  UNDO_IN_PROGRESS: "되돌리기가 이미 진행 중입니다. 완료될 때까지 기다려 주세요.",
  UNDO_PLAN_NOT_FOUND: "되돌리기 계획을 찾을 수 없습니다.",
  UNDO_BLOCKED: "되돌리기가 차단되었습니다. 감사 로그를 확인하세요.",
  LIBRARY_BUSY: "스캔 또는 적용이 진행 중입니다. 완료 후 다시 시도하세요.",
  NO_LIBRARY: "라이브러리가 없습니다. 폴더를 선택하세요.",
  INVALID_REQUEST: "요청이 유효하지 않습니다.",
};

export function recoveryUndoErrorMessage(err: unknown): {
  message: string;
  reason?: RecoveryUndoReason;
  requiresRepreview: boolean;
  actionDeferred: boolean;
} {
  if (err instanceof BridgeCallError) {
    const reason = err.reason;
    if (typeof reason === "string" && isRecoveryUndoReason(reason)) {
      return {
        message: RECOVERY_UNDO_ERROR_MESSAGES[reason],
        reason,
        requiresRepreview: isRecoveryRepreviewReason(reason),
        actionDeferred: reason === "UNDO_IN_PROGRESS" || reason === "LIBRARY_BUSY",
      };
    }
    return { message: err.message, requiresRepreview: false, actionDeferred: false };
  }
  return {
    message: err instanceof Error ? err.message : "되돌리기에 실패했습니다.",
    requiresRepreview: false,
    actionDeferred: false,
  };
}
