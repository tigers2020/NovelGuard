import type { ReviewRow } from "../../../types/review";

export function fileIdFromReviewRow(rowId: string): string | null {
  if (!rowId.startsWith("file:")) return null;
  const rest = rowId.slice(5);
  if (rest.length < 64) return null;
  const candidate = rest.slice(-64);
  if (!/^[0-9a-f]{64}$/i.test(candidate)) return null;
  return candidate.toLowerCase();
}

export function pickPolicyKeeperFileId(members: ReviewRow[]): string | null {
  const files = members.filter((row) => row.rowKind === "file");
  if (files.length === 0) return null;
  const sorted = [...files].sort((left, right) => {
    const sizeDiff = (right.sizeBytes ?? 0) - (left.sizeBytes ?? 0);
    if (sizeDiff !== 0) return sizeDiff;
    const pathDiff = String(right.path ?? right.name).localeCompare(
      String(left.path ?? left.name),
      "en-US",
    );
    if (pathDiff !== 0) return pathDiff;
    return String(fileIdFromReviewRow(right.id) ?? "").localeCompare(
      String(fileIdFromReviewRow(left.id) ?? ""),
      "en-US",
    );
  });
  return fileIdFromReviewRow(sorted[0]!.id);
}

export type AutoSelectKeepersStats = {
  exactUnreviewed: number;
  nearUnreviewed: number;
  relationUnreviewed: number;
  keeperCount: number;
  moveCandidateCount: number;
  unreviewedFileCount: number;
};

export function buildAutoSelectKeepersStats(rows: ReviewRow[]): AutoSelectKeepersStats {
  const unreviewedFileRows = rows.filter(
    (row) => row.rowKind === "file" && row.status === "unreviewed",
  );
  const groupIds = new Set(
    unreviewedFileRows.map((row) => row.groupId).filter((groupId): groupId is string => Boolean(groupId)),
  );
  const keeperCount = groupIds.size;
  return {
    exactUnreviewed: unreviewedFileRows.filter((row) => row.type === "exact").length,
    nearUnreviewed: unreviewedFileRows.filter((row) => row.type === "near").length,
    relationUnreviewed: unreviewedFileRows.filter((row) => row.type === "relation").length,
    keeperCount,
    moveCandidateCount: Math.max(0, unreviewedFileRows.length - keeperCount),
    unreviewedFileCount: unreviewedFileRows.length,
  };
}
