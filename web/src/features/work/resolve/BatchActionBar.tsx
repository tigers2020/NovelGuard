export function BatchActionBar({
  filteredCount,
  loadedCount,
  loadingAll = false,
  onExcludeAllFiltered,
  bulkQueryDisabled = false,
  bulkQueryDisabledReason,
  onPreview,
  previewDisabled = false,
  previewDisabledReason,
  reviewOnlyGuidance,
}: {
  filteredCount: number;
  loadedCount: number;
  loadingAll?: boolean;
  onExcludeAllFiltered: () => void;
  bulkQueryDisabled?: boolean;
  bulkQueryDisabledReason?: string;
  onPreview: () => void;
  previewDisabled?: boolean;
  previewDisabledReason?: string;
  reviewOnlyGuidance?: string;
}) {
  const bulkFilterDisabled = bulkQueryDisabled || filteredCount === 0;

  return (
    <div className="relative z-30 shrink-0 border-t border-outline bg-surface">
      {reviewOnlyGuidance && (
        <div
          className="border-b border-outline px-4 py-3 text-sm text-on-surface"
          data-testid="batch-review-only-banner"
          role="status"
        >
          <div className="rounded-md border border-secondary/40 bg-secondary/10 p-3">
            {reviewOnlyGuidance}
          </div>
        </div>
      )}
      <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-3">
      <div className="flex flex-wrap items-center gap-2">
        <p className="text-sm text-on-surface-variant">
          필터{" "}
          <span className="font-semibold text-on-surface">{filteredCount.toLocaleString()}</span>
          건 · 로드{" "}
          <span className="font-semibold text-on-surface">{loadedCount.toLocaleString()}</span>건
        </p>
        {loadingAll && (
          <span data-testid="batch-loading-all" className="text-xs text-primary">
            전체 로드 중…
          </span>
        )}
        {!loadingAll && loadedCount < filteredCount && (
          <span data-testid="batch-partial-load-warning" className="text-xs text-warn">
            일부만 로드됨
          </span>
        )}
      </div>
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
    </div>
  );
}
