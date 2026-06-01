import { useMemo } from "react";
import type { OnChangeFn, SortingState, VisibilityState } from "@tanstack/react-table";
import { VirtualizedDataGrid } from "../../../components/grid/VirtualizedDataGrid";
import type { ReviewRow } from "../../../types/review";
import { buildReviewGridColumns } from "./reviewGridColumns";

export function VirtualizedReviewGrid({
  rows,
  selectedRowId,
  onSelectRow,
  onNearEnd,
  loadingMore,
  sorting,
  onSortingChange,
  columnVisibility,
  onColumnVisibilityChange,
}: {
  rows: ReviewRow[];
  selectedRowId: string | null;
  onSelectRow: (row: ReviewRow) => void;
  onNearEnd?: () => void;
  loadingMore?: boolean;
  sorting: SortingState;
  onSortingChange: OnChangeFn<SortingState>;
  columnVisibility: VisibilityState;
  onColumnVisibilityChange: OnChangeFn<VisibilityState>;
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
      columnVisibility={columnVisibility}
      onColumnVisibilityChange={onColumnVisibilityChange}
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
