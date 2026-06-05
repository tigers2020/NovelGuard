import type { ReviewRow } from "../../../types/review";

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
