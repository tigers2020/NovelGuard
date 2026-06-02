import { getAllReviewRows, paginateRows, textSortKey } from "./mockData";
import { BridgeCallError } from "./bridgeErrors";
import type { FileRow, FileRowsPage, FileRowsQuery, FileRowSortField } from "../types/fileRows";
import { clampFileRowsLimit } from "../contracts/fileRowsPageContract";

export { textSortKey };

const FILE_ROW_SORT_FIELDS = new Set<FileRowSortField>([
  "name",
  "path",
  "extension",
  "size",
  "modifiedAt",
  "encoding",
  "duplicateGroup",
  "integrity",
]);

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

function integrityBucket(row: FileRow): "ok" | "unknown" | "issue" {
  const status = row.integrityStatus;
  if (status == null || status === "") {
    return "unknown";
  }
  const key = textSortKey(status);
  if (key === "utf-8" || key === "ascii") {
    return "ok";
  }
  return "issue";
}

function validateSort(query: FileRowsQuery): void {
  const field = query.sort?.field;
  if (field && !FILE_ROW_SORT_FIELDS.has(field)) {
    throw new BridgeCallError("Bridge call rejected: INVALID_SORT_FIELD", {
      code: "rejected",
      method: "queryFileRows",
      reason: "INVALID_SORT_FIELD",
    });
  }
  const direction = query.sort?.direction;
  if (direction && direction !== "asc" && direction !== "desc") {
    throw new BridgeCallError("Bridge call rejected: INVALID_SORT_FIELD", {
      code: "rejected",
      method: "queryFileRows",
      reason: "INVALID_SORT_FIELD",
    });
  }
}

function validateFilters(query: FileRowsQuery): void {
  const filters = query.filters;
  if (!filters) {
    return;
  }
  if (filters.extension != null) {
    if (!Array.isArray(filters.extension) || filters.extension.length === 0) {
      throw new BridgeCallError("Bridge call rejected: INVALID_FILTER_VALUE", {
        code: "rejected",
        method: "queryFileRows",
        reason: "INVALID_FILTER_VALUE",
      });
    }
  }
  if (filters.encoding != null) {
    if (!Array.isArray(filters.encoding) || filters.encoding.length === 0) {
      throw new BridgeCallError("Bridge call rejected: INVALID_FILTER_VALUE", {
        code: "rejected",
        method: "queryFileRows",
        reason: "INVALID_FILTER_VALUE",
      });
    }
  }
  if (
    filters.duplicateGroup != null &&
    filters.duplicateGroup !== "any" &&
    filters.duplicateGroup !== "none"
  ) {
    throw new BridgeCallError("Bridge call rejected: INVALID_FILTER_VALUE", {
      code: "rejected",
      method: "queryFileRows",
      reason: "INVALID_FILTER_VALUE",
    });
  }
  if (
    filters.integrity != null &&
    filters.integrity !== "ok" &&
    filters.integrity !== "issue" &&
    filters.integrity !== "unknown"
  ) {
    throw new BridgeCallError("Bridge call rejected: INVALID_FILTER_VALUE", {
      code: "rejected",
      method: "queryFileRows",
      reason: "INVALID_FILTER_VALUE",
    });
  }
}

export function applyMockFileRowFilters(rows: FileRow[], query: FileRowsQuery): FileRow[] {
  let result = rows;
  const search = query.search?.trim();
  if (search) {
    const term = textSortKey(search);
    result = result.filter((row) => {
      const haystack = `${textSortKey(row.name)} ${textSortKey(row.path)} ${textSortKey(row.extension ?? "")}`;
      return haystack.includes(term);
    });
  }

  const filters = query.filters;
  if (filters?.extension?.length) {
    const allowed = new Set(filters.extension.map((value) => textSortKey(value)));
    result = result.filter((row) => allowed.has(textSortKey(row.extension ?? "")));
  }
  if (filters?.encoding?.length) {
    const allowed = new Set(filters.encoding.map((value) => textSortKey(value)));
    result = result.filter((row) => allowed.has(textSortKey(row.integrityStatus ?? "")));
  }
  if (filters?.duplicateGroup === "any") {
    result = result.filter((row) => row.duplicateGroupId);
  } else if (filters?.duplicateGroup === "none") {
    result = result.filter((row) => !row.duplicateGroupId);
  }
  if (filters?.integrity === "ok") {
    result = result.filter((row) => integrityBucket(row) === "ok");
  } else if (filters?.integrity === "unknown") {
    result = result.filter((row) => integrityBucket(row) === "unknown");
  } else if (filters?.integrity === "issue") {
    result = result.filter((row) => integrityBucket(row) === "issue");
  }

  return result;
}

export function sortMockFileRows(rows: FileRow[], query: FileRowsQuery): FileRow[] {
  const field = query.sort?.field ?? "path";
  const reverse = query.sort?.direction === "desc";

  const indexed = rows.map((row, index) => ({ row, index }));
  indexed.sort((a, b) => {
    const cmp =
      field === "size"
        ? (a.row.sizeBytes ?? 0) - (b.row.sizeBytes ?? 0)
        : field === "modifiedAt"
          ? String(a.row.modifiedAt ?? "").localeCompare(String(b.row.modifiedAt ?? ""))
          : field === "duplicateGroup"
            ? (a.row.duplicateGroupId ? textSortKey(a.row.duplicateGroupId) : "").localeCompare(
                b.row.duplicateGroupId ? textSortKey(b.row.duplicateGroupId) : "",
                "en-US",
              )
            : field === "integrity" || field === "encoding"
              ? textSortKey(a.row.integrityStatus ?? "").localeCompare(
                  textSortKey(b.row.integrityStatus ?? ""),
                  "en-US",
                )
              : field === "extension"
                ? textSortKey(a.row.extension ?? "").localeCompare(
                    textSortKey(b.row.extension ?? ""),
                    "en-US",
                  )
                : field === "name"
                  ? textSortKey(a.row.name).localeCompare(textSortKey(b.row.name), "en-US")
                  : textSortKey(a.row.path).localeCompare(textSortKey(b.row.path), "en-US");
    if (cmp !== 0) {
      return reverse ? -cmp : cmp;
    }
    if (a.index !== b.index) {
      return a.index - b.index;
    }
    return a.row.id.localeCompare(b.row.id);
  });
  return indexed.map((entry) => entry.row);
}

export function queryMockFileRows(query: FileRowsQuery): FileRowsPage {
  validateSort(query);
  validateFilters(query);
  const limit = clampFileRowsLimit(query);
  const all = getAllMockFileRows();
  const filtered = applyMockFileRowFilters(all, query);
  const sorted = sortMockFileRows(filtered, query);
  const { slice, nextCursor, hasMore } = paginateRows(sorted, query.cursor, limit);

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
