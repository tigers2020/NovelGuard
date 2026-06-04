import { useCallback, useMemo } from "react";
import type { OnChangeFn, SortingState, VisibilityState } from "@tanstack/react-table";
import { VirtualizedDataGrid } from "../../../components/grid/VirtualizedDataGrid";
import type { QualityRow, QualityRowsPage } from "../../../types/quality";
import { buildQualityGridColumns } from "./qualityGridColumns";
import { mergeQualityColumnVisibility } from "./qualityGridLayout";

const OPTIONAL_COLUMN_IDS = ["severity", "encoding", "integrity", "path", "issueType"] as const;

export function VirtualizedQualityGrid({
  rows,
  selectedRowId,
  onSelectRow,
  onNearEnd,
  loadingMore,
  sorting,
  onSortingChange,
  userColumnVisibility,
  columnSizing,
  onColumnSizingChange,
  filteredCount,
  tabSummary,
}: {
  rows: QualityRow[];
  selectedRowId: string | null;
  onSelectRow: (row: QualityRow) => void;
  onNearEnd?: () => void;
  loadingMore?: boolean;
  sorting: SortingState;
  onSortingChange: OnChangeFn<SortingState>;
  userColumnVisibility: VisibilityState;
  columnSizing?: Record<string, number>;
  onColumnSizingChange?: (next: Record<string, number>) => void;
  filteredCount: number;
  tabSummary: QualityRowsPage["summary"];
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
        <div
          className="flex flex-wrap items-center justify-between gap-2 border-t border-outline bg-surface px-4 py-2 text-xs text-muted"
          data-testid="quality-grid-footer"
        >
          <span>
            필터{" "}
            <span className="font-semibold text-on-surface">
              {filteredCount.toLocaleString()}
            </span>
            건 · 로드{" "}
            <span className="font-semibold text-on-surface">{rows.length.toLocaleString()}</span>
            건
            {tabSummary.warningCount > 0 || tabSummary.errorCount > 0
              ? ` · 경고 ${tabSummary.warningCount.toLocaleString()} · 오류 ${tabSummary.errorCount.toLocaleString()}`
              : ""}
            {loadingMore ? " · loading…" : ""}
          </span>
        </div>
      }
    />
  );
}
