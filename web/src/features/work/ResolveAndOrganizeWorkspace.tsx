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
import { FacetPanel } from "./resolve/FacetPanel";
import {
  loadResolveFacetExpanded,
  persistResolveFacetExpanded,
} from "./resolve/resolveFacetStorage";
import { ResolveGridToolbar } from "./resolve/ResolveGridToolbar";
import { VirtualizedReviewGrid } from "./resolve/VirtualizedReviewGrid";
import { REVIEW_GRID_SIZING_KEY } from "./resolve/reviewGridColumns";
import { mergeReviewColumnVisibility } from "./resolve/reviewGridLayout";
import { DetailPanel } from "./resolve/DetailPanel";
import { BatchActionBar } from "./resolve/BatchActionBar";
import { BulkFilterConfirmDialog } from "./resolve/BulkFilterConfirmDialog";
import { hasExecutableMovePreviewRows } from "./resolve/previewEligibility";
import {
  bulkMutationChunkCursors,
  bulkMutationTargetCount,
} from "../../constants/reviewBulk";
import { MAX_QUERY_LIMIT } from "../../contracts/reviewPageContract";

function loadColumnSizing(): Record<string, number> {
  try {
    const raw = localStorage.getItem(REVIEW_GRID_SIZING_KEY);
    return raw ? (JSON.parse(raw) as Record<string, number>) : {};
  } catch {
    return {};
  }
}

