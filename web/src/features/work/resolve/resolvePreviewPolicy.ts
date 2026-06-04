import type { ReviewRow, ReviewRowsQuery } from "../../../types/review";
import type { SelectionScope } from "../../../types/selection";
import {
  collectCanonicalApprovedMoveTargetRows,
  isApprovedMoveTargetRow,
} from "./canonicalMoveTargets";
import { fileIdFromReviewRowId } from "./reviewRowSelectionPriority";

export { isApprovedMoveTargetRow };

export function buildPreviewBlockedReason(options: {
  moveTargetCount: number;
}): string | undefined {
  if (options.moveTargetCount === 0) {
    return "승인된 이동 대상이 없습니다. 스캔을 다시 실행하세요.";
  }
  return undefined;
}

export function buildPreviewSelection(options: {
  explicitIds: string[];
  visibleRows: ReviewRow[];
  previewQuery: ReviewRowsQuery;
}): SelectionScope {
  const { explicitIds, visibleRows, previewQuery } = options;

  if (explicitIds.length > 0) {
    const selectedFileIds = new Set(
      visibleRows
        .filter((row) => explicitIds.includes(row.id))
        .map((row) => fileIdFromReviewRowId(row.id))
        .filter((id): id is string => id !== null),
    );
    const moveIds = collectCanonicalApprovedMoveTargetRows(visibleRows)
      .filter((row) => {
        const fileId = fileIdFromReviewRowId(row.id);
        return fileId !== null && selectedFileIds.has(fileId);
      })
      .map((row) => row.id);
    if (moveIds.length > 0) {
      return { type: "explicit_rows", rowIds: moveIds };
    }
  }

  return {
    type: "current_query",
    query: {
      ...previewQuery,
      viewMode: "move",
      filters: {
        ...previewQuery.filters,
        types: ["exact", "near", "relation"],
      },
    },
    excludeRowIds: [],
  };
}

export function isRowSelectableForBatch(row: ReviewRow, isPrimary: boolean): boolean {
  if (!isPrimary) return false;
  if (row.rowKind === "group") return false;
  return isApprovedMoveTargetRow(row);
}
