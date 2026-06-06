import { useState } from "react";
import type { RecoveryState, UndoDryRunPlan, UndoExecutionResult } from "../../types/recovery";
import { useBridge, useRefreshSnapshot } from "../../app/providers/snapshotHooks";
import { recoveryUndoErrorMessage } from "../../bridge/recoveryUndoErrorMessage";

type Step = "preview" | "confirm" | "done";

function isTerminalExecution(result: UndoExecutionResult): boolean {
  return (
    result.noOp ||
    result.manifestStatus === "completed" ||
    result.manifestStatus === "partial"
  );
}

function executionSummary(result: UndoExecutionResult): string {
  if (result.noOp) {
    return "변경할 항목이 없었습니다.";
  }
  if (result.manifestStatus === "partial") {
    return `부분 복구: ${result.recoveredCount}건 복구, ${result.failedCount}건 실패`;
  }
  return `복구 완료: ${result.recoveredCount}건`;
}

export function RecoveryUndoSubflowDialog({
  open,
  recoveryState,
  onClose,
  onRecoveryRefreshed,
}: {
  open: boolean;
  recoveryState: RecoveryState;
  onClose: () => void;
  onRecoveryRefreshed: () => Promise<void>;
}) {
  const bridge = useBridge();
  const refreshSnapshot = useRefreshSnapshot();
  const [step, setStep] = useState<Step>("preview");
  const [previewPlan, setPreviewPlan] = useState<UndoDryRunPlan | null>(null);
  /** Component state only — never persisted to storage. */
  const [previewToken, setPreviewToken] = useState<string | null>(null);
  const [previewError, setPreviewError] = useState<string | null>(null);
  const [executeError, setExecuteError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [confirmChecked, setConfirmChecked] = useState(false);
  const [executionResult, setExecutionResult] = useState<UndoExecutionResult | null>(null);

  const undoPlanId = recoveryState.undoPlanId;
  const actionsDeferred =
    recoveryState.manifestStatus === "executing" ||
    recoveryState.manifestStatus === "expired" ||
    recoveryState.manifestStatus === "superseded";

  if (!open || !undoPlanId) return null;

  const resetFlow = () => {
    setStep("preview");
    setPreviewPlan(null);
    setPreviewToken(null);
    setPreviewError(null);
    setExecuteError(null);
    setConfirmChecked(false);
    setExecutionResult(null);
  };

  const handleClose = () => {
    resetFlow();
    onClose();
  };

  const runPreview = async () => {
    setBusy(true);
    setPreviewError(null);
    setExecuteError(null);
    setPreviewToken(null);
    setPreviewPlan(null);
    setConfirmChecked(false);
    try {
      const plan = await bridge.previewUndoPlan({ undoPlanId });
      setPreviewPlan(plan);
      setPreviewToken(plan.previewToken);
      setStep("confirm");
    } catch (err) {
      const { message, requiresRepreview } = recoveryUndoErrorMessage(err);
      setPreviewError(message);
      if (requiresRepreview) {
        setPreviewToken(null);
        setPreviewPlan(null);
      }
      setStep("preview");
    } finally {
      setBusy(false);
    }
  };

  const runExecute = async () => {
    if (!previewToken || !confirmChecked || step !== "confirm") return;
    setBusy(true);
    setExecuteError(null);
    try {
      const result = await bridge.executeUndoPlan({ undoPlanId, previewToken });
      setPreviewToken(null);
      setExecutionResult(result);
      setStep("done");
      if (isTerminalExecution(result)) {
        await refreshSnapshot();
        await onRecoveryRefreshed();
      }
    } catch (err) {
      const { message, requiresRepreview, actionDeferred } = recoveryUndoErrorMessage(err);
      setExecuteError(message);
      if (requiresRepreview) {
        setPreviewToken(null);
        setPreviewPlan(null);
        setConfirmChecked(false);
        setStep("preview");
      } else if (!actionDeferred) {
        setStep("confirm");
      }
    } finally {
      setBusy(false);
    }
  };

  const canExecute =
    step === "confirm" &&
    previewToken != null &&
    confirmChecked &&
    !actionsDeferred &&
    !busy;

  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center bg-background/80 p-4 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      data-testid="recovery-undo-subflow-dialog"
    >
      <div
        className="relative z-[101] flex max-h-[min(90vh,720px)] w-full max-w-2xl flex-col rounded-md border border-outline bg-surface p-5"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="text-lg font-bold text-on-surface">부분 성공 되돌리기</h2>
        <p className="mt-1 text-sm text-on-surface-variant">미리보기 → 확인 → 실행</p>

        {actionsDeferred && (
          <p className="mt-3 rounded-md border border-outline bg-surface-elevated p-2 text-sm text-warning">
            {recoveryState.manifestStatus === "executing"
              ? "되돌리기가 진행 중입니다. 완료될 때까지 기다려 주세요."
              : "이 되돌리기 계획은 더 이상 실행할 수 없습니다."}
          </p>
        )}

        {previewError && (
          <p className="mt-3 text-sm text-error" data-testid="recovery-undo-preview-error">
            {previewError}
          </p>
        )}

        {previewPlan && step !== "preview" && (
          <div
            className="mt-3 min-h-0 flex-1 overflow-y-auto"
            data-testid="recovery-undo-preview-summary"
          >
            <dl className="grid grid-cols-2 gap-x-4 gap-y-1 text-sm sm:grid-cols-4">
              <div>
                <dt className="text-muted">전체</dt>
                <dd>{previewPlan.totalCount}</dd>
              </div>
              <div>
                <dt className="text-muted">복구 가능</dt>
                <dd>{previewPlan.recoverableCount}</dd>
              </div>
              <div>
                <dt className="text-muted">차단</dt>
                <dd>{previewPlan.blockedCount}</dd>
              </div>
              <div>
                <dt className="text-muted">수동 필요</dt>
                <dd>{previewPlan.manualRequiredCount}</dd>
              </div>
            </dl>
            {previewPlan.items.length > 0 && (
              <table className="mt-3 w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-outline text-muted">
                    <th className="py-1 pr-2">#</th>
                    <th className="py-1 pr-2">경로</th>
                    <th className="py-1">상태</th>
                  </tr>
                </thead>
                <tbody>
                  {previewPlan.items.map((item) => (
                    <tr key={item.operationId} className="border-b border-outline/50">
                      <td className="py-1 pr-2 align-top">{item.sequence}</td>
                      <td className="max-w-[14rem] break-all py-1 pr-2 align-top sm:max-w-none">
                        {item.fromPath}
                        {item.toPath ? ` → ${item.toPath}` : null}
                      </td>
                      <td className="py-1 align-top">{item.status}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}

        {step === "confirm" && (
          <label className="mt-4 flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={confirmChecked}
              onChange={(e) => setConfirmChecked(e.target.checked)}
              data-testid="recovery-undo-confirm-checkbox"
            />
            미리보기 내용을 확인했으며 되돌리기를 실행합니다.
          </label>
        )}

        {executeError && (
          <p className="mt-2 text-sm text-error" data-testid="recovery-undo-execute-error">
            {executeError}
          </p>
        )}

        {step === "done" && executionResult && (
          <div className="mt-3 rounded-md border border-success/40 bg-success/10 p-3 text-sm">
            <p className="text-success" data-testid="recovery-undo-done">
              {executionSummary(executionResult)}
            </p>
          </div>
        )}

        <div className="mt-5 flex flex-wrap justify-end gap-2">
          <button
            type="button"
            className="rounded-md border border-outline px-3 py-2 text-sm hover:bg-hover"
            onClick={handleClose}
          >
            닫기
          </button>
          {step === "preview" && (
            <button
              type="button"
              data-testid="recovery-undo-preview-run"
              className="rounded-md bg-primary px-3 py-2 text-sm font-semibold text-background disabled:opacity-50"
              disabled={busy || actionsDeferred}
              onClick={() => void runPreview()}
            >
              되돌리기 미리보기
            </button>
          )}
          {step === "confirm" && (
            <>
              <button
                type="button"
                className="rounded-md border border-outline px-3 py-2 text-sm"
                disabled={busy}
                onClick={() => void runPreview()}
              >
                다시 미리보기
              </button>
              <button
                type="button"
                data-testid="recovery-undo-execute-run"
                className="rounded-md bg-primary px-3 py-2 text-sm font-semibold text-background disabled:opacity-50"
                disabled={!canExecute}
                onClick={() => void runExecute()}
              >
                되돌리기 실행
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
