import type { FileRowsPage, FileRowsQuery } from "../types/fileRows";
import { DEFAULT_QUERY_LIMIT, MAX_QUERY_LIMIT, PageContractError } from "./reviewPageContract";

export function clampFileRowsLimit(query: FileRowsQuery): number {
  const raw = query.limit ?? DEFAULT_QUERY_LIMIT;
  return Math.min(Math.max(1, raw), MAX_QUERY_LIMIT);
}

export function validateFileRowsPage(page: unknown): asserts page is FileRowsPage {
  if (typeof page !== "object" || page === null) {
    throw new PageContractError("FileRowsPage must be an object");
  }
  const p = page as FileRowsPage;
  if (!Array.isArray(p.rows)) {
    throw new PageContractError("FileRowsPage.rows must be an array");
  }
  if (p.rows.length > MAX_QUERY_LIMIT) {
    throw new PageContractError(`FileRowsPage.rows exceeds limit ${MAX_QUERY_LIMIT}`);
  }
  if (!p.pageInfo || typeof p.pageInfo.totalFiltered !== "number") {
    throw new PageContractError("FileRowsPage.pageInfo invalid");
  }
}
