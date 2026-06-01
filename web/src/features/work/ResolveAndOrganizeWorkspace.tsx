import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useBridge } from "../../app/providers/SnapshotProvider";
import { useSnapshot } from "../../app/providers/SnapshotProvider";
import type { ReviewRow, ReviewRowsQuery, ReviewViewMode } from "../../types/review";
import type { SelectionScope } from "../../types/selection";
import { StatChip } from "../../components/ui/StatChip";
import { FacetPanel } from "./resolve/FacetPanel";
import { VirtualizedReviewGrid } from "./resolve/VirtualizedReviewGrid";
import { DetailPanel } from "./resolve/DetailPanel";
import { BatchActionBar } from "./resolve/BatchActionBar";

export function ResolveAndOrganizeWorkspace({ onOpenPreview }: { onOpenPreview: (selection: SelectionScope) => void }) {
  const bridge = useBridge();
  const snapshot = useSnapshot();
  const resolve = snapshot.work.resolve;

  const [viewMode, setViewMode] = useState<ReviewViewMode>("action");
  const [search, setSearch] = useState("");
  const [rows, setRows] = useState<ReviewRow[]>([]);
  const [filteredCount, setFilteredCount] = useState(0);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [selectedRow, setSelectedRow] = useState<ReviewRow | null>(null);
  const [explicitIds, setExplicitIds] = useState<string[]>([]);

  const currentQuery = useMemo<ReviewRowsQuery>(
    () => ({
      viewMode,
      filters: { search: search || undefined },
      cursor: null,
      limit: 100,
    }),
    [viewMode, search],
  );

  const loadPage = useCallback(
    async (cursor: string | null, append: boolean) => {
      if (append) setLoadingMore(true);
      else setLoading(true);
      try {
        const page = await bridge.queryReviewRows({
          ...currentQuery,
          cursor,
        });
        setFilteredCount(page.pageInfo.totalFiltered);
        setNextCursor(page.pageInfo.nextCursor);
        setRows((prev) => (append ? [...prev, ...page.rows] : page.rows));
        if (!append && page.rows.length > 0) {
          setSelectedRow(page.rows[0]);
        }
      } finally {
        setLoading(false);
        setLoadingMore(false);
      }
    },
    [bridge, currentQuery],
  );

  useEffect(() => {
    setExplicitIds([]);
    void loadPage(null, false);
  }, [loadPage]);

  const loadingMoreRef = useRef(false);
  const handleNearEnd = () => {
    if (!nextCursor || loadingMore || loadingMoreRef.current) return;
    loadingMoreRef.current = true;
    void loadPage(nextCursor, true).finally(() => {
      loadingMoreRef.current = false;
    });
  };

  const toggleSelect = (row: ReviewRow) => {
    setSelectedRow(row);
    setExplicitIds((ids) =>
      ids.includes(row.id) ? ids.filter((id) => id !== row.id) : [...ids, row.id],
    );
  };

  const selection: SelectionScope =
    explicitIds.length > 0
      ? { type: "explicit_rows", rowIds: explicitIds }
      : { type: "current_query", query: currentQuery, excludeRowIds: [] };

  const selectionLabel =
    explicitIds.length > 0
      ? `${explicitIds.length} selected`
      : `${filteredCount} in current filter`;

  return (
    <main className="flex h-full min-h-0 flex-col bg-background">
      <div className="shrink-0 border-b border-outline p-4">
        <p className="text-xs font-semibold text-secondary">Resolve & Organize</p>
        <h1 className="text-xl font-bold text-on-surface">중복 검토와 이동 정리를 한 큐에서 처리</h1>
        <div className="mt-4 grid gap-2 sm:grid-cols-4">
          <StatChip label="Queue" value={resolve.queueCount} tone="warn" />
          <StatChip label="Groups" value={resolve.groupCount} />
          <StatChip label="Conflicts" value={resolve.conflictCount} tone="danger" />
          <StatChip label="Approved" value={resolve.approvedCount} tone="good" />
        </div>
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="파일명, keeper, target, type 검색"
          className="mt-4 w-full rounded-md border border-outline bg-surface px-3 py-2 text-sm text-on-surface outline-none focus:ring-2 focus:ring-primary"
        />
        {loading && <p className="mt-2 text-xs text-muted">Loading rows…</p>}
      </div>

      <div className="flex min-h-0 flex-1">
        <FacetPanel viewMode={viewMode} onViewModeChange={setViewMode} />
        <VirtualizedReviewGrid
          rows={rows}
          selectedRowId={selectedRow?.id ?? null}
          onSelectRow={toggleSelect}
          onNearEnd={handleNearEnd}
          loadingMore={loadingMore}
        />
        <DetailPanel selectedRow={selectedRow} />
      </div>

      <BatchActionBar
        selectionLabel={selectionLabel}
        filteredCount={filteredCount}
        onPreview={() => onOpenPreview(selection)}
      />
    </main>
  );
}
