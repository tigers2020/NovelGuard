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
  onNearEnd?: () => void;
  loadingMore?: boolean;
  sorting: SortingState;
  onSortingChange: OnChangeFn<SortingState>;
  columnSizing?: Record<string, number>;
  onColumnSizingChange?: (next: Record<string, number>) => void;
  mergeColumnVisibility?: (containerWidth: number) => VisibilityState;
  enableColumnResize?: boolean;
}) {
  const columns = useMemo(() => buildReviewGridColumns(), []);

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
    />
  );
}