export function ResolveAndOrganizeWorkspace({
  onOpenPreview,
  onOpenFinalize,
}: {
  onOpenPreview: (selection: SelectionScope) => void;
  onOpenFinalize: () => void;
}) {
  const bridge = useBridge();
  const refreshSnapshot = useRefreshSnapshot();
  const snapshot = useSnapshot();
  const resolve = snapshot.work.resolve;

  const [viewMode, setViewMode] = useState<ReviewViewMode>("action");
  const [facetExpanded, setFacetExpanded] = useState(() => loadResolveFacetExpanded());

  const handleFacetExpandedChange = (next: boolean) => {
    setFacetExpanded(next);
    persistResolveFacetExpanded(next);
  };
  const [rowTypeFilter, setRowTypeFilter] = useState<"exact" | "near" | "relation" | "all">("all");
  const [search, setSearch] = useState("");
  const [rows, setRows] = useState<ReviewRow[]>([]);
  const [filteredCount, setFilteredCount] = useState(0);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [loadingAll, setLoadingAll] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [selectedRow, setSelectedRow] = useState<ReviewRow | null>(null);
  const [queryError, setQueryError] = useState<string | null>(null);
  const [sorting, setSorting] = useState<SortingState>([]);
  const [columnSizing, setColumnSizing] = useState<Record<string, number>>(loadColumnSizing);
  const [detail, setDetail] = useState<DuplicateGroupDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [detailMutating, setDetailMutating] = useState(false);
  const [detailSheetOpen, setDetailSheetOpen] = useState(false);
  const [bulkExcludeConfirmOpen, setBulkExcludeConfirmOpen] = useState(false);
  const [bulkMutating, setBulkMutating] = useState(false);
  const [isWideLayout, setIsWideLayout] = useState(
    () => typeof window !== "undefined" && window.matchMedia("(min-width: 1024px)").matches,
  );
  const detailSeqRef = useRef(0);
  const loadSeqRef = useRef(0);

  useEffect(() => {
    const media = window.matchMedia("(min-width: 1024px)");
    const onChange = () => {
      setIsWideLayout(media.matches);
      if (media.matches) {
        setDetailSheetOpen(false);
      }
    };
    media.addEventListener("change", onChange);
    return () => media.removeEventListener("change", onChange);
  }, []);

  const rowTypeFilterTypes = useMemo((): ReviewRowType[] | undefined => {
    if (rowTypeFilter === "exact") return ["exact"];
    if (rowTypeFilter === "near") return ["near"];
    if (rowTypeFilter === "relation") return ["relation"];
    return ["exact", "near", "relation"];
  }, [rowTypeFilter]);

  const currentQuery = useMemo<ReviewRowsQuery>(() => {
    const primary = sorting[0];
    return {
      viewMode,
      filters: { search: search || undefined, types: rowTypeFilterTypes },
      cursor: null,
      limit: MAX_QUERY_LIMIT,
      sort: primary
        ? { field: primary.id, direction: primary.desc ? "desc" : "asc" }
        : undefined,
    };
  }, [viewMode, search, sorting, rowTypeFilterTypes]);

  const loadDetail = useCallback(
    async (row: ReviewRow | null) => {
      const seq = ++detailSeqRef.current;
      const gid = row ? reviewRowGroupId(row) : null;
      if (!gid) {
        if (seq !== detailSeqRef.current) return;
        setDetail(null);
        setDetailError(null);
        return;
      }
      setDetailLoading(true);
      try {
        setDetailError(null);
        const next = await bridge.getDuplicateGroupDetail(gid);
        if (seq !== detailSeqRef.current) return;
        setDetail(next);
      } catch (err) {
        if (seq !== detailSeqRef.current) return;
        setDetailError(err instanceof Error ? err.message : "Failed to load group detail");
        setDetail(null);
      } finally {
        if (seq === detailSeqRef.current) {
          setDetailLoading(false);
        }
      }
    },
    [bridge],
  );

  const loadAllFiltered = useCallback(
    async (preserveRowId?: string | null) => {
      const seq = ++loadSeqRef.current;
      setLoading(true);
      setLoadingAll(true);
      setQueryError(null);
      setRows([]);
      setNextCursor(null);

      let cursor: string | null = null;
      let accumulated: ReviewRow[] = [];

      try {
        while (true) {
          if (seq !== loadSeqRef.current) return;
          const page = await bridge.queryReviewRows({ ...currentQuery, cursor });
          if (seq !== loadSeqRef.current) return;

          accumulated = accumulated.concat(page.rows);
          cursor = page.pageInfo.nextCursor;

          setRows(accumulated);
          setFilteredCount(page.pageInfo.totalFiltered);
          setNextCursor(cursor);

          if (!cursor || accumulated.length >= page.pageInfo.totalFiltered) break;
        }

        if (seq !== loadSeqRef.current) return;
        setNextCursor(null);

        if (preserveRowId != null) {
          const rebound = accumulated.find((r) => r.id === preserveRowId) ?? null;
          setSelectedRow(rebound);
          void loadDetail(rebound);
        } else {
          setSelectedRow(null);
          setDetail(null);
          setDetailError(null);
        }
      } catch (err) {
        if (seq !== loadSeqRef.current) return;
        setQueryError(err instanceof Error ? err.message : "Failed to load rows");
        setRows([]);
        setFilteredCount(0);
        setNextCursor(null);
      } finally {
        if (seq === loadSeqRef.current) {
          setLoading(false);
          setLoadingAll(false);
        }
      }
    },
    [bridge, currentQuery, loadDetail],
  );

  useEffect(() => {
    const frame = requestAnimationFrame(() => {
      void loadAllFiltered();
    });
    return () => cancelAnimationFrame(frame);
  }, [loadAllFiltered]);

  const loadPage = useCallback(
    async (cursor: string | null) => {
      setLoadingMore(true);
      try {
        const page = await bridge.queryReviewRows({
          ...currentQuery,
          cursor,
        });
        setFilteredCount(page.pageInfo.totalFiltered);
        setNextCursor(page.pageInfo.nextCursor);
        setRows((prev) => [...prev, ...page.rows]);
      } catch (err) {
        setQueryError(err instanceof Error ? err.message : "Failed to load rows");
      } finally {
        setLoadingMore(false);
      }
    },
    [bridge, currentQuery],
  );

  const loadingMoreRef = useRef(false);
  const handleNearEnd = () => {
    if (loadingAll || loading || !nextCursor || rows.length >= filteredCount) return;
    if (loadingMore || loadingMoreRef.current) return;
    loadingMoreRef.current = true;
    void loadPage(nextCursor).finally(() => {
      loadingMoreRef.current = false;
    });
  };

  const clearDetailSelection = useCallback(() => {
    detailSeqRef.current += 1;
    setSelectedRow(null);
    setDetail(null);
    setDetailError(null);
    setDetailLoading(false);
  }, []);

  const selectMasterRow = (row: ReviewRow) => {
    if (selectedRow?.id === row.id) {
      clearDetailSelection();
      return;
    }
    setSelectedRow(row);
    if (!isWideLayout) {
      setDetailSheetOpen(true);
    }
    void loadDetail(row);
  };

  const previewSelection: SelectionScope = useMemo(
    () => ({ type: "current_query", query: currentQuery, excludeRowIds: [] }),
    [currentQuery],
  );

  const hasExecutableRows = useMemo(() => hasExecutableMovePreviewRows(rows), [rows]);

  const reviewOnlyBlockedReason = useMemo(() => {
    if (rowTypeFilter === "near") {
      return "Near 중복은 검토 전용이며 일괄 적용할 수 없습니다.";
    }
    if (rowTypeFilter === "relation") {
      return "Relation 그룹은 검토 전용이며 일괄 적용할 수 없습니다.";
    }
    if (rowTypeFilter === "all") {
      return "현재 필터에 검토 전용 유형이 포함되어 있습니다. Exact만 선택하세요.";
    }
    return undefined;
  }, [rowTypeFilter]);

  const previewBlockedReason = useMemo(() => {
    if (reviewOnlyBlockedReason) return reviewOnlyBlockedReason;
    if (filteredCount === 0) {
      return "현재 필터에 표시된 항목이 없습니다.";
    }
    if (!hasExecutableRows) {
      return "현재 필터에 이동 미리보기 가능한 항목이 없습니다. Exact 이동 대상을 승인한 뒤 다시 시도하세요.";
    }
    return undefined;
  }, [filteredCount, hasExecutableRows, reviewOnlyBlockedReason]);

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
        await loadAllFiltered(preserveRowId);
      } catch (err) {
        setQueryError(err instanceof Error ? err.message : "Review update failed");
      } finally {
        setDetailMutating(false);
      }
    },
    [bridge, loadAllFiltered, refreshSnapshot, selectedRow?.id],
  );

  const runBulkExcludeFiltered = useCallback(async () => {
    const targetCount = bulkMutationTargetCount(filteredCount);
    if (targetCount === 0) return;
    setBulkMutating(true);
    try {
      setQueryError(null);
      const cursors = bulkMutationChunkCursors(targetCount);
      for (const cursor of cursors) {
        await bridge.updateReviewDecisions({
          selection: {
            type: "current_query",
            query: { ...currentQuery, cursor },
            excludeRowIds: [],
          },
          command: "exclude",
        });
      }
      await refreshSnapshot();
      await loadAllFiltered();
    } catch (err) {
      setQueryError(err instanceof Error ? err.message : "Review update failed");
    } finally {
      setBulkMutating(false);
      setBulkExcludeConfirmOpen(false);
    }
  }, [bridge, currentQuery, filteredCount, loadAllFiltered, refreshSnapshot]);

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
      <div className="relative z-0 flex min-h-0 min-w-0 flex-1 overflow-hidden">
        <FacetPanel
          viewMode={viewMode}
          onViewModeChange={setViewMode}
          expanded={facetExpanded}
          onExpandedChange={handleFacetExpandedChange}
        />
        <div className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden">
          {!isWideLayout && selectedRow && (
            <div className="flex shrink-0 items-center justify-between gap-2 border-b border-outline bg-surface px-3 py-2">
              <p className="truncate text-xs text-on-surface-variant">
                선택: <span className="font-semibold text-on-surface">{selectedRow.name}</span>
              </p>
              <button
                type="button"
                data-testid="resolve-detail-sheet-open"
                className="rounded-md bg-primary px-3 py-1.5 text-xs font-semibold text-background"
                onClick={() => setDetailSheetOpen(true)}
              >
                상세 보기
              </button>
            </div>
          )}
          <ResolveGridToolbar
            queueCount={resolve.queueCount}
            groupCount={resolve.groupCount}
            conflictCount={resolve.conflictCount}
            approvedCount={resolve.approvedCount}
            rowTypeFilter={rowTypeFilter}
            onRowTypeFilterChange={setRowTypeFilter}
            search={search}
            onSearchChange={setSearch}
            loading={loading}
            queryError={queryError}
            onRetry={() => void loadAllFiltered()}
            onOpenFinalize={onOpenFinalize}
          />
          <VirtualizedReviewGrid
            rows={rows}
            selectedRowId={selectedRow?.id ?? null}
            onSelectRow={selectMasterRow}
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
        {isWideLayout && (
          <div
            data-testid="resolve-detail-drawer"
            data-state={selectedRow ? "open" : "closed"}
            className={`shrink-0 overflow-hidden border-l border-outline transition-[max-width] duration-300 ease-out ${
              selectedRow ? "max-w-[min(360px,36vw)]" : "max-w-0 border-l-0"
            }`}
          >
            {selectedRow && (
              <DetailPanel
                className="h-full w-[min(360px,36vw)]"
                selectedRow={selectedRow}
                detail={detail}
                loading={detailLoading}
                error={detailError}
                mutating={detailMutating}
                onSetKeeper={handleSetKeeper}
                onMarkConflict={handleMarkConflict}
                onReset={handleReset}
                onRefreshDetail={() => {
                  if (detail?.status === "not_found") {
                    void loadAllFiltered(selectedRow?.id ?? null);
                  } else {
                    void loadDetail(selectedRow);
                  }
                }}
                onClose={clearDetailSelection}
              />
            )}
          </div>
        )}
      </div>

      {!isWideLayout && detailSheetOpen && (
        <div
          className="fixed inset-0 z-40 flex flex-col bg-background/95 backdrop-blur-sm"
          data-testid="resolve-detail-sheet"
          role="dialog"
          aria-modal="true"
        >
          <DetailPanel
            className="h-full"
            selectedRow={selectedRow}
            detail={detail}
            loading={detailLoading}
            error={detailError}
            mutating={detailMutating}
            onSetKeeper={handleSetKeeper}
            onMarkConflict={handleMarkConflict}
            onReset={handleReset}
            onRefreshDetail={() => {
              if (detail?.status === "not_found") {
                void loadAllFiltered(selectedRow?.id ?? null);
              } else {
                void loadDetail(selectedRow);
              }
            }}
            onClose={() => setDetailSheetOpen(false)}
          />
        </div>
      )}

      <BatchActionBar
        filteredCount={filteredCount}
        loadedCount={rows.length}
        loadingAll={loadingAll}
        onExcludeAllFiltered={() => setBulkExcludeConfirmOpen(true)}
        bulkQueryDisabled={Boolean(reviewOnlyBlockedReason)}
        bulkQueryDisabledReason={reviewOnlyBlockedReason}
        onPreview={() => onOpenPreview(previewSelection)}
        previewDisabled={Boolean(previewBlockedReason)}
        previewDisabledReason={previewBlockedReason}
      />

      <BulkFilterConfirmDialog
        open={bulkExcludeConfirmOpen}
        filteredCount={filteredCount}
        mutating={bulkMutating}
        onCancel={() => setBulkExcludeConfirmOpen(false)}
        onConfirm={() => void runBulkExcludeFiltered()}
      />
    </main>
  );
}
