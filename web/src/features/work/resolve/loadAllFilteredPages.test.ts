import { describe, expect, it, vi } from "vitest";
import { fetchAllReviewPages } from "./loadAllFilteredPages";
import type { ReviewRowsPage, ReviewRowsQuery } from "../../../types/review";

function makePage(
  rows: { id: string }[],
  totalFiltered: number,
  nextCursor: string | null,
): ReviewRowsPage {
  return {
    rows: rows as ReviewRowsPage["rows"],
    pageInfo: {
      cursor: null,
      nextCursor,
      hasMore: nextCursor != null,
      totalFiltered,
    },
    summary: {
      selectedCount: 0,
      conflictCount: 0,
      unreviewedCount: 0,
      approvedCount: 0,
    },
  };
}

describe("fetchAllReviewPages", () => {
  it("accumulates until no next cursor and length >= totalFiltered", async () => {
    const query: ReviewRowsQuery = {
      viewMode: "all",
      filters: {},
      cursor: null,
      limit: 200,
    };
    const fetchPage = vi
      .fn()
      .mockResolvedValueOnce(
        makePage(Array.from({ length: 200 }, (_, i) => ({ id: `r${i}` })), 300, "200"),
      )
      .mockResolvedValueOnce(
        makePage(Array.from({ length: 100 }, (_, i) => ({ id: `r${200 + i}` })), 300, null),
      );

    const result = await fetchAllReviewPages(query, fetchPage);

    expect(fetchPage).toHaveBeenCalledTimes(2);
    expect(result.rows).toHaveLength(300);
    expect(result.totalFiltered).toBe(300);
    expect(result.nextCursor).toBeNull();
  });
});
