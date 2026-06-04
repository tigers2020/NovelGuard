import type { ReviewViewMode } from "../../../types/review";
import { StatChip } from "../../../components/ui/StatChip";

const LIST_VIEWS: { id: ReviewViewMode; label: string }[] = [
  { id: "move", label: "이동 대상" },
  { id: "all", label: "전체" },
];

export function ResolveGridToolbar({
  viewMode,
  onViewModeChange,
  groupCount,
  conflictCount,
  moveTargetCount,
  listFilteredCount,
  search,
  onSearchChange,
  loading,
  queryError,
  onRetry,
  onOpenFinalize,
}: {
  viewMode: ReviewViewMode;
  onViewModeChange: (mode: ReviewViewMode) => void;
  groupCount: number;
  conflictCount: number;
  moveTargetCount: number;
  listFilteredCount: number;
  search: string;
  onSearchChange: (value: string) => void;
  loading: boolean;
  queryError: string | null;
  onRetry: () => void;
  onOpenFinalize: () => void;
}) {
  return (
    <div className="shrink-0 border-b border-outline bg-surface px-3 py-2">
      <div className="flex flex-wrap items-center gap-2">
        <p className="text-xs font-semibold text-secondary">검토·정리</p>
        <StatChip label="이동 대상" value={moveTargetCount} tone={moveTargetCount > 0 ? "good" : "warn"} />
        <StatChip label="그룹" value={groupCount} />
        {conflictCount > 0 ? <StatChip label="충돌" value={conflictCount} tone="danger" /> : null}
        <StatChip label="목록" value={listFilteredCount} />
        <button
          type="button"
          data-testid="resolve-open-finalize"
          className="ml-auto rounded-md border border-outline px-3 py-1.5 text-xs font-semibold text-on-surface hover:bg-hover"
          onClick={onOpenFinalize}
        >
          최종 검증
        </button>
      </div>
      <div className="mt-2 flex flex-wrap items-center gap-2">
        <div
          className="inline-flex rounded-md border border-outline p-0.5"
          role="tablist"
          aria-label="목록 보기"
        >
          {LIST_VIEWS.map(({ id, label }) => (
            <button
              key={id}
              type="button"
              role="tab"
              aria-selected={viewMode === id}
              data-testid={`resolve-facet-${id}`}
              onClick={() => onViewModeChange(id)}
              className={
                viewMode === id
                  ? "rounded px-3 py-1.5 text-xs font-semibold bg-primary text-background"
                  : "rounded px-3 py-1.5 text-xs font-semibold text-on-surface hover:bg-hover"
              }
            >
              {label}
            </button>
          ))}
        </div>
        <input
          value={search}
          onChange={(e) => onSearchChange(e.target.value)}
          placeholder="이름·경로 검색"
          className="min-w-[12rem] flex-1 rounded-md border border-outline bg-background px-3 py-1.5 text-sm text-on-surface outline-none focus:ring-2 focus:ring-primary"
        />
      </div>
      {loading && !queryError ? <p className="mt-2 text-xs text-muted">불러오는 중…</p> : null}
      {queryError ? (
        <div
          className="mt-2 flex items-center justify-between rounded-md border border-error/40 bg-error/10 px-3 py-2 text-sm text-error"
          data-testid="resolve-query-error"
        >
          <span>{queryError}</span>
          <button
            type="button"
            data-testid="resolve-query-retry"
            className="rounded-md border border-outline px-2 py-1 text-xs font-semibold text-on-surface"
            onClick={onRetry}
          >
            다시 시도
          </button>
        </div>
      ) : null}
    </div>
  );
}
