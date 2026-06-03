import { useMemo, useState } from "react";
import type {
  QualityRepairPreviewResult,
  RepairApplyErrorCode,
  RepairPreviewErrorCode,
} from "../../types/qualityRepair";
import { useBridge, useRefreshSnapshot } from "../../app/providers/snapshotHooks";
import { BridgeCallError } from "../../bridge/bridgeErrors";
import { issueSelectionFingerprint } from "../../bridge/issueSelectionFingerprint";

type Step = "preview" | "confirm" | "apply" | "done";

type PreviewState =
  | { status: "idle" }
  | { status: "ready"; preview: QualityRepairPreviewResult }
  | { status: "stale"; reason: "issue_selection_changed" | "library_changed" }
  | { status: "error"; message: string; reason?: RepairPreviewErrorCode };

function repairErrorMessage(err: unknown): {
  message: string;
  reason?: RepairApplyErrorCode | RepairPreviewErrorCode;
} {
  if (err instanceof BridgeCallError) {
    const reason = err.reason as RepairApplyErrorCode | RepairPreviewErrorCode | undefined;
    const byReason: Record<string, string> = {
      STALE_REPAIR_PREVIEW: "라이브러리 또는 파일이 변경되었습니다. 다시 미리보기하세요.",
      ISSUE_SELECTION_CHANGED: "선택이 변경되었습니다. 다시 미리보기하세요.",
      PLAN_MISMATCH: "복구 계획이 일치하지 않습니다. 다시 미리보기하세요.",
      NO_PENDING_REPAIR: "적용 가능한 복구 미리보기가 없습니다.",
      MISSING_REPAIR_PREVIEW_TOKEN: "미리보기 토큰이 없습니다.",
      INVALID_REPAIR_PREVIEW_TOKEN: "미리보기 토큰이 유효하지 않습니다.",
      REPAIR_FAILED: "복구 적용에 실패했습니다. 감사 로그를 확인하세요.",
      MOVE_PREVIEW_ACTIVE: "이동 미리보기가 활성 상태입니다. 먼저 닫으세요.",
      MIXED_OR_INELIGIBLE_SELECTION: "복구할 수 없는 이슈가 포함되어 있습니다.",
      BATCH_LIMIT_EXCEEDED: "한 번에 최대 10건까지 복구할 수 있습니다.",
      LIBRARY_BUSY: "스캔 또는 적용이 진행 중입니다.",
    };
    if (reason && byReason[reason]) {
      return { message: byReason[reason], reason };
    }
    return { message: err.message };
  }
  return { message: err instanceof Error ? err.message : "Repair failed" };
}

