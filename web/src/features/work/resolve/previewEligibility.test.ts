import { describe, expect, it } from "vitest";
import type { ReviewRow } from "../../../types/review";
import {
  countExecutableMovePreviewRows,
  hasExecutableMovePreviewRows,
  isExecutableMovePreviewRow,
  reviewOnlyBlockedReasonForFilter,
} from "./previewEligibility";

function fileRow(overrides: Partial<ReviewRow> = {}): ReviewRow {
  return {
    id: "row-1",
    rowKind: "file",
    status: "approved",
    type: "exact",
    name: "dup.txt",
    proposedAction: "move_duplicate",
    hasChildren: false,
    ...overrides,
  };
}

describe("isExecutableMovePreviewRow", () => {
  it("accepts approved move_duplicate file rows", () => {
    expect(isExecutableMovePreviewRow(fileRow())).toBe(true);
  });

  it("rejects group rows", () => {
    expect(isExecutableMovePreviewRow(fileRow({ rowKind: "group" }))).toBe(false);
  });

  it("rejects excluded and conflict rows", () => {
    expect(isExecutableMovePreviewRow(fileRow({ status: "excluded" }))).toBe(false);
    expect(isExecutableMovePreviewRow(fileRow({ status: "conflict" }))).toBe(false);
  });

  it("rejects keep, ignore, and move_organized actions", () => {
    expect(isExecutableMovePreviewRow(fileRow({ proposedAction: "keep" }))).toBe(false);
    expect(isExecutableMovePreviewRow(fileRow({ proposedAction: "ignore" }))).toBe(false);
    expect(isExecutableMovePreviewRow(fileRow({ proposedAction: "move_organized" }))).toBe(false);
  });
});

describe("reviewOnlyBlockedReasonForFilter", () => {
  it("returns undefined for exact filter", () => {
    expect(reviewOnlyBlockedReasonForFilter("exact")).toBeUndefined();
  });

  it("blocks near, relation, and all filters with distinct reasons", () => {
    expect(reviewOnlyBlockedReasonForFilter("near")).toMatch(/Near 중복/);
    expect(reviewOnlyBlockedReasonForFilter("relation")).toMatch(/Relation 그룹/);
    expect(reviewOnlyBlockedReasonForFilter("all")).toMatch(/Exact만 선택하세요/);
  });
});

describe("hasExecutableMovePreviewRows", () => {
  it("returns true when any loaded row is executable", () => {
    expect(
      hasExecutableMovePreviewRows([
        fileRow({ id: "a", proposedAction: "keep" }),
        fileRow({ id: "b", proposedAction: "move_duplicate" }),
      ]),
    ).toBe(true);
  });

  it("returns false when no executable rows in loaded page", () => {
    expect(
      hasExecutableMovePreviewRows([
        fileRow({ id: "a", proposedAction: "keep" }),
        fileRow({ id: "b", status: "excluded", proposedAction: "move_duplicate" }),
      ]),
    ).toBe(false);
  });

  it("returns false for empty rows", () => {
    expect(hasExecutableMovePreviewRows([])).toBe(false);
  });
});

describe("countExecutableMovePreviewRows", () => {
  it("counts only executable move_duplicate file rows", () => {
    expect(
      countExecutableMovePreviewRows([
        fileRow({ id: "a", proposedAction: "keep" }),
        fileRow({ id: "b", proposedAction: "move_duplicate" }),
        fileRow({ id: "c", status: "excluded", proposedAction: "move_duplicate" }),
        fileRow({ id: "d", rowKind: "group", proposedAction: "move_duplicate" }),
      ]),
    ).toBe(1);
  });

  it("returns 0 for empty rows", () => {
    expect(countExecutableMovePreviewRows([])).toBe(0);
  });
});
