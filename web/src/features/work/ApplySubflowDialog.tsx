import { useMemo, useState } from "react";
import type { SelectionScope } from "../../types/selection";
import type {
  ApplyFailedDetails,
  MovePreviewResult,
  MovePreviewSummary,
  PreviewApplyErrorCode,
} from "../../types/movePreview";
import { useBridge, useRefreshSnapshot } from "../../app/providers/snapshotHooks";
import { BridgeCallError } from "../../bridge/bridgeErrors";
import { selectionFingerprint } from "../../bridge/selectionFingerprint";

type Step = "preview" | "confirm" | "apply" | "done";

type PreviewState =
  | { status: "idle" }
  | {
      status: "ready";
      preview: MovePreviewResult;
    }
  | { status: "stale"; reason: "selection_changed" | "library_changed" }
  | { status: "error"; message: string; reason?: PreviewApplyErrorCode };

type ApplyOutcome = {
  operationCount: number;
  libraryRevision: number;
};

function applyErrorMessage(err: unknown): {
  message: string;
  reason?: PreviewApplyErrorCode;
  details?: ApplyFailedDetails;
} {
  if (err instanceof BridgeCallError) {
    const reason = err.reason;
    const details = err.details;
    const byReason: Record<PreviewApplyErrorCode, string> = {
      STALE_PREVIEW: "라이브러리가 변경되었습니다. 다시 미리보기하세요.",
      SELECTION_CHANGED: "선택이 변경되었습니다. 다시 미리보기하세요.",
      NO_PENDING_APPLY: "적용 가능한 미리보기가 없습니다.",
      MISSING_PREVIEW_TOKEN: "미리보기 토큰이 없습니다.",
      INVALID_PREVIEW_TOKEN: "미리보기 토큰이 유효하지 않습니다.",
      APPLY_FAILED: formatApplyFailedMessage(details),
      LIBRARY_BUSY: "스캔 또는 적용이 진행 중입니다. 완료 후 다시 시도하세요.",
      REPAIR_PREVIEW_ACTIVE: "품질 복구 미리보기가 활성 상태입니다. 먼저 닫으세요.",
      INVALID_REVIEW_COMMAND: "지원하지 않는 검토 명령입니다.",
      NEAR_DUPLICATE_APPLY_UNSUPPORTED: "유사 중복 항목은 적용할 수 없습니다.",
      RELATION_APPLY_UNSUPPORTED: "관계 항목은 적용할 수 없습니다.",
      INVALID_SETTING_VALUE: "설정 값이 유효하지 않습니다.",
    };
    if (reason && reason in byReason) {
      const previewReason = reason as PreviewApplyErrorCode;
      return { message: byReason[previewReason], reason: previewReason, details };
    }
    return { message: err.message };
  }
  return { message: err instanceof Error ? err.message : "Apply failed" };
}

function formatApplyFailedMessage(details?: ApplyFailedDetails): string {
  if (!details?.partialSuccess) {
    return "이동 적용에 실패했습니다. 감사 로그를 확인하세요.";
  }
  const n = details.succeededCount ?? 0;
  const failed = details.failedRowId ? ` (실패 행: ${details.failedRowId})` : "";
  const refresh = details.refreshError
    ? " 인덱스 새로고침에 실패했습니다. 재스캔을 권장합니다."
    : "";
  return `${n}건 이동 후 중단되었습니다.${failed}${refresh} 감사 로그를 확인하세요.`;
}

function SummaryChips({ summary }: { summary: MovePreviewSummary }) {
  const chips: { label: string; value: number; testId: string }[] = [
    { label: "실행", value: summary.operationCount ?? 0, testId: "apply-summary-operations" },
    { label: "미리보기 행", value: summary.rowCount, testId: "apply-summary-rows" },
  ];
  if (summary.conflictCount) {
    chips.push({
      label: "충돌",
      value: summary.conflictCount,
      testId: "apply-summary-conflicts",
    });
  }
  if (summary.blockedCount) {
    chips.push({
      label: "차단",
      value: summary.blockedCount,
      testId: "apply-summary-blocked",
    });
  }

  return (
    <dl className="mt-3 flex flex-wrap gap-2" data-testid="apply-preview-summary">
      {chips.map((chip) => (
        <div
          key={chip.testId}
          className="rounded-md border border-outline bg-surface-elevated px-3 py-2 text-sm"
          data-testid={chip.testId}
        >
          <dt className="text-on-surface-variant">{chip.label}</dt>
          <dd className="font-semibold text-on-surface">{chip.value}</dd>
        </div>
      ))}
    </dl>
  );
}

