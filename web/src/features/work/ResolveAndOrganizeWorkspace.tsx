import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { REVIEW_MAX_QUERY_LIMIT } from "../../contracts/reviewPageContract";
import type { SortingState } from "@tanstack/react-table";
import { useBridge, useRefreshSnapshot, useSnapshot } from "../../app/providers/snapshotHooks";
import type {
  DuplicateGroupDetail,
  DuplicateGroupMemberDetail,
  ReviewRow,
  ReviewRowsQuery,
  ReviewViewMode,
} from "../../types/review";
import { reviewRowGroupId } from "../../types/review";
import type { ReviewDecisionCommand } from "../../types/reviewDecisions";
import type { SelectionScope } from "../../types/selection";
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
  chunkExplicitRowIds,
} from "../../constants/reviewBulk";
import {
  buildPreviewBlockedReason,
  buildPreviewSelection,
  isRowSelectableForBatch,
} from "./resolve/resolvePreviewPolicy";
import {
  buildPrimaryRowIdByFileId,
  isPrimaryReviewRowForFile,
} from "./resolve/reviewRowSelectionPriority";

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

  const [viewMode, setViewMode] = useState<ReviewViewMode>("move");
  const [search, setSearch] = useState("");
  const [rows, setRows] = useState<ReviewRow[]>([]);
  const [filteredCount, setFilteredCount] = useState(0);
  const [loading, setLoading] = useState(false);
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
  const [batchMutating, setBatchMutating] = useState(false);
  const detailSeqRef = useRef(0);

  const explicitRowIdSet = useMemo(() => new Set(explicitIds), [explicitIds]);
  const primaryRowIdByFileId = useMemo(() => buildPrimaryRowIdByFileId(rows), [rows]);

  const currentQuery = useMemo<ReviewRowsQuery>(() => {
    const primary = sorting[0];
    return {
      viewMode,
      filters: {
        search: search || undefined,
        types: ["exact", "near", "relation"],
      },
      cursor: null,
      limit: REVIEW_MAX_QUERY_LIMIT,
      sort: primary
        ? { field: primary.id, direction: primary.desc ? "desc" : "asc" }
        : undefined,
    };
  }, [viewMode, search, sorting]);

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

  const loadRows = useCallback(
    async (preserveRowId?: string | null) => {
      setExplicitIds([]);
      setLoading(true);
      try {
        setQueryError(null);
        const page = await bridge.queryReviewRows(currentQuery);
        setFilteredCount(page.pageInfo.totalFiltered);
        setRows(page.rows);

        if (preserveRowId != null) {
          const next = page.rows.find((r) => r.id === preserveRowId) ?? null;
          if (next) {
            setSelectedRow(next);
            void loadDetail(next);
            return;
          }
        }

        setSelectedRow(null);
        setDetail(null);
        setDetailSheetOpen(false);
      } catch (err) {
        setQueryError(err instanceof Error ? err.message : "Failed to load rows");
        setRows([]);
        setFilteredCount(0);
        setSelectedRow(null);
        setDetail(null);
        setDetailSheetOpen(false);
      } finally {
        setLoading(false);
      }
    },
    [bridge, currentQuery, loadDetail],
  );

  useEffect(() => {
    const frame = requestAnimationFrame(() => {
      void loadRows();
    });
    return () => cancelAnimationFrame(frame);
  }, [loadRows]);

  const closeDetailSheet = useCallback(() => {
    setDetailSheetOpen(false);
  }, []);

  const selectMasterRow = (row: ReviewRow) => {
    if (selectedRow?.id === row.id && detailSheetOpen) {
      closeDetailSheet();
      return;
    }
    setSelectedRow(row);
    setDetailSheetOpen(true);
    void loadDetail(row);
  };

  const toggleExplicitRow = (row: ReviewRow) => {
    if (!isPrimaryReviewRowForFile(row, primaryRowIdByFileId)) {
      return;
    }
    setExplicitIds((ids) =>
      ids.includes(row.id) ? ids.filter((id) => id !== row.id) : [...ids, row.id],
    );
  };

  const selectAllVisible = useCallback(() => {
    setExplicitIds(
      rows
        .filter((row) =>
          isRowSelectableForBatch(row, isPrimaryReviewRowForFile(row, primaryRowIdByFileId)),
        )
        .map((row) => row.id),
    );
  }, [primaryRowIdByFileId, rows]);

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

  const previewQuery = useMemo<ReviewRowsQuery>(
    () => ({
      ...currentQuery,
      viewMode: "move",
    }),
    [currentQuery],
  );

  const previewSelection = useMemo(
    () =>
      buildPreviewSelection({
        explicitIds,
        visibleRows: rows,
        previewQuery,
      }),
    [explicitIds, previewQuery, rows],
  );

  const previewBlockedReason = useMemo(
    () => buildPreviewBlockedReason({ moveTargetCount: resolve.moveTargetCount }),
    [resolve.moveTargetCount],
  );

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
        await loadRows(preserveRowId);
      } catch (err) {
        setQueryError(err instanceof Error ? err.message : "Review update failed");
      } finally {
        setDetailMutating(false);
      }
    },
    [bridge, loadRows, refreshSnapshot, selectedRow?.id],
  );

  const runBatchCommand = useCallback(
    async (command: "approve" | "exclude") => {
      if (explicitIds.length === 0) return;
      setBatchMutating(true);
      try {
        setQueryError(null);
        let totalUpdated = 0;
        for (const rowIds of chunkExplicitRowIds(explicitIds)) {
          const result = await bridge.updateReviewDecisions({
            selection: { type: "explicit_rows", rowIds },
            command,
          });
          totalUpdated += result.updatedCount;
        }
        if (totalUpdated === 0) {
          setQueryError(
            "선택한 행에 승인·제외가 적용되지 않았습니다. Exact·Near·Relation 그룹 행인지 확인하세요.",
          );
          return;
        }
        await refreshSnapshot();
        await loadRows();
        closeDetailSheet();
      } catch (err) {
        setQueryError(err instanceof Error ? err.message : "Review update failed");
      } finally {
        setBatchMutating(false);
      }
    },
    [bridge, closeDetailSheet, explicitIds, loadRows, refreshSnapshot],
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
        await loadRows();
        setExplicitIds([]);
        closeDetailSheet();
      } catch (err) {
        setQueryError(err instanceof Error ? err.message : "Review update failed");
      } finally {
        setBulkMutating(false);
        setBulkConfirm((prev) => ({ ...prev, open: false }));
      }
    },
    [bridge, closeDetailSheet, currentQuery, filteredCount, loadRows, refreshSnapshot],
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

  const refreshDetail = () => {
    if (detail?.status === "not_found") {
      void loadRows(selectedRow?.id ?? null);
    } else {
      void loadDetail(selectedRow);
    }
  };

  return (
    <main
      className="flex h-full min-h-0 flex-col overflow-hidden bg-background"
      data-testid="resolve-workspace"
    >
      <div className="relative z-0 flex min-h-0 min-w-0 flex-1 overflow-hidden">
        <div className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden">
          <ResolveGridToolbar
            viewMode={viewMode}
            onViewModeChange={setViewMode}
            groupCount={resolve.groupCount}
            conflictCount={resolve.conflictCount}
            moveTargetCount={resolve.moveTargetCount}
            listFilteredCount={filteredCount}
            search={search}
            onSearchChange={setSearch}
            loading={loading}
            queryError={queryError}
            onRetry={() => void loadRows()}
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
            isRowCheckEnabled={(row) =>
              isRowSelectableForBatch(row, isPrimaryReviewRowForFile(row, primaryRowIdByFileId))
            }
            filteredCount={filteredCount}
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
      </div>

      {detailSheetOpen && (
        <>
          <button
            type="button"
            aria-label="Close detail panel"
            className="fixed inset-0 z-40 bg-background/50 backdrop-blur-[2px]"
            data-testid="resolve-detail-backdrop"
            onClick={closeDetailSheet}
          />
          <div
            className="fixed inset-y-0 right-0 z-50 flex w-[min(400px,92vw)] flex-col border-l border-outline bg-background shadow-2xl transition-transform duration-300 ease-out motion-reduce:transition-none"
            data-testid="resolve-detail-sheet"
            role="dialog"
            aria-modal="true"
            aria-label="Evidence and move detail"
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
              onRefreshDetail={refreshDetail}
              onClose={closeDetailSheet}
            />
          </div>
        </>
      )}

      <BatchActionBar
        selectionLabel={selectionLabel}
        filteredCount={filteredCount}
        loadedCount={rows.length}
        explicitCount={explicitIds.length}
        batchBusy={batchMutating || bulkMutating}
        onSelectAllVisible={selectAllVisible}
        onSelectExactGroupHeaders={selectExactGroupHeaders}
        onClearSelection={clearExplicitSelection}
        onApprove={() => void runBatchCommand("approve")}
        onExclude={() => void runBatchCommand("exclude")}
        onApproveAllFiltered={() => setBulkConfirm({ open: true, command: "approve" })}
        onExcludeAllFiltered={() => setBulkConfirm({ open: true, command: "exclude" })}
        bulkQueryDisabled={false}
        bulkQueryDisabledReason={undefined}
        moveTargetCount={resolve.moveTargetCount}
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
