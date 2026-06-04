import type { ReviewRow } from "../../../types/review";
import { fileIdFromReviewRowId } from "./reviewRowSelectionPriority";

const TYPE_RANK: Record<string, number> = {
  exact: 0,
  near: 1,
  relation: 2,
  move_only: 3,
};

export function isApprovedMoveTargetRow(row: ReviewRow): boolean {
  if (row.rowKind !== "file") return false;
  if (row.type !== "exact" && row.type !== "near" && row.type !== "relation") return false;
  if (row.status !== "approved") return false;
  const action = row.proposedAction === "ignore" ? "move_duplicate" : row.proposedAction;
  return action === "move_duplicate";
}

function normalizeMoveRow(row: ReviewRow): ReviewRow {
  if (row.status !== "approved") return row;
  if (row.proposedAction === "ignore") {
    return { ...row, proposedAction: "move_duplicate", targetFolder: row.targetFolder ?? "duplicate/" };
  }
  return row;
}

/** One move row per file; exact duplicate group wins over near/relation rows. */
export function collectCanonicalApprovedMoveTargetRows(rows: readonly ReviewRow[]): ReviewRow[] {
  const approvedByFile = new Map<string, { rank: number; groupId: string; row: ReviewRow }>();

  for (const row of rows) {
    if (row.rowKind !== "file") continue;
    if (row.type !== "exact" && row.type !== "near" && row.type !== "relation") continue;
    if (row.status !== "approved") continue;
    const fileId = fileIdFromReviewRowId(row.id);
    const groupId = row.groupId ?? "";
    if (!fileId) continue;

    const normalized = normalizeMoveRow(row);
    const rank = TYPE_RANK[normalized.type] ?? 99;
    const current = approvedByFile.get(fileId);
    if (
      current === undefined ||
      rank < current.rank ||
      (rank === current.rank && groupId < current.groupId)
    ) {
      approvedByFile.set(fileId, { rank, groupId, row: normalized });
    }
  }

  return [...approvedByFile.values()]
    .filter((entry) => isApprovedMoveTargetRow(entry.row))
    .sort(
      (a, b) =>
        a.rank - b.rank || a.groupId.localeCompare(b.groupId) || a.row.id.localeCompare(b.row.id),
    )
    .map((entry) => entry.row);
}
