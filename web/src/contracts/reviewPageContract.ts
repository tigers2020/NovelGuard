import type { ReviewRowsPage, ReviewRowsQuery } from "../types/review";

/** Quality grid page cap (unchanged). */
export const MAX_QUERY_LIMIT = 200;
/** Resolve review grid — load full filtered set in one request. */
export const REVIEW_MAX_QUERY_LIMIT = 5000;
export const DEFAULT_QUERY_LIMIT = 100;

export class PageContractError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "PageContractError";
  }
}

export function clampQueryLimit(query: ReviewRowsQuery): number {
  const raw = query.limit ?? DEFAULT_QUERY_LIMIT;
  return Math.min(Math.max(1, raw), REVIEW_MAX_QUERY_LIMIT);
}

export function validateReviewRowsPage(page: unknown): asserts page is ReviewRowsPage {
  if (typeof page !== "object" || page === null) {
    throw new PageContractError("ReviewRowsPage must be an object");
  }
  const p = page as ReviewRowsPage;
  if (!Array.isArray(p.rows)) {
    throw new PageContractError("ReviewRowsPage.rows must be an array");
  }
  if (p.rows.length > REVIEW_MAX_QUERY_LIMIT) {
    throw new PageContractError(`ReviewRowsPage.rows exceeds limit ${REVIEW_MAX_QUERY_LIMIT}`);
  }
  if (!p.pageInfo || typeof p.pageInfo.totalFiltered !== "number") {
    throw new PageContractError("ReviewRowsPage.pageInfo invalid");
  }
  if (!p.summary || typeof p.summary.unreviewedCount !== "number") {
    throw new PageContractError("ReviewRowsPage.summary invalid");
  }
}
