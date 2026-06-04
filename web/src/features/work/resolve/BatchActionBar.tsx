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
  moveTargetCount = 0,
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
  moveTargetCount?: number;
  previewDisabled?: boolean;
  previewDisabledReason?: string;
}) {
  const batchDisabled = explicitCount === 0 || batchBusy;
  const previewBlocked = previewDisabled || batchBusy;
  const bulkFilterDisabled = bulkQueryDisabled || filteredCount === 0 || batchBusy;
  const canClear = explicitCount > 0 && !batchBusy;
  const selectionControlsDisabled = loadedCount === 0 || batchBusy;

  return (
    <div className="relative z-30 flex shrink-0 flex-col gap-3 border-t border-outline bg-surface px-4 py-3">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div className="min-w-0">
          <p className="text-sm font-semibold text-on-surface" data-testid="batch-workflow-hint">
            {moveTargetCount > 0 ? (
              <>
                승인된 이동 대상{" "}
                <span className="text-primary">{moveTargetCount.toLocaleString()}건</span> (Exact·Near·Relation) —{" "}
                <span className="text-primary">이동 계획 미리보기</span>
              </>
            ) : (
              <>승인된 이동 대상이 없습니다. 스캔을 다시 실행하세요.</>
            )}
          </p>
          <p className="mt-1 text-xs text-on-surface-variant" role="status">
            {moveTargetCount > 0
              ? "승인됐고 keeper(유지)가 아닌 파일은 라이브러리 옆 «이름_duplicate» 폴더로 이동합니다."
              : "승인된 이동 대상이 없습니다. 스캔을 다시 실행하세요."}
            {batchBusy ? (
              <span className="ml-2 font-semibold text-primary">처리 중…</span>
            ) : null}
            {previewDisabledReason ? (
              <span className="mt-1 block text-warning">{previewDisabledReason}</span>
            ) : null}
          </p>
        </div>
        <button
          type="button"
          disabled={previewBlocked}
          title={
            previewDisabledReason ??
            "Exact 이동 대상 전체로 미리보기를 만듭니다. (행을 고르면 선택만 사용)"
          }
          data-testid="batch-preview-open"
          onClick={onPreview}
          className="shrink-0 rounded-md bg-primary px-5 py-2.5 text-sm font-bold text-background hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
        >
          이동 계획 미리보기
        </button>
      </div>

      <p className="text-xs text-muted">
        {selectionLabel} · 필터 {filteredCount.toLocaleString()}건 · 로드{" "}
        {loadedCount.toLocaleString()}건
      </p>

      <details className="group rounded-md border border-outline/80 bg-background/50 text-sm">
        <summary className="cursor-pointer list-none px-3 py-2 font-semibold text-on-surface-variant marker:content-none [&::-webkit-details-marker]:hidden">
          <span className="text-on-surface">예외 처리</span>
          <span className="ml-2 text-xs font-normal text-muted">
            (이동 제외·수동 승인 — 보통은 쓰지 않음)
          </span>
        </summary>
        <div className="flex flex-col gap-2 border-t border-outline px-3 py-2">
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
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              disabled={batchDisabled}
              title={batchDisabled ? BATCH_DISABLED_TOOLTIP : "재검토 후 다시 승인할 때만 사용"}
              data-testid="batch-approve"
              onClick={onApprove}
              className="rounded-md border border-outline px-3 py-1.5 text-xs font-semibold text-on-surface hover:bg-hover disabled:cursor-not-allowed disabled:opacity-50"
            >
              선택 수동 승인
            </button>
            <button
              type="button"
              disabled={batchDisabled}
              title={batchDisabled ? BATCH_DISABLED_TOOLTIP : "선택한 행을 이동 대상에서 제외"}
              data-testid="batch-exclude"
              onClick={onExclude}
              className="rounded-md border border-outline px-3 py-1.5 text-xs font-semibold text-on-surface hover:bg-hover disabled:cursor-not-allowed disabled:opacity-50"
            >
              선택 제외
            </button>
            <button
              type="button"
              disabled={bulkFilterDisabled}
              title={bulkQueryDisabledReason}
              data-testid="batch-approve-all-filtered"
              onClick={onApproveAllFiltered}
              className="rounded-md border border-outline px-3 py-1.5 text-xs font-semibold text-on-surface hover:bg-hover disabled:cursor-not-allowed disabled:opacity-50"
            >
              필터 전체 수동 승인
            </button>
            <button
              type="button"
              disabled={bulkFilterDisabled}
              title={bulkQueryDisabledReason}
              data-testid="batch-exclude-all-filtered"
              onClick={onExcludeAllFiltered}
              className="rounded-md border border-outline px-3 py-1.5 text-xs font-semibold text-on-surface hover:bg-hover disabled:cursor-not-allowed disabled:opacity-50"
            >
              필터 전체 제외
            </button>
          </div>
        </div>
      </details>
    </div>
  );
}
