export type ReviewViewMode = "action" | "groups" | "move" | "all" | "conflicts";

export type ReviewStatus = "unreviewed" | "approved" | "conflict" | "excluded";

export type RelationKind =
  | "same_title_series"
  | "chapter_sequence"
  | "version_variant"
  | "title_prefix_overlap";
export type ConfidenceLabel = "low" | "medium" | "high";

export type ReviewRowType = "exact" | "near" | "relation" | "move_only";

export type ProposedAction = "keep" | "move_duplicate" | "move_organized" | "ignore";

export interface ReviewRowsQuery {
  viewMode: ReviewViewMode;
  filters?: {
    status?: ReviewStatus[];
    types?: ReviewRowType[];
    search?: string;
  };
  sort?: { field: string; direction: "asc" | "desc" };
  cursor?: string | null;
  limit?: number;
}

export interface ReviewRow {
  id: string;
  rowKind: "group" | "file";
  status: ReviewStatus;
  type: ReviewRowType;
  name: string;
  keeperLabel?: string;
  proposedAction: ProposedAction;
  targetFolder?: string;
  confidence?: number;
  confidenceLabel?: ConfidenceLabel;
  relationKind?: RelationKind;
  sizeBytes?: number;
  encoding?: string;
  integrity?: string;
  hasChildren: boolean;
  groupId?: string;
  path?: string;
}

export interface ReviewRowsPage {
  rows: ReviewRow[];
  pageInfo: {
    cursor: string | null;
    nextCursor: string | null;
    hasMore: boolean;
    totalFiltered: number;
  };
  summary: {
    selectedCount: number;
    conflictCount: number;
    unreviewedCount: number;
    approvedCount: number;
  };
}

export type DuplicateMatchKind = "exact_content_hash" | "near_ngram_v1" | "relation_filename_v1";

export interface MemberIntegrity {
  status: "ok" | "issue";
  label: string;
  issueCount: number;
}

export interface DuplicateGroupMemberDetail {
  rowId: string;
  fileId: string;
  name: string;
  path: string;
  sizeBytes: number;
  status: ReviewStatus;
  isKeeper: boolean;
  proposedAction: ProposedAction;
  targetFolder?: string;
  encoding?: string;
  integrity: MemberIntegrity;
}

interface DuplicateGroupDetailOkBase {
  status: "ok";
  groupId: string;
  groupStatus: ReviewStatus;
  keeperFileId: string;
  keeperLabel: string;
  members: DuplicateGroupMemberDetail[];
}

export interface DuplicateGroupDetailExactOk extends DuplicateGroupDetailOkBase {
  type: "exact";
  evidence: {
    matchKind: "exact_content_hash";
    contentSha256: string;
    memberCount: number;
  };
  movePlan: {
    keeperAction: "keep";
    duplicateAction: "move_duplicate";
    targetFolder: string;
  };
}

export interface DuplicateGroupDetailNearOk extends DuplicateGroupDetailOkBase {
  type: "near";
  evidence: {
    matchKind: "near_ngram_v1";
    maxSimilarity: number;
    threshold: number;
    memberCount: number;
    comparisonMethod: string;
  };
}

export interface DuplicateGroupDetailRelationOk extends DuplicateGroupDetailOkBase {
  type: "relation";
  evidence: {
    matchKind: "relation_filename_v1";
    relationKind: RelationKind;
    confidenceLabel: ConfidenceLabel;
    normalizedNames: string[];
    matchedTokens: string[];
    differingTokens: string[];
    memberCount: number;
  };
}

export type DuplicateGroupDetailOk =
  | DuplicateGroupDetailExactOk
  | DuplicateGroupDetailNearOk
  | DuplicateGroupDetailRelationOk;

export interface DuplicateGroupDetailNotFound {
  status: "not_found";
  groupId: string;
  members: [];
  message: string;
}

export type DuplicateGroupDetail = DuplicateGroupDetailOk | DuplicateGroupDetailNotFound;

export function reviewRowGroupId(row: ReviewRow): string | null {
  if (row.groupId) return row.groupId;
  if (row.id.startsWith("group:")) return row.id.slice("group:".length);
  if (row.id.startsWith("file:")) {
    const rest = row.id.slice(5);
    const fileId = rest.length >= 64 ? rest.slice(-64) : null;
    if (fileId && /^[0-9a-f]{64}$/i.test(fileId) && rest.length > fileId.length + 1) {
      return rest.slice(0, -(fileId.length + 1));
    }
    const parts = row.id.split(":");
    return parts.length >= 3 ? parts[1] : null;
  }
  return null;
}
