import { describe, expect, it } from "vitest";
import { validQualityRowsPage } from "./fixtures";
import { PageContractError } from "./reviewPageContract";
import { clampQualityQueryLimit, validateQualityRowsPage } from "./qualityPageContract";

describe("clampQualityQueryLimit", () => {
  it("caps limit at 200", () => {
    expect(clampQualityQueryLimit({ issueType: "integrity", limit: 999 })).toBe(200);
  });
});

describe("validateQualityRowsPage", () => {
  it("accepts valid page", () => {
    expect(() => validateQualityRowsPage(validQualityRowsPage)).not.toThrow();
  });

  it("rejects more than 200 rows", () => {
    const rows = Array.from({ length: 201 }, (_, i) => ({
      id: `q${i}`,
      issueType: "integrity" as const,
      name: "x",
      integrity: "ok",
      severity: "warning" as const,
    }));
    expect(() => validateQualityRowsPage({ ...validQualityRowsPage, rows })).toThrow(
      PageContractError,
    );
  });

  it("rejects missing pageInfo.totalFiltered", () => {
    const page = {
      ...validQualityRowsPage,
      pageInfo: { ...validQualityRowsPage.pageInfo, totalFiltered: undefined },
    };
    expect(() => validateQualityRowsPage(page)).toThrow(PageContractError);
  });

  it("accepts non-zero totalFiltered and tab summary counts", () => {
    const page = {
      ...validQualityRowsPage,
      pageInfo: { ...validQualityRowsPage.pageInfo, totalFiltered: 3 },
      summary: { issueCount: 2, warningCount: 1, errorCount: 0 },
    };
    expect(() => validateQualityRowsPage(page)).not.toThrow();
  });
});
