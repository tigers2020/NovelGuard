import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { SortingState } from "@tanstack/react-table";
import { useBridge, useRefreshSnapshot, useSnapshot } from "../../app/providers/snapshotHooks";
import type {
  DuplicateGroupDetail,
  DuplicateGroupMemberDetail,
  ReviewRow,
  ReviewRowType,
  ReviewRowsQuery,
  ReviewViewMode,
} from "../../types/review";
import { reviewRowGroupId } from "../../types/review";
import type { ReviewDecisionCommand } from "../../types/reviewDecisions";
import type { SelectionScope } from "../../types/selection";
import { StatChip } from "../../components/ui/StatChip";
import { FacetPanel } from "./resolve/FacetPanel";
import { VirtualizedReviewGrid } from "./resolve/VirtualizedReviewGrid";
import { REVIEW_GRID_SIZING_KEY } from "./resolve/reviewGridColumns";
import { mergeReviewColumnVisibility } from "./resolve/reviewGridLayout";
import { DetailPanel } from "./resolve/DetailPanel";
import { BatchActionBar } from "./resolve/BatchActionBar";

function loadColumnSizing(): Record<string, number> {
  try {
    const raw = localStorage.getItem(REVIEW_GRID_SIZING_KEY);
    return raw ? (JSON.parse(raw) as Record<string, number>) : {};
  } catch {
    return {};
  }
}