function PreviewRowsTable({ rows }: { rows: MovePreviewResult["rows"] }) {
  if (rows.length === 0) {
    return (
      <p className="mt-3 text-sm text-on-surface-variant" data-testid="apply-preview-empty">
        실행 가능한 이동이 없습니다. 충돌·차단 요약을 확인하세요.
      </p>
    );
  }

  return (
    <div
      className="mt-3 max-h-48 overflow-auto rounded-md border border-outline"
      data-testid="apply-preview-table"
    >
      <table className="w-full text-left text-sm">
        <thead className="sticky top-0 bg-surface-elevated text-on-surface-variant">
          <tr>
            <th className="px-3 py-2 font-semibold">행 ID</th>
            <th className="px-3 py-2 font-semibold">동작</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.id} className="border-t border-outline" data-testid={`apply-preview-row-${row.id}`}>
              <td className="px-3 py-2 font-mono text-xs text-on-surface">{row.id}</td>
              <td className="px-3 py-2 text-on-surface">{row.action}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
export function ApplySubflowDialog({
  open,
  selection,
  snapshotLibraryRevision,
  onOpenFinalize,
  onClose,
}: {
  open: boolean;
  selection: SelectionScope | null;
  snapshotLibraryRevision: number;
  onOpenFinalize: () => void;
  onClose: () => void;
}) {
  const bridge = useBridge();
  const refreshSnapshot = useRefreshSnapshot();
  const [step, setStep] = useState<Step>("preview");
  const [previewState, setPreviewState] = useState<PreviewState>({ status: "idle" });
  const [previewError, setPreviewError] = useState<string | null>(null);
  const [applyError, setApplyError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [applyOutcome, setApplyOutcome] = useState<ApplyOutcome | null>(null);
  /** Token last issued by preview; used for discard on close even when UI shows stale. */
  const [activePreviewToken, setActivePreviewToken] = useState<string | null>(null);

  const effectivePreviewState = useMemo((): PreviewState => {
    if (previewState.status !== "ready" || !selection) {
      return previewState;
    }
    const fp = selectionFingerprint(selection);
    if (fp !== previewState.preview.selectionFingerprint) {
      return { status: "stale", reason: "selection_changed" };
    }
    if (snapshotLibraryRevision !== previewState.preview.libraryRevision) {
      return { status: "stale", reason: "library_changed" };
    }
    return previewState;
  }, [previewState, selection, snapshotLibraryRevision]);

  if (!open || !selection) return null;

  const readyPreview = effectivePreviewState.status === "ready" ? effectivePreviewState.preview : null;
  const operationCount = readyPreview?.summary.operationCount ?? 0;

  const handleClose = async () => {
    if (activePreviewToken && step !== "done") {
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
    setApplyOutcome(null);
    onClose();
  };

  const runPreview = async () => {
    setBusy(true);
    setPreviewError(null);
    setApplyError(null);
    setApplyOutcome(null);
    try {
      const result = await bridge.getMovePreview(selection);
      setActivePreviewToken(result.previewToken);
      setPreviewState({ status: "ready", preview: result });
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
        previewToken: effectivePreviewState.preview.previewToken,
      });
      const opCount = effectivePreviewState.preview.summary.operationCount ?? 0;
      setApplyOutcome({
        operationCount: opCount,
        libraryRevision: effectivePreviewState.preview.libraryRevision,
      });
      setActivePreviewToken(null);
      setPreviewState({ status: "idle" });
      setStep("done");
      await refreshSnapshot();
    } catch (err) {
      const { message, reason, details } = applyErrorMessage(err);
      setApplyError(message);
      if (reason === "APPLY_FAILED" && details?.partialSuccess && (details.succeededCount ?? 0) > 0) {
        void refreshSnapshot();
      }
      if (reason === "STALE_PREVIEW" || reason === "SELECTION_CHANGED") {
        setPreviewState({
          status: "stale",
          reason: reason === "STALE_PREVIEW" ? "library_changed" : "selection_changed",
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
    !previewError &&
    operationCount > 0;

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

        <ol className="mt-4 grid gap-2 md:grid-cols-4">
          {(
            [
              ["preview", "1. Preview", "이동·충돌·대상 검토"],
              ["confirm", "2. Confirm", "파괴적 작업 전 확인"],
              ["apply", "3. Apply", "파일 이동 실행"],
              ["done", "4. Done", "결과 확인"],
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

        {(applyError || effectivePreviewState.status === "error") && step !== "done" && (
          <p className="mt-3 text-sm text-error" data-testid="apply-bridge-error" role="alert">
            {applyError ?? (effectivePreviewState.status === "error" ? effectivePreviewState.message : "")}
          </p>
        )}

        {readyPreview && (step === "confirm" || step === "apply") && !previewError && (
          <>
            <SummaryChips summary={readyPreview.summary} />
            <PreviewRowsTable rows={readyPreview.rows} />
          </>
        )}

        {step === "done" && applyOutcome && (
          <div
            className="mt-4 rounded-md border border-success/40 bg-success/10 p-4 text-sm text-on-surface"
            data-testid="apply-success-panel"
            role="status"
          >
            <p className="font-semibold text-success">적용 완료</p>
            <p className="mt-2">
              <strong>{applyOutcome.operationCount}</strong>건의 파일 이동이 완료되었습니다.
            </p>
            <p className="mt-1 text-on-surface-variant">
              라이브러리 revision이 갱신되었습니다. 검토 그리드는 스냅샷 갱신 후 반영됩니다.
            </p>

          </div>
        )}

        <div className="mt-5 flex justify-end gap-2">
          <button
            type="button"
            onClick={() => void handleClose()}
            className="rounded-md border border-outline px-3 py-2 text-sm font-semibold hover:bg-hover"
          >
            {step === "done" ? "닫기" : "취소"}
          </button>
          {step === "done" && (
            <button
              type="button"
              data-testid="apply-open-finalize"
              onClick={() => {
                void handleClose().then(onOpenFinalize);
              }}
              className="rounded-md bg-secondary px-3 py-2 text-sm font-semibold text-background"
            >
              최종 검증 열기
            </button>
          )}
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
