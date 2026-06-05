import type { QualityRowsPage, QualityRowsQuery } from "../types/quality";
import {
  DEFAULT_QUERY_LIMIT,
  MAX_QUERY_LIMIT,
  PageContractError,
} from "./reviewPageContract";

export function clampQualityQueryLimit(query: QualityRowsQuery): number {
  const raw = query.limit ?? DEFAULT_QUERY_LIMIT;
  return Math.min(Math.max(1, raw), MAX_QUERY_LIMIT);
}

export function validateQualityRowsPage(page: unknown): asserts page is QualityRowsPage {
  if (typeof page !== "object" || page === null) {
    throw new PageContractError("QualityRowsPage must be an object");
  }
  const p = page as QualityRowsPage;
  if (!Array.isArray(p.rows) || p.rows.length > MAX_QUERY_LIMIT) {
    throw new PageContractError(`QualityRowsPage.rows invalid or exceeds ${MAX_QUERY_LIMIT}`);
  }
  if (
    !p.pageInfo ||
    typeof p.pageInfo.totalFiltered !== "number" ||
    !p.summary ||
    typeof p.summary.issueCount !== "number" ||
    typeof p.summary.warningCount !== "number" ||
    typeof p.summary.errorCount !== "number"
  ) {
    throw new PageContractError("QualityRowsPage.pageInfo or summary invalid");
  }
}
