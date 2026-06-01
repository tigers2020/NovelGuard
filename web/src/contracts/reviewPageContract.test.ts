import { describe, expect, it } from "vitest";
import { validReviewRowsPage } from "./fixtures";
import { PageContractError, clampQueryLimit, validateReviewRowsPage } from "./reviewPageContract";

describe("validateReviewRowsPage", () => {
  it("accepts valid page", () => {
    expect(() => validateReviewRowsPage(validReviewRowsPage)).not.toThrow();
  });

  it("rejects page with more than 200 rows", () => {
    const rows = Array.from({ length: 201 }, (_, i) => ({
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

  it("clamps to 200 max", () => {
    expect(clampQueryLimit({ viewMode: "action", limit: 999 })).toBe(200);
  });
});
