import { StatChip } from "../../../components/ui/StatChip";

export type ResolveRowTypeFilter = "exact" | "near" | "relation" | "all";

const TYPE_FILTERS: { id: ResolveRowTypeFilter; label: string }[] = [
  { id: "exact", label: "Exact (이동)" },
  { id: "near", label: "Near (참고)" },
  { id: "relation", label: "Relation (참고)" },
  { id: "all", label: "All types" },
];

export function ResolveGridToolbar({
  queueCount,
  groupCount,
  conflictCount,
  approvedCount,
  rowTypeFilter,
  onRowTypeFilterChange,
  search,
  onSearchChange,
  loading,
  queryError,
  onRetry,
  onOpenFinalize,
}: {
  queueCount: number;
  groupCount: number;
  conflictCount: number;
  approvedCount: number;
  rowTypeFilter: ResolveRowTypeFilter;
  onRowTypeFilterChange: (id: ResolveRowTypeFilter) => void;
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
        <p className="text-xs font-semibold text-secondary">Resolve & Organize</p>
        <StatChip label="Queue" value={queueCount} tone="warn" />
        <StatChip label="Groups" value={groupCount} />
        <StatChip label="Conflicts" value={conflictCount} tone="danger" />
        <StatChip label="Approved" value={approvedCount} tone="good" />
        <button
          type="button"
          data-testid="resolve-open-finalize"
          className="ml-auto rounded-md border border-outline px-3 py-1.5 text-xs font-semibold text-on-surface hover:bg-hover"
          onClick={onOpenFinalize}
        >
          최종 검증
        </button>
      </div>
      <div className="mt-2 flex flex-wrap items-center gap-2" data-testid="resolve-type-filter">
        {TYPE_FILTERS.map(({ id, label }) => (
          <button
            key={id}
            type="button"
            data-testid={`resolve-type-filter-${id}`}
            onClick={() => onRowTypeFilterChange(id)}
            className={
              rowTypeFilter === id
                ? "rounded-md bg-primary px-3 py-1.5 text-xs font-semibold text-background"
                : "rounded-md border border-outline px-3 py-1.5 text-xs font-semibold text-on-surface hover:bg-hover"
            }
          >
            {label}
          </button>
        ))}
        <input
          value={search}
          onChange={(e) => onSearchChange(e.target.value)}
          placeholder="파일명, keeper, target, type 검색"
          className="min-w-[12rem] flex-1 rounded-md border border-outline bg-background px-3 py-1.5 text-sm text-on-surface outline-none focus:ring-2 focus:ring-primary"
        />
      </div>
      {loading && !queryError && <p className="mt-2 text-xs text-muted">Loading rows…</p>}
      {queryError && (
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
            Retry
          </button>
        </div>
      )}
    </div>
  );
}
