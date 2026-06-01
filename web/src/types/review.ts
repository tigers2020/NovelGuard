export type ReviewViewMode = "action" | "groups" | "move" | "all" | "conflicts";

export type ReviewStatus = "unreviewed" | "approved" | "conflict" | "excluded";

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
  sizeBytes?: number;
  encoding?: string;
  integrity?: string;
  hasChildren: boolean;
  groupId?: string;
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
