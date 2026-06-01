import { describe, expect, it } from "vitest";
import { getAllReviewRows, sortReviewRows } from "./mockData";

describe("sortReviewRows", () => {
  it("orders by name ascending", () => {
    const rows = getAllReviewRows(20);
    const sorted = sortReviewRows(rows, { field: "name", direction: "asc" });
    expect(sorted[0]!.name <= sorted[1]!.name).toBe(true);
  });
});
