import type { ReviewRow, ReviewRowsQuery } from "../../../types/review";

export type FetchReviewPage = (
  query: ReviewRowsQuery,
) => Promise<{
  rows: ReviewRow[];
  pageInfo: { nextCursor: string | null; totalFiltered: number };
}>;

export async function fetchAllReviewPages(
  baseQuery: ReviewRowsQuery,
  fetchPage: FetchReviewPage,
): Promise<{ rows: ReviewRow[]; totalFiltered: number; nextCursor: null }> {
  let cursor: string | null = null;
  let accumulated: ReviewRow[] = [];
  let totalFiltered: number | undefined;

  while (true) {
    const page = await fetchPage({ ...baseQuery, cursor });
    accumulated = accumulated.concat(page.rows);
    totalFiltered = page.pageInfo.totalFiltered;
    cursor = page.pageInfo.nextCursor;
    if (!cursor || accumulated.length >= totalFiltered) break;
  }

  return { rows: accumulated, totalFiltered: totalFiltered ?? 0, nextCursor: null };
}
