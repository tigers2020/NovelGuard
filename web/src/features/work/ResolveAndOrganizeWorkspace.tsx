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
import { ResolveGridToolbar } from "./resolve/ResolveGridToolbar";
import { VirtualizedReviewGrid } from "./resolve/VirtualizedReviewGrid";
import { REVIEW_GRID_SIZING_KEY } from "./resolve/reviewGridColumns";
import { mergeReviewColumnVisibility } from "./resolve/reviewGridLayout";
import { DetailPanel } from "./resolve/DetailPanel";
import { BatchActionBar } from "./resolve/BatchActionBar";
import { BulkFilterConfirmDialog } from "./resolve/BulkFilterConfirmDialog";
import {
  bulkMutationChunkCursors,
  bulkMutationTargetCount,
} from "../../constants/reviewBulk";

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
  const [rowTypeFilter, setRowTypeFilter] = useState<"exact" | "near" | "relation" | "all">("all");
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
  const [detailSheetOpen, setDetailSheetOpen] = useState(false);
  const [bulkConfirm, setBulkConfirm] = useState<{
    open: boolean;
    command: "approve" | "exclude";
  }>({ open: false, command: "approve" });
  const [bulkMutating, setBulkMutating] = useState(false);
  const [isWideLayout, setIsWideLayout] = useState(
    () => typeof window !== "undefined" && window.matchMedia("(min-width: 1024px)").matches,
  );
  const detailSeqRef = useRef(0);

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

  const explicitRowIdSet = useMemo(() => new Set(explicitIds), [explicitIds]);

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
      limit: 100,
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

  const selectMasterRow = (row: ReviewRow) => {
    setSelectedRow(row);
    if (!isWideLayout) {
      setDetailSheetOpen(true);
    }
    void loadDetail(row);
  };

  const toggleExplicitRow = (row: ReviewRow) => {
    setExplicitIds((ids) =>
      ids.includes(row.id) ? ids.filter((id) => id !== row.id) : [...ids, row.id],
    );
  };

  const selectAllVisible = useCallback(() => {
    setExplicitIds(rows.map((row) => row.id));
  }, [rows]);

  const selectExactGroupHeaders = useCallback(() => {
    setExplicitIds(
      rows.filter((row) => row.rowKind === "group" && row.type === "exact").map((row) => row.id),
    );
  }, [rows]);

  const clearExplicitSelection = useCallback(() => {
    setExplicitIds([]);
  }, []);

  const allVisibleSelected =
    rows.length > 0 && rows.every((row) => explicitRowIdSet.has(row.id));
  const someVisibleSelected = explicitIds.length > 0;

  const toggleSelectAllVisible = useCallback(() => {
    if (allVisibleSelected) {
      clearExplicitSelection();
    } else {
      selectAllVisible();
    }
  }, [allVisibleSelected, clearExplicitSelection, selectAllVisible]);

  const explicitSelection = useMemo<SelectionScope>(
    () => ({ type: "explicit_rows", rowIds: explicitIds }),
    [explicitIds],
  );

  const previewSelection: SelectionScope =
    explicitIds.length > 0
      ? explicitSelection
      : { type: "current_query", query: currentQuery, excludeRowIds: [] };

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
    if (explicitIds.length > 0) {
      const selected = rows.filter((row) => explicitIds.includes(row.id));
      if (selected.some((row) => row.type === "near")) {
        return "Near duplicate groups are review-only in PR-19 and cannot be applied.";
      }
      if (selected.some((row) => row.type === "relation")) {
        return "Relation groups are review-only in PR-20 and cannot be applied.";
      }
    }
    return reviewOnlyBlockedReason;
  }, [explicitIds, rows, reviewOnlyBlockedReason]);

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

  const runBulkQueryCommand = useCallback(
    async (command: "approve" | "exclude") => {
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
            command,
          });
        }
        await refreshSnapshot();
        await loadPage(null, false);
        setExplicitIds([]);
      } catch (err) {
        setQueryError(err instanceof Error ? err.message : "Review update failed");
      } finally {
        setBulkMutating(false);
        setBulkConfirm((prev) => ({ ...prev, open: false }));
      }
    },
    [bridge, currentQuery, filteredCount, loadPage, refreshSnapshot],
  );

  const selectionLabel =
    explicitIds.length > 0
      ? `${explicitIds.length.toLocaleString()}건 선택`
      : `선택 없음`;

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
        <FacetPanel viewMode={viewMode} onViewModeChange={setViewMode} />
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
            onRetry={() => void loadPage(null, false)}
            onOpenFinalize={onOpenFinalize}
          />
          <VirtualizedReviewGrid
            rows={rows}
            selectedRowId={selectedRow?.id ?? null}
            onSelectRow={selectMasterRow}
            explicitRowIds={explicitRowIdSet}
            onToggleExplicit={toggleExplicitRow}
            allVisibleSelected={allVisibleSelected}
            someVisibleSelected={someVisibleSelected}
            onToggleSelectAllVisible={toggleSelectAllVisible}
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
          <DetailPanel
            className="w-[min(360px,36%)] shrink-0 border-l border-outline"
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
                void loadPage(null, false, selectedRow?.id ?? null);
              } else {
                void loadDetail(selectedRow);
              }
            }}
          />
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
                void loadPage(null, false, selectedRow?.id ?? null);
              } else {
                void loadDetail(selectedRow);
              }
            }}
            onClose={() => setDetailSheetOpen(false)}
          />
        </div>
      )}

      <BatchActionBar
        selectionLabel={selectionLabel}
        filteredCount={filteredCount}
        loadedCount={rows.length}
        explicitCount={explicitIds.length}
        onSelectAllVisible={selectAllVisible}
        onSelectExactGroupHeaders={selectExactGroupHeaders}
        onClearSelection={clearExplicitSelection}
        onApprove={() => void runBatchCommand("approve")}
        onExclude={() => void runBatchCommand("exclude")}
        onApproveAllFiltered={() => setBulkConfirm({ open: true, command: "approve" })}
        onExcludeAllFiltered={() => setBulkConfirm({ open: true, command: "exclude" })}
        bulkQueryDisabled={Boolean(reviewOnlyBlockedReason)}
        bulkQueryDisabledReason={reviewOnlyBlockedReason}
        onPreview={() => onOpenPreview(previewSelection)}
        previewDisabled={Boolean(previewBlockedReason)}
        previewDisabledReason={previewBlockedReason}
      />

      <BulkFilterConfirmDialog
        open={bulkConfirm.open}
        command={bulkConfirm.command}
        filteredCount={filteredCount}
        mutating={bulkMutating}
        onCancel={() => setBulkConfirm((prev) => ({ ...prev, open: false }))}
        onConfirm={() => void runBulkQueryCommand(bulkConfirm.command)}
      />
    </main>
  );
}