export function RepairSubflowDialog({
  open,
  issueId,
  snapshotLibraryRevision,
  onClose,
  onSuccess,
  onOpenFinalize,
}: {
  open: boolean;
  issueId: string | null;
  snapshotLibraryRevision: number;
  onClose: () => void;
  onSuccess: () => void;
  onOpenFinalize: () => void;
}) {
  const bridge = useBridge();
  const refreshSnapshot = useRefreshSnapshot();
  const [step, setStep] = useState<Step>("preview");
  const [previewState, setPreviewState] = useState<PreviewState>({ status: "idle" });
  const [previewError, setPreviewError] = useState<string | null>(null);
  const [applyError, setApplyError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [confirmChecked, setConfirmChecked] = useState(false);
  const [activeToken, setActiveToken] = useState<string | null>(null);

  const issueIds = useMemo(() => (issueId ? [issueId] : []), [issueId]);

  const effectivePreviewState = useMemo((): PreviewState => {
    if (previewState.status !== "ready" || !issueId) {
      return previewState;
    }
    const fp = issueSelectionFingerprint(issueIds);
    if (fp !== previewState.preview.issueSelectionFingerprint) {
      return { status: "stale", reason: "issue_selection_changed" };
    }
    if (snapshotLibraryRevision !== previewState.preview.libraryRevision) {
      return { status: "stale", reason: "library_changed" };
    }
    return previewState;
  }, [previewState, issueId, issueIds, snapshotLibraryRevision]);

  if (!open || !issueId) return null;

  const readyPreview =
    effectivePreviewState.status === "ready" ? effectivePreviewState.preview : null;
  const hasLowConfidence = readyPreview?.rows.some((r) => r.encodingConfidence === "low") ?? false;

  const handleClose = async () => {
    if (activeToken && step !== "done") {
      try {
        await bridge.discardQualityRepairPreview({ repairPreviewToken: activeToken });
      } catch {
        // best-effort
      }
    }
    setActiveToken(null);
    setPreviewState({ status: "idle" });
    setStep("preview");
    setPreviewError(null);
    setApplyError(null);
    setConfirmChecked(false);
    onClose();
  };

  const runPreview = async () => {
    setBusy(true);
    setPreviewError(null);
    setApplyError(null);
    try {
      const result = await bridge.getQualityRepairPreview({ issueIds });
      setActiveToken(result.repairPreviewToken);
      setPreviewState({ status: "ready", preview: result });
      setStep("confirm");
    } catch (err) {
      const { message } = repairErrorMessage(err);
      setPreviewError(message);
      setPreviewState({ status: "error", message });
      setStep("preview");
    } finally {
      setBusy(false);
    }
  };

  const runApply = async () => {
    if (effectivePreviewState.status !== "ready" || !confirmChecked) return;
    setBusy(true);
    setApplyError(null);
    try {
      await bridge.applyQualityRepair({
        issueIds,
        repairPreviewToken: effectivePreviewState.preview.repairPreviewToken,
      });
      setActiveToken(null);
      setPreviewState({ status: "idle" });
      setStep("done");
      await refreshSnapshot();
      onSuccess();
    } catch (err) {
      const { message, reason } = repairErrorMessage(err);
      setApplyError(message);
      if (reason === "STALE_REPAIR_PREVIEW" || reason === "ISSUE_SELECTION_CHANGED") {
        setPreviewState({
          status: "stale",
          reason: reason === "STALE_REPAIR_PREVIEW" ? "library_changed" : "issue_selection_changed",
        });
      }
      setStep("confirm");
    } finally {
      setBusy(false);
    }
  };

  const canApply =
    effectivePreviewState.status === "ready" &&
    step === "confirm" &&
    confirmChecked &&
    (readyPreview?.summary.operationCount ?? 0) > 0;

  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center bg-background/80 p-4 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      data-testid="quality-repair-subflow-dialog"
    >
      <div
        className="relative z-[101] w-full max-w-xl rounded-md border border-outline bg-surface p-5"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="text-lg font-bold text-on-surface">UTF-8 복구</h2>
        <p className="mt-1 text-sm text-on-surface-variant">미리보기 → 확인 → 적용</p>

        {effectivePreviewState.status === "stale" && (
          <p className="mt-3 rounded-md border border-outline bg-surface-elevated p-2 text-warning">
            {effectivePreviewState.reason === "library_changed"
              ? "라이브러리가 변경되었습니다. 다시 미리보기하세요."
              : "선택이 변경되었습니다. 다시 미리보기하세요."}
          </p>
        )}

        {previewError && (
          <p className="mt-3 text-sm text-error" data-testid="quality-repair-preview-error">
            {previewError}
          </p>
        )}

        {readyPreview && step !== "preview" && (
          <dl className="mt-3 space-y-2 text-sm" data-testid="quality-repair-preview-summary">
            {readyPreview.rows.map((row) => (
              <div key={row.issueId} className="rounded-md border border-outline p-2">
                <dt className="text-muted">경로</dt>
                <dd className="break-all">{row.relativePath}</dd>
                <dt className="mt-1 text-muted">소스 인코딩</dt>
                <dd>
                  {row.sourceEncoding} ({row.encodingConfidence})
                </dd>
                {row.encodingWarning && (
                  <dd className="mt-1 text-warning">{row.encodingWarning}</dd>
                )}
              </div>
            ))}
          </dl>
        )}

        {hasLowConfidence && step === "confirm" && (
          <p className="mt-2 text-sm text-warning">
            낮은 신뢰도 인코딩입니다. 미리보기 내용을 확인한 뒤 적용하세요.
          </p>
        )}

        {step === "confirm" && (
          <label className="mt-4 flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={confirmChecked}
              onChange={(e) => setConfirmChecked(e.target.checked)}
              data-testid="quality-repair-confirm-checkbox"
            />
            파일을 UTF-8로 덮어쓰는 것을 이해했습니다.
          </label>
        )}

        {applyError && (
          <p className="mt-2 text-sm text-error" data-testid="quality-repair-apply-error">
            {applyError}
          </p>
        )}

        {step === "done" && (
          <div className="mt-3 rounded-md border border-success/40 bg-success/10 p-3 text-sm">
            <p className="text-success" data-testid="quality-repair-done">
              복구가 완료되었습니다.
            </p>
            <button
              type="button"
              data-testid="quality-repair-open-finalize"
              className="mt-3 rounded-md bg-primary px-3 py-2 text-sm font-semibold text-background"
              onClick={() => {
                void handleClose().then(onOpenFinalize);
              }}
            >
              최종 검증으로 이동
            </button>
          </div>
        )}

        <div className="mt-5 flex flex-wrap justify-end gap-2">
          <button
            type="button"
            className="rounded-md border border-outline px-3 py-2 text-sm hover:bg-hover"
            onClick={() => void handleClose()}
          >
            닫기
          </button>
          {step === "preview" && (
            <button
              type="button"
              data-testid="quality-repair-preview-run"
              className="rounded-md bg-primary px-3 py-2 text-sm font-semibold text-background disabled:opacity-50"
              disabled={busy}
              onClick={() => void runPreview()}
            >
              복구 미리보기
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
                data-testid="quality-repair-apply-run"
                className="rounded-md bg-primary px-3 py-2 text-sm font-semibold text-background disabled:opacity-50"
                disabled={busy || !canApply}
                onClick={() => void runApply()}
              >
                복구 적용
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
