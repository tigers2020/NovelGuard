import type { FileRowsPage, FileRowsQuery } from "../types/fileRows";

export const FILE_ROWS_DEFAULT_LIMIT = 100;
export const FILE_ROWS_MAX_LIMIT = 500;

export class PageContractError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "PageContractError";
  }
}

export function clampFileRowsLimit(query: FileRowsQuery): number {
  const raw = query.limit ?? FILE_ROWS_DEFAULT_LIMIT;
  return Math.min(Math.max(1, raw), FILE_ROWS_MAX_LIMIT);
}

export function validateFileRowsPage(page: unknown): asserts page is FileRowsPage {
  if (typeof page !== "object" || page === null) {
    throw new PageContractError("FileRowsPage must be an object");
  }
  const p = page as FileRowsPage;
  if (!Array.isArray(p.rows)) {
    throw new PageContractError("FileRowsPage.rows must be an array");
  }
  if (p.rows.length > FILE_ROWS_MAX_LIMIT) {
    throw new PageContractError(`FileRowsPage.rows exceeds limit ${FILE_ROWS_MAX_LIMIT}`);
  }
  if (!p.pageInfo || typeof p.pageInfo.totalFiltered !== "number") {
    throw new PageContractError("FileRowsPage.pageInfo invalid");
  }
}
