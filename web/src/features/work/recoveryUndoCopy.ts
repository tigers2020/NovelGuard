import type { RecoveryBatchKind, UndoManifestStatus } from "../../types/recovery";

const BATCH_KIND_LABELS: Record<RecoveryBatchKind, string> = {
  move_apply: "이동 적용",
  repair_apply: "복구 적용",
  finalize_cleanup: "정리 작업",
};

const MANIFEST_STATUS_LABELS: Record<UndoManifestStatus, string> = {
  pending: "대기",
  executing: "실행 중",
  completed: "완료",
  partial: "부분 완료",
  expired: "만료",
  superseded: "대체됨",
};

export function recoveryBatchKindLabel(kind: RecoveryBatchKind | null): string {
  if (!kind) return "알 수 없음";
  return BATCH_KIND_LABELS[kind];
}

export function recoveryManifestStatusLabel(status: UndoManifestStatus | null): string {
  if (!status) return "—";
  return MANIFEST_STATUS_LABELS[status];
}
