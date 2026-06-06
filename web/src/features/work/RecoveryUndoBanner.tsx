import { useState } from "react";
import type { RecoveryState } from "../../types/recovery";
import {
  recoveryBatchKindLabel,
  recoveryManifestStatusLabel,
} from "./recoveryUndoCopy";
import { RecoveryUndoSubflowDialog } from "./RecoveryUndoSubflowDialog";

export function RecoveryUndoBanner({
  recoveryState,
  onRecoveryRefreshed,
}: {
  recoveryState: RecoveryState;
  onRecoveryRefreshed: () => Promise<void>;
}) {
  const [dialogOpen, setDialogOpen] = useState(false);

  if (!recoveryState.hasActivePlan) {
    return null;
  }

  const actionsDeferred = recoveryState.manifestStatus === "executing";

  return (
    <>
      <div
        className="border-b border-warning/40 bg-warning/10 px-4 py-3"
        data-testid="recovery-undo-banner"
        role="status"
      >
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0 flex-1 text-sm">
            <p className="font-semibold text-on-surface">부분 성공 복구 필요</p>
            <p className="mt-1 text-on-surface-variant">
              {recoveryBatchKindLabel(recoveryState.batchKind)} · 상태{" "}
              {recoveryManifestStatusLabel(recoveryState.manifestStatus)} · 적용 {recoveryState.appliedCount}
              건 · 복구 가능 {recoveryState.recoverableCount}건 · 차단 {recoveryState.blockedCount}
              건
            </p>
            {actionsDeferred && (
              <p className="mt-1 text-warning">
                되돌리기가 진행 중입니다. 완료 후 다시 확인하세요.
              </p>
            )}
          </div>
          <button
            type="button"
            data-testid="recovery-undo-open-dialog"
            className="shrink-0 rounded-md bg-primary px-3 py-2 text-sm font-semibold text-background disabled:opacity-50"
            disabled={actionsDeferred}
            onClick={() => setDialogOpen(true)}
          >
            되돌리기 미리보기
          </button>
        </div>
      </div>
      <RecoveryUndoSubflowDialog
        open={dialogOpen}
        recoveryState={recoveryState}
        onClose={() => setDialogOpen(false)}
        onRecoveryRefreshed={onRecoveryRefreshed}
      />
    </>
  );
}
