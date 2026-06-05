export function BatchActionBar({
  filteredCount,
  loadedCount,
  onExcludeAllFiltered,
  bulkQueryDisabled = false,
  bulkQueryDisabledReason,
  onPreview,
  previewDisabled = false,
  previewDisabledReason,
}: {
  filteredCount: number;
  loadedCount: number;
  onExcludeAllFiltered: () => void;
  bulkQueryDisabled?: boolean;
  bulkQueryDisabledReason?: string;
  onPreview: () => void;
  previewDisabled?: boolean;
  previewDisabledReason?: string;
}) {
  const bulkFilterDisabled = bulkQueryDisabled || filteredCount === 0;

  return (
    <div className="relative z-30 flex shrink-0 flex-wrap items-center justify-between gap-3 border-t border-outline bg-surface px-4 py-3">
      <p className="text-sm text-on-surface-variant">
        필터{" "}
        <span className="font-semibold text-on-surface">{filteredCount.toLocaleString()}</span>
        건 · 로드{" "}
        <span className="font-semibold text-on-surface">{loadedCount.toLocaleString()}</span>건
      </p>
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          disabled={bulkFilterDisabled}
          title={bulkQueryDisabledReason}
          data-testid="batch-exclude-all-filtered"
          onClick={onExcludeAllFiltered}
          className="rounded-md border border-outline px-3 py-2 text-sm font-semibold text-on-surface hover:bg-hover disabled:cursor-not-allowed disabled:opacity-50"
        >
          현재 필터 결과 제외
        </button>
        <button
          type="button"
          disabled={previewDisabled}
          title={previewDisabledReason}
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
