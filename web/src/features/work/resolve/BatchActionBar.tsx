const BATCH_DISABLED_TOOLTIP = "행을 선택한 뒤 사용하세요 (v1: explicit selection only)";

export function BatchActionBar({
  selectionLabel,
  filteredCount,
  explicitCount,
  onApprove,
  onExclude,
  onPreview,
  previewDisabled = false,
  previewDisabledReason,
}: {
  selectionLabel: string;
  filteredCount: number;
  explicitCount: number;
  onApprove: () => void;
  onExclude: () => void;
  onPreview: () => void;
  previewDisabled?: boolean;
  previewDisabledReason?: string;
}) {
  const batchDisabled = explicitCount === 0;
  const previewBlocked = previewDisabled || batchDisabled;

  return (
    <div className="relative z-30 flex shrink-0 flex-wrap items-center justify-between gap-3 border-t border-outline bg-surface px-4 py-3">
      <p className="text-sm text-on-surface-variant">
        {selectionLabel} ·{" "}
        <span className="font-semibold text-on-surface">{filteredCount.toLocaleString()}</span>{" "}
        rows in current query
      </p>
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          disabled={batchDisabled}
          title={batchDisabled ? BATCH_DISABLED_TOOLTIP : undefined}
          aria-disabled={batchDisabled}
          data-testid="batch-approve"
          onClick={onApprove}
          className="rounded-md border border-outline px-3 py-2 text-sm font-semibold text-on-surface hover:bg-hover disabled:cursor-not-allowed disabled:opacity-50"
        >
          선택 승인
        </button>
        <button
          type="button"
          disabled={batchDisabled}
          title={batchDisabled ? BATCH_DISABLED_TOOLTIP : undefined}
          aria-disabled={batchDisabled}
          data-testid="batch-exclude"
          onClick={onExclude}
          className="rounded-md border border-outline px-3 py-2 text-sm font-semibold text-on-surface hover:bg-hover disabled:cursor-not-allowed disabled:opacity-50"
        >
          선택 제외
        </button>
        <button
          type="button"
          disabled={previewBlocked}
          title={
            previewDisabledReason ??
            (batchDisabled ? BATCH_DISABLED_TOOLTIP : undefined)
          }
          data-testid="batch-preview-open"
          onClick={onPreview}
          className="rounded-md bg-primary px-3 py-2 text-sm font-semibold text-background hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
        >
          이동 계획 미리보기
        </button>
      </div>
    </div>
  );
}