export function ResolveAndOrganizeWorkspace({ onOpenPreview }: { onOpenPreview: (selection: SelectionScope) => void }) {
  const bridge = useBridge();
  const refreshSnapshot = useRefreshSnapshot();
  const snapshot = useSnapshot();
  const resolve = snapshot.work.resolve;

  const [viewMode, setViewMode] = useState<ReviewViewMode>("action");
  const [rowTypeFilter, setRowTypeFilter] = useState<"exact" | "near" | "all">("exact");
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
  const [columnSizing, setColumnSizing] = useState<Record<string, number>>(loadColumnSizing);
  const [detail, setDetail] = useState<DuplicateGroupDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [detailMutating, setDetailMutating] = useState(false);

  const rowTypeFilterTypes = useMemo((): ReviewRowType[] | undefined => {
    if (rowTypeFilter === "exact") return ["exact"];
    if (rowTypeFilter === "near") return ["near"];
    return ["exact", "near"];
  }, [rowTypeFilter]);

  const currentQuery = useMemo<ReviewRowsQuery>(() => {
    const primary = sorting[0];
    return {
      viewMode,
      filters: { search: search || undefined, types: rowTypeFilterTypes },
      cursor: null,
      limit: 100,
      sort: primary
        ? { field: primary.id, direction: primary.desc ? "desc" : "asc" }
        : undefined,
    };
  }, [viewMode, search, sorting, rowTypeFilterTypes]);

  const loadDetail = useCallback(
    async (row: ReviewRow | null) => {
      const gid = row ? reviewRowGroupId(row) : null;
      if (!gid) {
        setDetail(null);
        setDetailError(null);
        return;
      }
      setDetailLoading(true);
      try {
        setDetailError(null);
        setDetail(await bridge.getDuplicateGroupDetail(gid));
      } catch (err) {
        setDetailError(err instanceof Error ? err.message : "Failed to load group detail");
        setDetail(null);
      } finally {
        setDetailLoading(false);
      }
    },
    [bridge],
  );

  const loadPage = useCallback(
    async (cursor: string | null, append: boolean, preserveRowId?: string | null) => {
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
          const next =
            preserveRowId != null
              ? (page.rows.find((r) => r.id === preserveRowId) ?? page.rows[0])
              : page.rows[0];
          setSelectedRow(next);
          void loadDetail(next);
        } else if (!append) {
          setSelectedRow(null);
          setDetail(null);
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
    [bridge, currentQuery, loadDetail],
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
    void loadDetail(row);
    setExplicitIds((ids) =>
      ids.includes(row.id) ? ids.filter((id) => id !== row.id) : [...ids, row.id],
    );
  };

  const explicitSelection = useMemo<SelectionScope>(
    () => ({ type: "explicit_rows", rowIds: explicitIds }),
    [explicitIds],
  );

  const previewSelection: SelectionScope =
    explicitIds.length > 0
      ? explicitSelection
      : { type: "current_query", query: currentQuery, excludeRowIds: [] };

  const previewIncludesNear = useMemo(() => {
    if (explicitIds.length > 0) {
      return rows.some((row) => explicitIds.includes(row.id) && row.type === "near");
    }
    return rowTypeFilter !== "exact";
  }, [explicitIds, rows, rowTypeFilter]);

  const runDetailReviewCommand = useCallback(
    async (
      command: ReviewDecisionCommand,
      selection: SelectionScope,
      keeperFileId?: string,
    ) => {
      const preserveRowId = selectedRow?.id ?? null;
      setDetailMutating(true);
      try {
        setQueryError(null);
        await bridge.updateReviewDecisions({ selection, command, keeperFileId });
        await refreshSnapshot();
        await loadPage(null, false, preserveRowId);
      } catch (err) {
        setQueryError(err instanceof Error ? err.message : "Review update failed");
      } finally {
        setDetailMutating(false);
      }
    },
    [bridge, loadPage, refreshSnapshot, selectedRow?.id],
  );

  const runBatchCommand = useCallback(
    async (command: "approve" | "exclude") => {
      if (explicitIds.length === 0) return;
      try {
        setQueryError(null);
        await bridge.updateReviewDecisions({ selection: explicitSelection, command });
        await refreshSnapshot();
        await loadPage(null, false);
      } catch (err) {
        setQueryError(err instanceof Error ? err.message : "Review update failed");
      }
    },
    [bridge, explicitIds, explicitSelection, loadPage, refreshSnapshot],
  );

  const selectionLabel =
    explicitIds.length > 0
      ? `${explicitIds.length} selected`
      : `${filteredCount} in current filter`;

  const handleSetKeeper = (member: DuplicateGroupMemberDetail) => {
    if (member.isKeeper) return;
    void runDetailReviewCommand(
      "setKeeper",
      { type: "explicit_rows", rowIds: [member.rowId] },
      member.fileId,
    );
  };

  const handleMarkConflict = () => {
    if (!selectedRow) return;
    void runDetailReviewCommand("markConflict", {
      type: "explicit_rows",
      rowIds: [selectedRow.id],
    });
  };

  const handleReset = () => {
    if (!selectedRow) return;
    void runDetailReviewCommand("reset", {
      type: "explicit_rows",
      rowIds: [selectedRow.id],
    });
  };

  return (
    <main
      className="flex h-full min-h-0 flex-col overflow-hidden bg-background"
      data-testid="resolve-workspace"
    >
      <div className="shrink-0 border-b border-outline p-4">
        <p className="text-xs font-semibold text-secondary">Resolve & Organize</p>
        <h1 className="text-xl font-bold text-on-surface">중복 검토와 이동 정리를 한 큐에서 처리</h1>
        <div className="mt-4 grid gap-2 sm:grid-cols-4">
          <StatChip label="Queue" value={resolve.queueCount} tone="warn" />
          <StatChip label="Groups" value={resolve.groupCount} />
          <StatChip label="Conflicts" value={resolve.conflictCount} tone="danger" />
          <StatChip label="Approved" value={resolve.approvedCount} tone="good" />
        </div>
        <div className="mt-4 flex flex-wrap gap-2" data-testid="resolve-type-filter">
          {(
            [
              ["exact", "Exact only"],
              ["near", "Near only"],
              ["all", "Exact + Near"],
            ] as const
          ).map(([id, label]) => (
            <button
              key={id}
              type="button"
              data-testid={`resolve-type-filter-${id}`}
              onClick={() => setRowTypeFilter(id)}
              className={
                rowTypeFilter === id
                  ? "rounded-md bg-primary px-3 py-1.5 text-xs font-semibold text-background"
                  : "rounded-md border border-outline px-3 py-1.5 text-xs font-semibold text-on-surface hover:bg-hover"
              }
            >
              {label}
            </button>
          ))}
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

      <div className="relative z-0 flex min-h-0 min-w-0 flex-1 overflow-hidden">
        <FacetPanel viewMode={viewMode} onViewModeChange={setViewMode} />
        <div className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden">
          <VirtualizedReviewGrid
            rows={rows}
            selectedRowId={selectedRow?.id ?? null}
            onSelectRow={toggleSelect}
            onNearEnd={handleNearEnd}
            loadingMore={loadingMore}
            sorting={sorting}
            onSortingChange={setSorting}
            columnSizing={columnSizing}
            onColumnSizingChange={(next) => {
              setColumnSizing(next);
              localStorage.setItem(REVIEW_GRID_SIZING_KEY, JSON.stringify(next));
            }}
            mergeColumnVisibility={mergeReviewColumnVisibility}
            enableColumnResize
          />
        </div>
        <DetailPanel
          selectedRow={selectedRow}
          detail={detail}
          loading={detailLoading}
          error={detailError}
          mutating={detailMutating}
          onSetKeeper={handleSetKeeper}
          onMarkConflict={handleMarkConflict}
          onReset={handleReset}
          onRefreshDetail={() => {
            void loadPage(null, false);
            void loadDetail(selectedRow);
          }}
        />
      </div>

      <BatchActionBar
        selectionLabel={selectionLabel}
        filteredCount={filteredCount}
        explicitCount={explicitIds.length}
        onApprove={() => void runBatchCommand("approve")}
        onExclude={() => void runBatchCommand("exclude")}
        onPreview={() => onOpenPreview(previewSelection)}
        previewDisabled={previewIncludesNear}
        previewDisabledReason={
          previewIncludesNear
            ? "Near duplicate groups are review-only in PR-19 and cannot be applied."
            : undefined
        }
      />
    </main>
  );
}
