import type { ReviewRow, ReviewRowType } from "../../../types/review";

export type RowTypeFilter = ReviewRowType | "all";

/** Block move preview when filter cannot yield executable rows (unless rows already approved). */
export function reviewOnlyBlockedReasonForFilter(
  rowTypeFilter: RowTypeFilter,
  rows?: readonly ReviewRow[],
): string | undefined {
  if (rows && hasExecutableMovePreviewRows(rows)) {
    return undefined;
  }
  if (rowTypeFilter === "near") {
    return "Near 중복은 승인된 이동 대상이 없습니다. 자동 선정·승인 후 미리보기를 사용하세요.";
  }
  if (rowTypeFilter === "relation") {
    return "Relation 그룹은 승인된 이동 대상이 없습니다. 자동 선정·승인 후 미리보기를 사용하세요.";
  }
  if (rowTypeFilter === "all") {
    return "현재 필터에 이동 미리보기 가능한 승인 항목이 없습니다. 자동 선정·승인 후 다시 시도하세요.";
  }
  return undefined;
}

/** Longer inline banner copy for review-only type filters (display-only). */
export function reviewOnlyGuidanceBannerForFilter(rowTypeFilter: RowTypeFilter): string | undefined {
  if (rowTypeFilter === "near") {
    return "Near 중복은 검토 전용입니다. 이동 미리보기·적용은 Exact (이동) 탭에서만 가능합니다.";
  }
  if (rowTypeFilter === "relation") {
    return "Relation 그룹은 검토 전용입니다. 이동 미리보기·적용은 Exact (이동) 탭에서만 가능합니다.";
  }
  if (rowTypeFilter === "all") {
    return "현재 필터에 검토 전용 유형이 포함되어 있습니다. 이동 미리보기는 Exact (이동) 탭을 선택하세요.";
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

export function countExecutableMovePreviewRows(rows: readonly ReviewRow[]): number {
  return rows.filter(isExecutableMovePreviewRow).length;
}
