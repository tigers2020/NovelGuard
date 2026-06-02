import type { ReviewRowsPage } from "./review";

export type FileRowColumnPreset = "basic" | "review";

export type FileRowDensity = "comfortable" | "compact";

export interface FileRowsQuery {
  search?: string;
  preset?: FileRowColumnPreset;
  cursor?: string | null;
  limit?: number;
}

export interface FileRow {
  id: string;
  name: string;
  path: string;
  sizeBytes?: number;
  modifiedAt?: string;
  extension?: string;
  duplicateGroupId?: string | null;
  isKeeper?: boolean | null;
  integrityStatus?: string | null;
}

export interface FileRowsPage {
  rows: FileRow[];
  pageInfo: ReviewRowsPage["pageInfo"];
}

/** Stable empty page for unscanned library / stub backends (LOCK-P25-3). */
export function emptyFileRowsPage(cursor: string | null = null): FileRowsPage {
  return {
    rows: [],
    pageInfo: {
      cursor,
      nextCursor: null,
      hasMore: false,
      totalFiltered: 0,
    },
  };
}
