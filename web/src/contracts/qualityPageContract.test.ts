import { describe, expect, it } from "vitest";
import { validQualityRowsPage } from "./fixtures";
import { PageContractError } from "./reviewPageContract";
import { validateQualityRowsPage } from "./qualityPageContract";

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
});
