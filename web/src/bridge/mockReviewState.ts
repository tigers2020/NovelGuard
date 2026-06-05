import type { ReviewRow } from "../types/review";
import type { ReviewDecisionCommand } from "../types/reviewDecisions";

const groupState = new Map<string, { keeperFileId?: string; groupStatus?: string }>();
const memberState = new Map<string, string>();

function fileIdFromRowId(rowId: string): string | null {
  if (rowId.startsWith("file:")) {
    const parts = rowId.split(":");
    return parts.length === 3 ? parts[2] : null;
  }
  if (rowId.startsWith("row-")) {
    return rowId;
  }
  return null;
}

export function resetMockReviewState(): void {
  groupState.clear();
  memberState.clear();
}

function pickMockKeeperFileId(members: ReviewRow[]): string | null {
  const files = members.filter((row) => row.rowKind === "file");
  if (files.length === 0) return null;
  const keeper = [...files].sort((a, b) => {
    const sizeDiff = (b.sizeBytes ?? 0) - (a.sizeBytes ?? 0);
    if (sizeDiff !== 0) return sizeDiff;
    return String(b.name).localeCompare(String(a.name), "en-US");
  })[0];
  return fileIdFromRowId(keeper.id);
}

/** Mirror backend `persist_exact_non_keeper_approvals` after post-scan (NOV-17/NOV-20). */
export function persistMockExactNonKeeperApprovals(rows: ReviewRow[]): number {
  const byGroup = new Map<string, ReviewRow[]>();
  for (const row of rows) {
    if (row.rowKind !== "file" || row.type !== "exact" || !row.groupId) continue;
    const list = byGroup.get(row.groupId) ?? [];
    list.push(row);
    byGroup.set(row.groupId, list);
  }

  let updated = 0;
  for (const members of byGroup.values()) {
    if (members.length < 2) continue;
    const groupId = members[0].groupId;
    if (!groupId) continue;

    const groupEntry = groupState.get(groupId);
    const keeperOverride = groupEntry?.keeperFileId;
    const keeperId =
      keeperOverride && members.some((row) => fileIdFromRowId(row.id) === keeperOverride)
        ? keeperOverride
        : pickMockKeeperFileId(members);
    if (!keeperId) continue;

    for (const row of members) {
      const fileId = fileIdFromRowId(row.id);
      if (!fileId || fileId === keeperId) continue;
      if (memberState.has(fileId)) continue;
      memberState.set(fileId, "approved");
      updated += 1;
    }
  }
  return updated;
}

export function applyMockReviewState(rows: ReviewRow[]): ReviewRow[] {
  return rows.map((row) => {
    const groupId = row.groupId;
    if (!groupId) return row;

    const groupEntry = groupState.get(groupId);
    const keeperOverride = groupEntry?.keeperFileId;
    const groupStatus = groupEntry?.groupStatus;

    if (row.rowKind === "group") {
      return {
        ...row,
        status: (groupStatus as ReviewRow["status"]) ?? "unreviewed",
        keeperLabel: row.keeperLabel,
      };
    }

    const fileId = fileIdFromRowId(row.id);
    const memberStatus = fileId ? memberState.get(fileId) : undefined;
    const effectiveStatus =
      (memberStatus as ReviewRow["status"] | undefined) ??
      (groupStatus as ReviewRow["status"] | undefined) ??
      "unreviewed";

    const updated = { ...row, status: effectiveStatus };
    if (keeperOverride && row.keeperLabel) {
      updated.keeperLabel = row.keeperLabel;
    }
    return updated;
  });
}

const UNRESOLVED_STATUSES = new Set(["unreviewed", "conflict"]);

export function resolveInsightCounts(rows: ReviewRow[]): {
  moveReadyCount: number;
  reviewSignalCount: number;
} {
  let moveReadyCount = 0;
  let reviewSignalCount = 0;
  for (const row of rows) {
    if (row.rowKind !== "file") continue;
    if (row.status !== "unreviewed" && row.status !== "conflict") continue;
    if (row.type === "exact") moveReadyCount += 1;
    else if (row.type === "near" || row.type === "relation") reviewSignalCount += 1;
  }
  return { moveReadyCount, reviewSignalCount };
}

export function fileRowStatusCounts(rows: ReviewRow[]): {
  queueCount: number;
  approvedCount: number;
  conflictCount: number;
} {
  let queueCount = 0;
  let approvedCount = 0;
  let conflictCount = 0;
  for (const row of rows) {
    if (row.rowKind !== "file") continue;
    if (row.status === "approved") approvedCount += 1;
    else if (row.status === "conflict") conflictCount += 1;
    if (UNRESOLVED_STATUSES.has(row.status)) queueCount += 1;
  }
  return { queueCount, approvedCount, conflictCount };
}

export function applyMockReviewCommand(
  rows: ReviewRow[],
  command: ReviewDecisionCommand,
  keeperFileId?: string,
): number {
  let updated = 0;
  for (const row of rows) {
    const groupId = row.groupId;
    if (!groupId) continue;

    if (command === "reset") {
      if (row.rowKind === "group") {
        if (groupState.delete(groupId)) updated += 1;
      } else {
        const fileId = fileIdFromRowId(row.id);
        if (fileId && memberState.delete(fileId)) updated += 1;
      }
      continue;
    }

    if (command === "setKeeper") {
      const keeper =
        row.rowKind === "file" ? fileIdFromRowId(row.id) : keeperFileId;
      if (!keeper) continue;
      const entry = groupState.get(groupId);
      if (entry?.groupStatus === "approved") {
        groupState.set(groupId, { ...entry, groupStatus: undefined });
      }
      for (const [fid, status] of memberState.entries()) {
        if (status === "approved") memberState.delete(fid);
      }
      groupState.set(groupId, { ...entry, keeperFileId: keeper });
      updated += 1;
      continue;
    }

    const status =
      command === "approve"
        ? "approved"
        : command === "exclude"
          ? "excluded"
          : command === "markConflict"
            ? "conflict"
            : null;
    if (!status) continue;

    if (row.rowKind === "group") {
      groupState.set(groupId, { ...groupState.get(groupId), groupStatus: status });
      updated += 1;
    } else {
      const fileId = fileIdFromRowId(row.id);
      if (fileId) {
        memberState.set(fileId, status);
        updated += 1;
      }
    }
  }
  return updated;
}
