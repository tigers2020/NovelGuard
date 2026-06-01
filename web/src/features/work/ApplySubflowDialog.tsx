import { useMemo, useState } from "react";
import type { SelectionScope } from "../../types/selection";
import type { PreviewApplyErrorCode } from "../../types/movePreview";
import { useBridge } from "../../app/providers/snapshotHooks";
import { BridgeCallError } from "../../bridge/bridgeErrors";
import { selectionFingerprint } from "../../bridge/selectionFingerprint";

type Step = "preview" | "confirm" | "apply";

type PreviewState =
  | { status: "idle" }
  | {
      status: "ready";
      token: string;
      libraryRevision: number;
      selectionFingerprint: string;
      rowCount: number;
    }
  | { status: "stale"; reason: "selection_changed" | "library_changed" }
  | { status: "error"; message: string; reason?: PreviewApplyErrorCode };

function applyErrorMessage(err: unknown): { message: string; reason?: PreviewApplyErrorCode } {
  if (err instanceof BridgeCallError) {
    const reason = err.reason;
    const byReason: Record<PreviewApplyErrorCode, string> = {
      STALE_PREVIEW: "라이브러리가 변경되었습니다. 다시 미리보기하세요.",
      SELECTION_CHANGED: "선택이 변경되었습니다. 다시 미리보기하세요.",
      NO_PENDING_APPLY: "적용 가능한 미리보기가 없습니다.",
      MISSING_PREVIEW_TOKEN: "미리보기 토큰이 없습니다.",
      INVALID_PREVIEW_TOKEN: "미리보기 토큰이 유효하지 않습니다.",
    };
    if (reason) {
      return { message: byReason[reason], reason };
    }
    return { message: err.message };
  }
  return { message: err instanceof Error ? err.message : "Apply failed" };
}

