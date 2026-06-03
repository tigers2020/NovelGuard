const BATCH_DISABLED_TOOLTIP = "행을 선택한 뒤 사용하세요.";

export function BatchActionBar({
  selectionLabel,
  filteredCount,
  loadedCount,
  explicitCount,
  onSelectAllVisible,
  onSelectExactGroupHeaders,
  onClearSelection,
  onApprove,
  onExclude,
  onApproveAllFiltered,
  onExcludeAllFiltered,
  bulkQueryDisabled = false,
  bulkQueryDisabledReason,
  onPreview,
  previewDisabled = false,
  previewDisabledReason,
}: {
  selectionLabel: string;
  filteredCount: number;
  loadedCount: number;
  explicitCount: number;
  onSelectAllVisible: () => void;
  onSelectExactGroupHeaders: () => void;
  onClearSelection: () => void;
  onApprove: () => void;
  onExclude: () => void;
  onApproveAllFiltered: () => void;
  onExcludeAllFiltered: () => void;
  bulkQueryDisabled?: boolean;
  bulkQueryDisabledReason?: string;
  onPreview: () => void;
  previewDisabled?: boolean;
  previewDisabledReason?: string;
}) {
  const batchDisabled = explicitCount === 0;
  const previewBlocked = previewDisabled || batchDisabled;
  const bulkFilterDisabled = bulkQueryDisabled || filteredCount === 0;
  const canClear = explicitCount > 0;

  return (
    <div className="relative z-30 flex shrink-0 flex-wrap items-center justify-between gap-3 border-t border-outline bg-surface px-4 py-3">
      <div className="flex min-w-0 flex-1 flex-col gap-2 sm:flex-row sm:flex-wrap sm:items-center">
        <p className="text-sm text-on-surface-variant">
          {selectionLabel} · 필터{" "}
          <span className="font-semibold text-on-surface">{filteredCount.toLocaleString()}</span>
          건 · 로드{" "}
          <span className="font-semibold text-on-surface">{loadedCount.toLocaleString()}</span>건
        </p>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            data-testid="batch-select-all-visible"
            disabled={loadedCount === 0}
            className="rounded-md border border-outline px-2 py-1 text-xs font-semibold text-on-surface hover:bg-hover disabled:cursor-not-allowed disabled:opacity-50"
            onClick={onSelectAllVisible}
          >
            보이는 행 전체 선택
          </button>
          <button
            type="button"
            data-testid="batch-select-exact-groups"
            disabled={loadedCount === 0}
            className="rounded-md border border-outline px-2 py-1 text-xs font-semibold text-on-surface hover:bg-hover disabled:cursor-not-allowed disabled:opacity-50"
            onClick={onSelectExactGroupHeaders}
          >
            Exact 그룹 헤더 선택
          </button>
          {canClear ? (
            <button
              type="button"
              data-testid="batch-clear-selection"
              className="rounded-md border border-outline px-2 py-1 text-xs font-semibold text-on-surface hover:bg-hover"
              onClick={onClearSelection}
            >
              선택 해제
            </button>
          ) : null}
        </div>
      </div>
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
          disabled={bulkFilterDisabled}
          title={bulkQueryDisabledReason}
          data-testid="batch-approve-all-filtered"
          onClick={onApproveAllFiltered}
          className="rounded-md border border-primary/50 px-3 py-2 text-sm font-semibold text-primary hover:bg-primary/10 disabled:cursor-not-allowed disabled:opacity-50"
        >
          필터 전체 승인
        </button>
        <button
          type="button"
          disabled={bulkFilterDisabled}
          title={bulkQueryDisabledReason}
          data-testid="batch-exclude-all-filtered"
          onClick={onExcludeAllFiltered}
          className="rounded-md border border-outline px-3 py-2 text-sm font-semibold text-on-surface hover:bg-hover disabled:cursor-not-allowed disabled:opacity-50"
        >
          필터 전체 제외
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
