const BATCH_DISABLED_TOOLTIP = "행을 선택한 뒤 사용하세요.";

export function BatchActionBar({
  selectionLabel,
  filteredCount,
  loadedCount,
  explicitCount,
  batchBusy = false,
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
  batchBusy?: boolean;
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
  const batchDisabled = explicitCount === 0 || batchBusy;
  const previewBlocked = previewDisabled || batchDisabled;
  const bulkFilterDisabled = bulkQueryDisabled || filteredCount === 0 || batchBusy;
  const canClear = explicitCount > 0 && !batchBusy;
  const selectionControlsDisabled = loadedCount === 0 || batchBusy;

  return (
    <div className="relative z-30 flex shrink-0 flex-col gap-2 border-t border-outline bg-surface px-4 py-3">
      {explicitCount > 0 ? (
        <p
          className="text-xs text-on-surface-variant"
          data-testid="batch-workflow-hint"
          role="status"
        >
          <span className="font-semibold text-on-surface">다음 단계:</span>{" "}
          <span className="text-on-surface">① 선택 승인</span>
          <span className="text-muted"> (제안대로 확정)</span>
          {" → "}
          <span className="text-on-surface">② 이동 계획 미리보기</span>
          {" → "}
          <span className="text-on-surface">③ 상단 전체 실행</span>
          {batchBusy ? (
            <span className="ml-2 font-semibold text-primary">처리 중…</span>
          ) : null}
          {previewDisabledReason ? (
            <span className="mt-1 block text-warning">{previewDisabledReason}</span>
          ) : null}
        </p>
      ) : null}

      <div className="flex flex-wrap items-center justify-between gap-3">
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
              disabled={selectionControlsDisabled}
              className="rounded-md border border-outline px-2 py-1 text-xs font-semibold text-on-surface hover:bg-hover disabled:cursor-not-allowed disabled:opacity-50"
              onClick={onSelectAllVisible}
            >
              전체 선택 (로드됨)
            </button>
            <button
              type="button"
              data-testid="batch-select-exact-groups"
              disabled={selectionControlsDisabled}
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
            title={
              batchBusy
                ? "승인 처리 중입니다."
                : batchDisabled
                  ? BATCH_DISABLED_TOOLTIP
                  : "선택한 행의 제안(이동·유지)을 승인합니다."
            }
            aria-disabled={batchDisabled}
            data-testid="batch-approve"
            onClick={onApprove}
            className="rounded-md border border-primary/50 bg-primary/10 px-3 py-2 text-sm font-semibold text-primary hover:bg-primary/20 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {batchBusy ? "처리 중…" : "① 선택 승인"}
          </button>
          <button
            type="button"
            disabled={batchDisabled}
            title={batchDisabled ? BATCH_DISABLED_TOOLTIP : "선택한 행을 검토 대상에서 제외합니다."}
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
            className="rounded-md border border-outline px-3 py-2 text-sm font-semibold text-on-surface hover:bg-hover disabled:cursor-not-allowed disabled:opacity-50"
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
              (batchDisabled ? BATCH_DISABLED_TOOLTIP : "승인 후 이동·삭제 계획을 확인합니다.")
            }
            data-testid="batch-preview-open"
            onClick={onPreview}
            className="rounded-md bg-primary px-3 py-2 text-sm font-semibold text-background hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
          >
            ② 이동 계획 미리보기
          </button>
        </div>
      </div>
    </div>
  );
}
