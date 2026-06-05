import { useCallback, useMemo } from "react";
import type { OnChangeFn, SortingState, VisibilityState } from "@tanstack/react-table";
import { VirtualizedDataGrid } from "../../../components/grid/VirtualizedDataGrid";
import type { QualityRow } from "../../../types/quality";
import { buildQualityGridColumns } from "./qualityGridColumns";
import { mergeQualityColumnVisibility } from "./qualityGridLayout";

const OPTIONAL_COLUMN_IDS = ["severity", "encoding", "integrity", "path", "issueType"] as const;

export function VirtualizedQualityGrid({
  rows,
  filteredCount,
  selectedRowId,
  onSelectRow,
  onNearEnd,
  loadingMore,
  sorting,
  onSortingChange,
  userColumnVisibility,
  columnSizing,
  onColumnSizingChange,
}: {
  rows: QualityRow[];
  filteredCount: number;
  selectedRowId: string | null;
  onSelectRow: (row: QualityRow) => void;
  onNearEnd?: () => void;
  loadingMore?: boolean;
  sorting: SortingState;
  onSortingChange: OnChangeFn<SortingState>;
  userColumnVisibility: VisibilityState;
  columnSizing?: Record<string, number>;
  onColumnSizingChange?: (next: Record<string, number>) => void;
}) {
  const columns = useMemo(() => buildQualityGridColumns(), []);

  const mergeEffectiveVisibility = useCallback(
    (containerWidth: number) => {
      const responsive = mergeQualityColumnVisibility(containerWidth);
      const merged: VisibilityState = { name: true };
      for (const key of OPTIONAL_COLUMN_IDS) {
        merged[key] = userColumnVisibility[key] !== false && responsive[key] !== false;
      }
      return merged;
    },
    [userColumnVisibility],
  );

  return (
    <VirtualizedDataGrid
      testId="quality-issue-grid"
      headerTestIdPrefix="quality-grid-header"
      data={rows}
      columns={columns}
      getRowId={(row) => row.id}
      selectedRowId={selectedRowId}
      onSelectRow={onSelectRow}
      sorting={sorting}
      onSortingChange={onSortingChange}
      mergeColumnVisibility={mergeEffectiveVisibility}
      columnSizing={columnSizing}
      onColumnSizingChange={onColumnSizingChange}
      enableColumnResize
      onNearEnd={onNearEnd}
      loadingMore={loadingMore}
      footer={
        <div className="flex items-center justify-between border-t border-outline bg-surface px-4 py-2 text-xs text-muted">
          <span data-testid="quality-grid-row-count">
            {rows.length.toLocaleString()} loaded · {filteredCount.toLocaleString()} filtered
            {loadingMore ? " · loading…" : ""}
          </span>
        </div>
      }
    />
  );
}
