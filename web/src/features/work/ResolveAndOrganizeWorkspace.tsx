import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { SortingState, VisibilityState } from "@tanstack/react-table";
import { useBridge, useSnapshot } from "../../app/providers/snapshotHooks";
import type { ReviewRow, ReviewRowsQuery, ReviewViewMode } from "../../types/review";
import type { SelectionScope } from "../../types/selection";
import { ColumnChooser } from "../../components/grid/ColumnChooser";
import { StatChip } from "../../components/ui/StatChip";
import { FacetPanel } from "./resolve/FacetPanel";
import { VirtualizedReviewGrid } from "./resolve/VirtualizedReviewGrid";
import {
  REVIEW_GRID_STORAGE_KEY,
  defaultReviewColumnVisibility,
  optionalReviewColumnKeys,
} from "./resolve/reviewGridColumns";
import { DetailPanel } from "./resolve/DetailPanel";
import { BatchActionBar } from "./resolve/BatchActionBar";

function loadColumnVisibility(): VisibilityState {
  try {
    const raw = localStorage.getItem(REVIEW_GRID_STORAGE_KEY);
    return raw
      ? { ...defaultReviewColumnVisibility, ...JSON.parse(raw) }
      : defaultReviewColumnVisibility;
  } catch {
    return defaultReviewColumnVisibility;
  }
}

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
  const [queryError, setQueryError] = useState<string | null>(null);
  const [sorting, setSorting] = useState<SortingState>([]);
  const [columnVisibility, setColumnVisibility] = useState<VisibilityState>(loadColumnVisibility);

  const currentQuery = useMemo<ReviewRowsQuery>(() => {
    const primary = sorting[0];
    return {
      viewMode,
      filters: { search: search || undefined },
      cursor: null,
      limit: 100,
      sort: primary
        ? { field: primary.id, direction: primary.desc ? "desc" : "asc" }
        : undefined,
    };
  }, [viewMode, search, sorting]);

  const loadPage = useCallback(
    async (cursor: string | null, append: boolean) => {
      if (!append) {
        setExplicitIds([]);
      }
      if (append) setLoadingMore(true);
      else setLoading(true);
      try {
        setQueryError(null);
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
      } catch (err) {
        setQueryError(err instanceof Error ? err.message : "Failed to load rows");
        if (!append) {
          setRows([]);
          setFilteredCount(0);
        }
      } finally {
        setLoading(false);
        setLoadingMore(false);
      }
    },
    [bridge, currentQuery],
  );

  useEffect(() => {
    const frame = requestAnimationFrame(() => {
      void loadPage(null, false);
    });
    return () => cancelAnimationFrame(frame);
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
    <main className="flex h-full min-h-0 flex-col bg-background" data-testid="resolve-workspace">
      <div className="shrink-0 border-b border-outline p-4">
        <p className="text-xs font-semibold text-secondary">Resolve & Organize</p>
        <h1 className="text-xl font-bold text-on-surface">중복 검토와 이동 정리를 한 큐에서 처리</h1>
        <div className="mt-4 flex flex-wrap items-center justify-between gap-2">
          <div className="grid gap-2 sm:grid-cols-4">
            <StatChip label="Queue" value={resolve.queueCount} tone="warn" />
            <StatChip label="Groups" value={resolve.groupCount} />
            <StatChip label="Conflicts" value={resolve.conflictCount} tone="danger" />
            <StatChip label="Approved" value={resolve.approvedCount} tone="good" />
          </div>
          <ColumnChooser
            visibility={columnVisibility}
            optionalKeys={optionalReviewColumnKeys}
            onChange={(key, visible) => {
              setColumnVisibility((prev) => {
                const next = { ...prev, [key]: visible };
                localStorage.setItem(REVIEW_GRID_STORAGE_KEY, JSON.stringify(next));
                return next;
              });
            }}
          />
        </div>
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="파일명, keeper, target, type 검색"
          className="mt-4 w-full rounded-md border border-outline bg-surface px-3 py-2 text-sm text-on-surface outline-none focus:ring-2 focus:ring-primary"
        />
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
              onClick={() => void loadPage(null, false)}
            >
              Retry
            </button>
          </div>
        )}
      </div>

      <div className="flex min-h-0 flex-1">
        <FacetPanel viewMode={viewMode} onViewModeChange={setViewMode} />
        <VirtualizedReviewGrid
          rows={rows}
          selectedRowId={selectedRow?.id ?? null}
          onSelectRow={toggleSelect}
          onNearEnd={handleNearEnd}
          loadingMore={loadingMore}
          sorting={sorting}
          onSortingChange={setSorting}
          columnVisibility={columnVisibility}
          onColumnVisibilityChange={setColumnVisibility}
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