export function ApplySubflowDialog({
  open,
  selection,
  snapshotLibraryRevision,
  onClose,
}: {
  open: boolean;
  selection: SelectionScope | null;
  snapshotLibraryRevision: number;
  onClose: () => void;
}) {
  const bridge = useBridge();
  const [step, setStep] = useState<Step>("preview");
  const [previewState, setPreviewState] = useState<PreviewState>({ status: "idle" });
  const [previewError, setPreviewError] = useState<string | null>(null);
  const [applyError, setApplyError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  /** Token last issued by preview; used for discard on close even when UI shows stale. */
  const [activePreviewToken, setActivePreviewToken] = useState<string | null>(null);

  const effectivePreviewState = useMemo((): PreviewState => {
    if (previewState.status !== "ready" || !selection) {
      return previewState;
    }
    const fp = selectionFingerprint(selection);
    if (fp !== previewState.selectionFingerprint) {
      return { status: "stale", reason: "selection_changed" };
    }
    if (snapshotLibraryRevision !== previewState.libraryRevision) {
      return { status: "stale", reason: "library_changed" };
    }
    return previewState;
  }, [previewState, selection, snapshotLibraryRevision]);

  if (!open || !selection) return null;

  const handleClose = async () => {
    if (activePreviewToken) {
      try {
        await bridge.discardMovePreview({ previewToken: activePreviewToken });
      } catch {
        // Still close UI; discard is best-effort cleanup.
      }
    }
    setActivePreviewToken(null);
    setPreviewState({ status: "idle" });
    setStep("preview");
    setPreviewError(null);
    setApplyError(null);
    onClose();
  };

  const runPreview = async () => {
    setBusy(true);
    setPreviewError(null);
    setApplyError(null);
    try {
      const result = await bridge.getMovePreview(selection);
      setActivePreviewToken(result.previewToken);
      setPreviewState({
        status: "ready",
        token: result.previewToken,
        libraryRevision: result.libraryRevision,
        selectionFingerprint: result.selectionFingerprint,
        rowCount: result.rows.length,
      });
      setStep("confirm");
    } catch (err) {
      setPreviewError(err instanceof Error ? err.message : "Preview failed");
      setPreviewState({ status: "error", message: "Preview failed" });
      setStep("preview");
    } finally {
      setBusy(false);
    }
  };

  const runApply = async () => {
    if (effectivePreviewState.status !== "ready") {
      return;
    }
    setBusy(true);
    setApplyError(null);
    try {
      await bridge.applyResolvedActions({
        selection,
        previewToken: effectivePreviewState.token,
      });
      setActivePreviewToken(null);
      setPreviewState({ status: "idle" });
      setStep("preview");
      setPreviewError(null);
      onClose();
    } catch (err) {
      const { message, reason } = applyErrorMessage(err);
      setApplyError(message);
      if (reason === "STALE_PREVIEW" || reason === "SELECTION_CHANGED") {
        setPreviewState({
          status: "stale",
          reason: reason === "STALE_PREVIEW" ? "library_changed" : "selection_changed",
        });
      }
    } finally {
      setBusy(false);
    }
  };

  const canApply =
    effectivePreviewState.status === "ready" &&
    step === "confirm" &&
    !previewError &&
    effectivePreviewState.rowCount > 0;

  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center bg-background/80 p-4 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      data-testid="apply-subflow-dialog"
    >
      <div
        className="relative z-[101] w-full max-w-2xl rounded-md border border-outline bg-surface p-5"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="text-lg font-bold text-on-surface">이동 계획 적용</h2>
        <p className="mt-1 text-sm text-on-surface-variant">
          dry-run → confirm → apply. Progress는 GlobalCommandBar만 표시합니다.
        </p>

        <ol className="mt-4 grid gap-2 md:grid-cols-3">
          {(
            [
              ["preview", "1. Preview", "이동·충돌·대상 폴더 검토"],
              ["confirm", "2. Confirm", "파괴적 작업 전 명시 확인"],
              ["apply", "3. Apply", "Python command로 적용"],
            ] as const
          ).map(([id, title, text]) => (
            <li
              key={id}
              className={`rounded-md border p-3 text-sm ${
                step === id ? "border-primary bg-primary/10" : "border-outline"
              }`}
            >
              <p className="font-semibold text-on-surface">{title}</p>
              <p className="mt-1 text-on-surface-variant">{text}</p>
            </li>
          ))}
        </ol>

        {effectivePreviewState.status === "stale" && (
          <p className="mt-3 text-sm text-warning" data-testid="apply-stale-banner" role="status">
            미리보기가 오래되었습니다. 다시 미리보기가 필요합니다.
          </p>
        )}

        {previewError && (
          <p className="mt-3 text-sm text-error" data-testid="apply-preview-error" role="alert">
            {previewError}
          </p>
        )}

        {(applyError || effectivePreviewState.status === "error") && (
          <p className="mt-3 text-sm text-error" data-testid="apply-bridge-error" role="alert">
            {applyError ?? (effectivePreviewState.status === "error" ? effectivePreviewState.message : "")}
          </p>
        )}

        {step === "confirm" && effectivePreviewState.status === "ready" && !previewError && (
          <p className="mt-4 text-sm text-on-surface">
            미리보기 대상: <strong>{effectivePreviewState.rowCount}</strong> rows
          </p>
        )}

        <div className="mt-5 flex justify-end gap-2">
          <button
            type="button"
            onClick={() => void handleClose()}
            className="rounded-md border border-outline px-3 py-2 text-sm font-semibold hover:bg-hover"
          >
            취소
          </button>
          {step === "preview" && (
            <button
              type="button"
              disabled={busy}
              data-testid="apply-preview-run"
              onClick={() => void runPreview()}
              className="rounded-md bg-primary px-3 py-2 text-sm font-semibold text-background"
            >
              미리보기
            </button>
          )}
          {canApply && (
            <button
              type="button"
              disabled={busy}
              data-testid="apply-confirm-run"
              onClick={() => void runApply()}
              className="rounded-md bg-primary px-3 py-2 text-sm font-semibold text-background"
            >
              선택한 이동 적용
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
