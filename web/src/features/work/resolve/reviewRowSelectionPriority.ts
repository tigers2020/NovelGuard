import type { ReviewRow, ReviewRowType } from "../../../types/review";

const TYPE_RANK: Record<ReviewRowType, number> = {
  exact: 0,
  near: 1,
  relation: 2,
  move_only: 3,
};

export function fileIdFromReviewRowId(rowId: string): string | null {
  if (rowId.startsWith("file:")) {
    const match = rowId.match(/([0-9a-f]{64})$/i);
    return match ? match[1] : null;
  }
  if (rowId.startsWith("row-")) {
    return rowId;
  }
  return null;
}

/** Highest-priority review row id per file (exact > near > relation). */
export function buildPrimaryRowIdByFileId(rows: readonly ReviewRow[]): Map<string, string> {
  const winners = new Map<string, { rank: number; groupId: string; rowId: string }>();

  for (const row of rows) {
    if (row.rowKind !== "file") continue;
    const fileId = fileIdFromReviewRowId(row.id);
    const groupId = row.groupId;
    if (!fileId || !groupId) continue;

    const rank = TYPE_RANK[row.type] ?? 99;
    const current = winners.get(fileId);
    if (
      current === undefined ||
      rank < current.rank ||
      (rank === current.rank && groupId < current.groupId)
    ) {
      winners.set(fileId, { rank, groupId, rowId: row.id });
    }
  }

  return new Map([...winners.entries()].map(([fileId, entry]) => [fileId, entry.rowId]));
}

export function isPrimaryReviewRowForFile(
  row: ReviewRow,
  primaryRowIdByFileId: ReadonlyMap<string, string>,
): boolean {
  if (row.rowKind !== "file") return true;
  const fileId = fileIdFromReviewRowId(row.id);
  if (!fileId) return true;
  const primaryRowId = primaryRowIdByFileId.get(fileId);
  return primaryRowId === undefined || primaryRowId === row.id;
}
