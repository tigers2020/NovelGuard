import { bulkMutationTargetCount, MAX_REVIEW_MUTATIONS } from "../../../constants/reviewBulk";
import type { ReviewRow } from "../../../types/review";

export interface AutoSelectSummary {
  unreviewedCount: number;
  keeperCount: number;
  moveCandidateCount: number;
  exactCount: number;
  nearCount: number;
  relationCount: number;
  capped: boolean;
  mutationTargetCount: number;
  partialLoad: boolean;
  keeperPreviewUsesMtime: boolean;
  samples?: {
    keepers: string[];
    moveCandidates: string[];
    exact: string[];
    near: string[];
    relation: string[];
  };
}

function isUnreviewedFile(row: ReviewRow): boolean {
  return row.rowKind === "file" && row.status === "unreviewed";
}

export function pickKeeperPreviewId(members: ReviewRow[]): string | undefined {
  if (members.length === 0) return undefined;
  const sorted = [...members].sort((left, right) => {
    const sizeDiff = (right.sizeBytes ?? 0) - (left.sizeBytes ?? 0);
    if (sizeDiff !== 0) return sizeDiff;
    const mtimeDiff = (right.modifiedAtNs ?? 0) - (left.modifiedAtNs ?? 0);
    if (mtimeDiff !== 0) return mtimeDiff;
    const pathLeft = left.path ?? left.id;
    const pathRight = right.path ?? right.id;
    const pathDiff = pathRight.localeCompare(pathLeft, "en-US");
    if (pathDiff !== 0) return pathDiff;
    return right.id.localeCompare(left.id, "en-US");
  });
  return sorted[0]?.id;
}

export function computeAutoSelectSummary(
  rows: readonly ReviewRow[],
  options: {
    filteredCount: number;
    loadedFileRowCount: number;
    maxSamples?: number;
  },
): AutoSelectSummary {
  const maxSamples = options.maxSamples ?? 5;
  const unreviewed = rows.filter(isUnreviewedFile);
  const unreviewedCount = unreviewed.length;

  const exactCount = unreviewed.filter((row) => row.type === "exact").length;
  const nearCount = unreviewed.filter((row) => row.type === "near").length;
  const relationCount = unreviewed.filter((row) => row.type === "relation").length;

  const groupIds = new Set(
    unreviewed.map((row) => row.groupId).filter((groupId): groupId is string => Boolean(groupId)),
  );
  const keeperCount = groupIds.size;
  const moveCandidateCount = Math.max(0, unreviewedCount - keeperCount);

  const mutationTargetCount = bulkMutationTargetCount(unreviewedCount);
  const capped = unreviewedCount > MAX_REVIEW_MUTATIONS;
  const partialLoad = options.loadedFileRowCount < options.filteredCount;
  const keeperPreviewUsesMtime = unreviewed.some((row) => row.modifiedAtNs != null);

  let samples: AutoSelectSummary["samples"];
  if (maxSamples > 0) {
    const byGroup = new Map<string, ReviewRow[]>();
    for (const row of unreviewed) {
      if (!row.groupId) continue;
      const members = byGroup.get(row.groupId) ?? [];
      members.push(row);
      byGroup.set(row.groupId, members);
    }
    const keeperIds = new Set<string>();
    for (const members of byGroup.values()) {
      const keeperId = pickKeeperPreviewId(members);
      if (keeperId) keeperIds.add(keeperId);
    }
    const takeNames = (predicate: (row: ReviewRow) => boolean) =>
      unreviewed.filter(predicate).slice(0, maxSamples).map((row) => row.name);
    samples = {
      keepers: unreviewed
        .filter((row) => keeperIds.has(row.id))
        .slice(0, maxSamples)
        .map((row) => row.name),
      moveCandidates: unreviewed
        .filter((row) => row.groupId && !keeperIds.has(row.id))
        .slice(0, maxSamples)
        .map((row) => row.name),
      exact: takeNames((row) => row.type === "exact"),
      near: takeNames((row) => row.type === "near"),
      relation: takeNames((row) => row.type === "relation"),
    };
  }

  return {
    unreviewedCount,
    keeperCount,
    moveCandidateCount,
    exactCount,
    nearCount,
    relationCount,
    capped,
    mutationTargetCount,
    partialLoad,
    keeperPreviewUsesMtime,
    ...(samples ? { samples } : {}),
  };
}
