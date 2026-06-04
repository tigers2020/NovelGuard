import { describe, expect, it } from "vitest";
import { validReviewRowsPage } from "./fixtures";
import { PageContractError, REVIEW_MAX_QUERY_LIMIT, clampQueryLimit, validateReviewRowsPage } from "./reviewPageContract";

describe("validateReviewRowsPage", () => {
  it("accepts valid page", () => {
    expect(() => validateReviewRowsPage(validReviewRowsPage)).not.toThrow();
  });

  it("rejects page with more than review max rows", () => {
    const rows = Array.from({ length: REVIEW_MAX_QUERY_LIMIT + 1 }, (_, i) => ({
      ...validReviewRowsPage.rows[0],
      id: `r${i}`,
    }));
    const bad = { ...validReviewRowsPage, rows };
    expect(() => validateReviewRowsPage(bad)).toThrow(PageContractError);
  });
});

describe("clampQueryLimit", () => {
  it("defaults to 100", () => {
    expect(clampQueryLimit({ viewMode: "action" })).toBe(100);
  });

  it("clamps to review max", () => {
    expect(clampQueryLimit({ viewMode: "action", limit: 99999 })).toBe(REVIEW_MAX_QUERY_LIMIT);
  });
});
