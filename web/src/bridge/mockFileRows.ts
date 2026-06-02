import { getAllReviewRows, paginateRows } from "./mockData";
import type { FileRow, FileRowsPage, FileRowsQuery } from "../types/fileRows";
import { clampFileRowsLimit } from "../contracts/fileRowsPageContract";

let cachedFileRows: FileRow[] | null = null;

function extensionFromName(name: string): string {
  const idx = name.lastIndexOf(".");
  return idx >= 0 ? name.slice(idx + 1).toLowerCase() : "";
}

export function getAllMockFileRows(count = 1284): FileRow[] {
  if (cachedFileRows && cachedFileRows.length !== count) {
    cachedFileRows = null;
  }
  if (cachedFileRows) {
    return cachedFileRows;
  }

  cachedFileRows = getAllReviewRows(count)
    .filter((row) => row.rowKind === "file")
    .map((row, index) => ({
      id: `file-${index + 1}`,
      name: row.name,
      path: row.path ?? `/library/raw/${row.name}`,
      sizeBytes: row.sizeBytes,
      modifiedAt: "2026-06-01T10:42:00Z",
      extension: extensionFromName(row.name),
      duplicateGroupId: row.groupId ?? null,
      isKeeper: index % 5 === 0 ? true : null,
      integrityStatus: row.integrity ?? null,
    }))
    .sort((a, b) => a.path.localeCompare(b.path, "ko"));

  return cachedFileRows;
}

export function filterMockFileRows(rows: FileRow[], search?: string): FileRow[] {
  const term = search?.trim().toLowerCase();
  if (!term) {
    return rows;
  }
  return rows.filter((row) => {
    const haystack = `${row.name} ${row.path} ${row.extension ?? ""}`.toLowerCase();
    return haystack.includes(term);
  });
}

export function queryMockFileRows(query: FileRowsQuery): FileRowsPage {
  const limit = clampFileRowsLimit(query);
  const all = getAllMockFileRows();
  const filtered = filterMockFileRows(all, query.search);
  const { slice, nextCursor, hasMore } = paginateRows(filtered, query.cursor, limit);

  return {
    rows: slice,
    pageInfo: {
      cursor: query.cursor ?? null,
      nextCursor,
      hasMore,
      totalFiltered: filtered.length,
    },
  };
}
