import type { ReviewRow, ReviewRowType } from "../../../types/review";

export type RowTypeFilter = ReviewRowType | "all";

/** Review-only type filters block move preview with a user-facing reason. */
export function reviewOnlyBlockedReasonForFilter(rowTypeFilter: RowTypeFilter): string | undefined {
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
}

/** Mirrors `BuildPreviewPlanUseCase` file-row eligibility for move_duplicate preview. */
export function isExecutableMovePreviewRow(row: ReviewRow): boolean {
  if (row.rowKind !== "file") return false;
  if (row.status === "excluded" || row.status === "conflict") return false;
  if (row.proposedAction === "keep" || row.proposedAction === "ignore") return false;
  if (row.proposedAction === "move_organized") return false;
  return row.proposedAction === "move_duplicate";
}

export function hasExecutableMovePreviewRows(rows: readonly ReviewRow[]): boolean {
  return rows.some(isExecutableMovePreviewRow);
}
