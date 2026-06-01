import { useMemo } from "react";
import { VirtualizedDataGrid } from "../../../components/grid/VirtualizedDataGrid";
import type { QualityRow } from "../../../types/quality";
import { buildQualityGridColumns } from "./qualityGridColumns";

export function QualityIssueGrid({
  rows,
  selectedId,
  onSelect,
  onNearEnd,
  loadingMore,
}: {
  rows: QualityRow[];
  selectedId: string | null;
  onSelect: (row: QualityRow) => void;
  onNearEnd?: () => void;
  loadingMore?: boolean;
}) {
  const columns = useMemo(() => buildQualityGridColumns(), []);

  return (
    <VirtualizedDataGrid
      testId="quality-issue-grid"
      headerTestIdPrefix="quality-grid-header"
      data={rows}
      columns={columns}
      getRowId={(row) => row.id}
      selectedRowId={selectedId}
      onSelectRow={onSelect}
      estimateRowHeight={44}
      overscan={6}
      onNearEnd={onNearEnd}
      loadingMore={loadingMore}
    />
  );
}
