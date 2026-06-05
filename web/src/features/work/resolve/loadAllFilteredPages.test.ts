import { describe, expect, it, vi } from "vitest";
import { mockBridge } from "../../../bridge/mockBridge";
import { MAX_QUERY_LIMIT } from "../../../contracts/reviewPageContract";
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

  it("accumulates 1200 rows across six pages at limit 200", async () => {
    const query: ReviewRowsQuery = {
      viewMode: "all",
      filters: {},
      cursor: null,
      limit: 200,
    };
    const totalFiltered = 1200;
    const fetchPage = vi.fn().mockImplementation(async (q: ReviewRowsQuery) => {
      const offset = q.cursor ? Number(q.cursor) : 0;
      const pageSize = Math.min(200, totalFiltered - offset);
      const rows = Array.from({ length: pageSize }, (_, i) => ({ id: `r${offset + i}` }));
      const nextOffset = offset + pageSize;
      const nextCursor = nextOffset < totalFiltered ? String(nextOffset) : null;
      return makePage(rows, totalFiltered, nextCursor);
    });

    const result = await fetchAllReviewPages(query, fetchPage);

    expect(fetchPage).toHaveBeenCalledTimes(6);
    expect(result.rows).toHaveLength(1200);
    expect(result.totalFiltered).toBe(1200);
    expect(result.nextCursor).toBeNull();
  });

  it("loads full mock filter set over 1000 rows via mockBridge", async () => {
    const query: ReviewRowsQuery = {
      viewMode: "all",
      filters: {},
      cursor: null,
      limit: MAX_QUERY_LIMIT,
    };
    const result = await fetchAllReviewPages(query, (q) => mockBridge.queryReviewRows(q));

    expect(result.rows.length).toBe(result.totalFiltered);
    expect(result.totalFiltered).toBeGreaterThan(1000);
    expect(result.nextCursor).toBeNull();
  });
});
