export function BatchActionBar({
  filteredCount,
  loadedCount,
  loadingAll = false,
  reviewOnlyGuidance,
  onExcludeAllFiltered,
  onAutoSelectKeepers,
  autoSelectDisabled = false,
  autoSelectDisabledReason,
  bulkQueryDisabled = false,
  bulkQueryDisabledReason,
  onPreview,
  previewDisabled = false,
  previewDisabledReason,
  previewLabel = "이동 계획 미리보기",
}: {
  filteredCount: number;
  loadedCount: number;
  loadingAll?: boolean;
  reviewOnlyGuidance?: string;
  onExcludeAllFiltered: () => void;
  onAutoSelectKeepers: () => void;
  autoSelectDisabled?: boolean;
  autoSelectDisabledReason?: string;
  bulkQueryDisabled?: boolean;
  bulkQueryDisabledReason?: string;
  onPreview: () => void;
  previewDisabled?: boolean;
  previewDisabledReason?: string;
  previewLabel?: string;
}) {
  const bulkFilterDisabled = bulkQueryDisabled || filteredCount === 0;

  return (
    <div className="shrink-0 border-t border-outline bg-surface">
      {reviewOnlyGuidance ? (
        <div className="px-4 pt-3">
          <div
            className="rounded-md border border-secondary/40 bg-secondary/10 p-3 text-sm text-on-surface"
            role="status"
            data-testid="batch-review-only-banner"
          >
            {reviewOnlyGuidance}
          </div>
        </div>
      ) : null}
      <div className="relative z-30 flex flex-wrap items-center justify-between gap-3 px-4 py-3">
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
            disabled={autoSelectDisabled}
            title={autoSelectDisabledReason}
            data-testid="batch-auto-select-keepers"
            onClick={onAutoSelectKeepers}
            className="rounded-md border border-outline px-3 py-2 text-sm font-semibold text-on-surface hover:bg-hover disabled:cursor-not-allowed disabled:opacity-50"
          >
            미검토 자동 선정·승인
          </button>
          <button
            type="button"
            disabled={previewDisabled}
            title={previewDisabledReason}
            data-testid="batch-preview-open"
            onClick={onPreview}
            className="rounded-md border border-outline px-3 py-2 text-sm font-semibold text-on-surface hover:bg-hover disabled:cursor-not-allowed disabled:opacity-50"
          >
            {previewLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
