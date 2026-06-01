const V1_BATCH_STUB_TOOLTIP = "v1: batch approve/exclude not available";

export function BatchActionBar({
  selectionLabel,
  filteredCount,
  onPreview,
}: {
  selectionLabel: string;
  filteredCount: number;
  onPreview: () => void;
}) {
  return (
    <div className="flex shrink-0 flex-wrap items-center justify-between gap-3 border-t border-outline bg-surface px-4 py-3">
      <p className="text-sm text-on-surface-variant">
        {selectionLabel} ·{" "}
        <span className="font-semibold text-on-surface">{filteredCount.toLocaleString()}</span>{" "}
        rows in current query
      </p>
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          disabled
          title={V1_BATCH_STUB_TOOLTIP}
          aria-disabled="true"
          data-testid="batch-approve"
          className="cursor-not-allowed rounded-md border border-outline px-3 py-2 text-sm font-semibold text-muted opacity-50"
        >
          선택 승인
        </button>
        <button
          type="button"
          disabled
          title={V1_BATCH_STUB_TOOLTIP}
          aria-disabled="true"
          data-testid="batch-exclude"
          className="cursor-not-allowed rounded-md border border-outline px-3 py-2 text-sm font-semibold text-muted opacity-50"
        >
          선택 제외
        </button>
        <button
          type="button"
          data-testid="batch-preview-open"
          onClick={onPreview}
          className="rounded-md bg-primary px-3 py-2 text-sm font-semibold text-background hover:opacity-90"
        >
          이동 계획 미리보기
        </button>
      </div>
    </div>
  );
}
