import type { ReviewRowsPage, ReviewRowsQuery } from "../types/review";

export const MAX_QUERY_LIMIT = 200;
export const DEFAULT_QUERY_LIMIT = 100;

export class PageContractError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "PageContractError";
  }
}

export function clampQueryLimit(query: ReviewRowsQuery): number {
  const raw = query.limit ?? DEFAULT_QUERY_LIMIT;
  return Math.min(Math.max(1, raw), MAX_QUERY_LIMIT);
}

export function validateReviewRowsPage(page: unknown): asserts page is ReviewRowsPage {
  if (typeof page !== "object" || page === null) {
    throw new PageContractError("ReviewRowsPage must be an object");
  }
  const p = page as ReviewRowsPage;
  if (!Array.isArray(p.rows)) {
    throw new PageContractError("ReviewRowsPage.rows must be an array");
  }
  if (p.rows.length > MAX_QUERY_LIMIT) {
    throw new PageContractError(`ReviewRowsPage.rows exceeds limit ${MAX_QUERY_LIMIT}`);
  }
  if (!p.pageInfo || typeof p.pageInfo.totalFiltered !== "number") {
    throw new PageContractError("ReviewRowsPage.pageInfo invalid");
  }
  if (!p.summary || typeof p.summary.unreviewedCount !== "number") {
    throw new PageContractError("ReviewRowsPage.summary invalid");
  }
}
