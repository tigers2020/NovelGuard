import { useMemo } from "react";
import type { OnChangeFn, SortingState } from "@tanstack/react-table";
import type { VisibilityState } from "@tanstack/react-table";
import { VirtualizedDataGrid } from "../../../components/grid/VirtualizedDataGrid";
import type { ReviewRow } from "../../../types/review";
import { buildReviewGridColumns, reviewGridAllColumnsVisible } from "./reviewGridColumns";

export function VirtualizedReviewGrid({
  rows,
  selectedRowId,
  onSelectRow,
  explicitRowIds,
  onToggleExplicit,
  allVisibleSelected,
  someVisibleSelected,
  onToggleSelectAllVisible,
  onNearEnd,
  loadingMore,
  sorting,
  onSortingChange,
  columnSizing,
  onColumnSizingChange,
  mergeColumnVisibility,
  enableColumnResize,
}: {
  rows: ReviewRow[];
  selectedRowId: string | null;
  onSelectRow: (row: ReviewRow) => void;
  explicitRowIds?: ReadonlySet<string>;
  onToggleExplicit?: (row: ReviewRow) => void;
  allVisibleSelected?: boolean;
  someVisibleSelected?: boolean;
  onToggleSelectAllVisible?: () => void;
  onNearEnd?: () => void;
  loadingMore?: boolean;
  sorting: SortingState;
  onSortingChange: OnChangeFn<SortingState>;
  columnSizing?: Record<string, number>;
  onColumnSizingChange?: (next: Record<string, number>) => void;
  mergeColumnVisibility?: (containerWidth: number) => VisibilityState;
  enableColumnResize?: boolean;
}) {
  const columns = useMemo(
    () =>
      buildReviewGridColumns(
        explicitRowIds && onToggleExplicit
          ? {
              explicitRowIds,
              onToggleExplicit,
              allVisibleSelected,
              someVisibleSelected,
              onToggleSelectAllVisible,
            }
          : undefined,
      ),
    [
      explicitRowIds,
      onToggleExplicit,
      allVisibleSelected,
      someVisibleSelected,
      onToggleSelectAllVisible,
    ],
  );

  return (
    <VirtualizedDataGrid
      testId="resolve-review-grid"
      headerTestIdPrefix="resolve-grid-header"
      data={rows}
      columns={columns}
      getRowId={(row) => row.id}
      selectedRowId={selectedRowId}
      onSelectRow={onSelectRow}
      sorting={sorting}
      onSortingChange={onSortingChange}
      columnVisibility={reviewGridAllColumnsVisible}
      columnSizing={columnSizing}
      onColumnSizingChange={onColumnSizingChange}
      mergeColumnVisibility={mergeColumnVisibility}
      enableColumnResize={enableColumnResize}
      onNearEnd={onNearEnd}
      loadingMore={loadingMore}
      footer={
        <div className="flex items-center justify-between border-t border-outline bg-surface px-4 py-2 text-xs text-muted">
          <span>
            {rows.length.toLocaleString()} loaded rows
            {loadingMore ? " · loading…" : ""}
          </span>
        </div>
      }
    />
  );
}
