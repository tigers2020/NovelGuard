import type { QualityRow } from "../types/quality";
import type {
  DuplicateGroupDetail,
  DuplicateGroupMemberDetail,
  MemberIntegrity,
  ReviewRow,
} from "../types/review";

const NOT_FOUND_MESSAGE = "Group not found. Refresh the review list.";

function fileIdFromRowId(rowId: string): string | null {
  if (rowId.startsWith("file:")) {
    const parts = rowId.split(":");
    return parts.length >= 3 ? parts[2] : null;
  }
  if (rowId.startsWith("row-")) {
    return rowId;
  }
  return null;
}

function indexQualityByPath(rows: QualityRow[]): Map<string, QualityRow[]> {
  const byPath = new Map<string, QualityRow[]>();
  for (const row of rows) {
    if (!row.path) continue;
    const list = byPath.get(row.path) ?? [];
    list.push(row);
    byPath.set(row.path, list);
  }
  return byPath;
}

function groupDetailType(
  fileRows: ReviewRow[],
  header: ReviewRow | undefined,
): "exact" | "near" | "relation" {
  const types = new Set(
    fileRows
      .map((row) => row.type)
      .filter((type): type is "exact" | "near" | "relation" => type !== "move_only"),
  );
  if (types.size === 1) {
    return [...types][0];
  }
  if (types.has("exact")) {
    return "exact";
  }
  if (types.has("near")) {
    return "near";
  }
  if (types.has("relation")) {
    return "relation";
  }
  return header?.type === "near" || header?.type === "relation" ? header.type : "exact";
}

function memberIntegrity(path: string, qualityByPath: Map<string, QualityRow[]>): MemberIntegrity {
  const issues = qualityByPath.get(path) ?? [];
  if (issues.length === 0) {
    return { status: "ok", label: "OK", issueCount: 0 };
  }
  const severityRank = { error: 2, warning: 1 };
  const best = issues.reduce((a, b) =>
    (severityRank[b.severity] ?? 0) > (severityRank[a.severity] ?? 0) ? b : a,
  );
  return {
    status: "issue",
    label: best.integrity || best.issueType,
    issueCount: issues.length,
  };
}

export function buildMockDuplicateGroupDetail(
  groupId: string,
  reviewRows: ReviewRow[],
  qualityRows: QualityRow[],
): DuplicateGroupDetail {
  const gid = groupId.trim();
  const groupRows = reviewRows.filter((r) => r.groupId === gid);
  const fileRows = groupRows.filter((r) => r.rowKind === "file");
  const header = groupRows.find((r) => r.rowKind === "group");
  const qualityByPath = indexQualityByPath(qualityRows);

  if (fileRows.length === 0) {
    return {
      status: "not_found",
      groupId: gid,
      members: [],
      message: NOT_FOUND_MESSAGE,
    };
  }

  const members: DuplicateGroupMemberDetail[] = [];
  for (const row of fileRows) {
    const fileId = fileIdFromRowId(row.id);
    if (!fileId) {
      continue;
    }
    const path = row.path ?? row.name;
    const isKeeper = row.proposedAction === "keep";
    members.push({
      rowId: row.id,
      fileId,
      name: row.name,
      path,
      sizeBytes: row.sizeBytes ?? 0,
      status: row.status,
      isKeeper,
      proposedAction: row.proposedAction,
      targetFolder: row.targetFolder,
      encoding: row.encoding ?? "Unknown",
      integrity: memberIntegrity(path, qualityByPath),
    });
  }

  if (members.length === 0) {
    return {
      status: "not_found",
      groupId: gid,
      members: [],
      message: NOT_FOUND_MESSAGE,
    };
  }

  members.sort((a, b) => {
    if (a.isKeeper !== b.isKeeper) return a.isKeeper ? -1 : 1;
    return a.path.localeCompare(b.path);
  });

  const keeper = members.find((m) => m.isKeeper) ?? members[0];
  const rowType = groupDetailType(fileRows, header);
  const groupStatus = header?.status ?? keeper.status;

  const base = {
    status: "ok" as const,
    groupId: gid,
    groupStatus,
    keeperFileId: keeper.fileId,
    keeperLabel: keeper.name,
    members,
  };

  if (rowType === "near") {
    return {
      ...base,
      type: "near",
      evidence: {
        matchKind: "near_ngram_v1",
        maxSimilarity: 0.91,
        threshold: 0.85,
        memberCount: members.length,
        comparisonMethod: "mock-ngram",
      },
    };
  }

  if (rowType === "relation") {
    return {
      ...base,
      type: "relation",
      evidence: {
        matchKind: "relation_filename_v1",
        relationKind: header?.relationKind ?? "same_title_series",
        confidenceLabel: header?.confidenceLabel ?? "medium",
        normalizedNames: [keeper.name],
        matchedTokens: ["title"],
        differingTokens: ["chapter"],
        memberCount: members.length,
      },
    };
  }

  return {
    ...base,
    type: "exact",
    evidence: {
      matchKind: "exact_content_hash",
      contentSha256: `mock-${gid}`,
      memberCount: members.length,
    },
    movePlan: {
      keeperAction: "keep",
      duplicateAction: "move_duplicate",
      targetFolder: keeper.targetFolder ?? "duplicate/",
    },
  };
}
