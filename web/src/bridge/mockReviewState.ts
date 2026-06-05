import type { AutoSelectKeepersSummary } from "../types/autoSelectSummary";
import type { ReviewRow, ReviewRowsQuery } from "../types/review";
import type { ReviewDecisionCommand } from "../types/reviewDecisions";
import { filterReviewRows } from "./mockData";

const groupState = new Map<string, { keeperFileId?: string; groupStatus?: string }>();
const memberState = new Map<string, string>();

function fileIdFromRowId(rowId: string): string | null {
  if (rowId.startsWith("file:")) {
    const rest = rowId.slice(5);
    if (rest.length < 64) return null;
    const candidate = rest.slice(-64);
    if (!/^[0-9a-f]{64}$/i.test(candidate)) return null;
    return candidate;
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
    const pathDiff = String(b.path ?? b.name).localeCompare(String(a.path ?? a.name), "en-US");
    if (pathDiff !== 0) return pathDiff;
    return String(b.id).localeCompare(String(a.id), "en-US");
  })[0];
  return fileIdFromRowId(keeper.id);
}

export function summarizeMockAutoSelectKeepers(
  rows: ReviewRow[],
  query: ReviewRowsQuery,
): AutoSelectKeepersSummary {
  const mergedQuery: ReviewRowsQuery = {
    ...query,
    filters: {
      ...query.filters,
      status: ["unreviewed"],
    },
  };
  const fileRows = filterReviewRows(rows, mergedQuery).filter(
    (row) => row.rowKind === "file" && row.status === "unreviewed" && row.status !== "conflict",
  );

  const byGroup = new Map<string, ReviewRow[]>();
  for (const row of fileRows) {
    if (!row.groupId) continue;
    const list = byGroup.get(row.groupId) ?? [];
    list.push(row);
    byGroup.set(row.groupId, list);
  }

  const keeperRowIds: string[] = [];
  let exactCount = 0;
  let nearCount = 0;
  let relationCount = 0;

  for (const groupRows of byGroup.values()) {
    const keeperId = pickMockKeeperFileId(groupRows);
    const keeperRow = groupRows.find((row) => fileIdFromRowId(row.id) === keeperId);
    if (keeperRow) keeperRowIds.push(keeperRow.id);
    const rowType = groupRows[0]?.type;
    const size = groupRows.length;
    if (rowType === "exact") exactCount += size;
    else if (rowType === "near") nearCount += size;
    else if (rowType === "relation") relationCount += size;
  }

  return {
    targetCount: fileRows.length,
    keeperCount: keeperRowIds.length,
    moveCandidateCount: Math.max(0, fileRows.length - keeperRowIds.length),
    exactCount,
    nearCount,
    relationCount,
    keeperRowIds,
  };
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
  const membersByGroup = new Map<string, ReviewRow[]>();
  for (const row of rows) {
    if (row.rowKind !== "file" || !row.groupId) continue;
    const list = membersByGroup.get(row.groupId) ?? [];
    list.push(row);
    membersByGroup.set(row.groupId, list);
  }

  const keeperByGroup = new Map<string, string | null>();
  for (const [groupId, members] of membersByGroup) {
    const override = groupState.get(groupId)?.keeperFileId;
    keeperByGroup.set(
      groupId,
      override && members.some((row) => fileIdFromRowId(row.id) === override)
        ? override
        : pickMockKeeperFileId(members),
    );
  }

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

    const keeperId = keeperByGroup.get(groupId);
    if (!keeperId || !fileId) return updated;
    const isKeeper = fileId === keeperId;
    if (row.type === "exact") {
      updated.proposedAction = isKeeper ? "keep" : "move_duplicate";
      updated.targetFolder = isKeeper ? undefined : "duplicate/";
    } else if (row.type === "near" || row.type === "relation") {
      if (effectiveStatus === "approved") {
        updated.proposedAction = isKeeper ? "keep" : "move_duplicate";
        updated.targetFolder = isKeeper ? undefined : "duplicate/";
      } else {
        updated.proposedAction = isKeeper ? "keep" : "ignore";
        updated.targetFolder = undefined;
      }
    }
    return updated;
  });
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
    if (row.status === "unreviewed" || row.status === "conflict") queueCount += 1;
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

    if (command !== "reset" && row.status === "conflict") continue;
    if (command === "approve" && row.rowKind !== "file") continue;

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
