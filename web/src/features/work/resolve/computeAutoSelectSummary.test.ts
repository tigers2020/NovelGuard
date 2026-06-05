import { describe, expect, it } from "vitest";
import type { ReviewRow } from "../../../types/review";
import { computeAutoSelectSummary } from "./computeAutoSelectSummary";

function file(overrides: Partial<ReviewRow> = {}): ReviewRow {
  return {
    id: "f1",
    rowKind: "file",
    status: "unreviewed",
    type: "exact",
    name: "a.txt",
    proposedAction: "ignore",
    hasChildren: false,
    groupId: "g1",
    sizeBytes: 100,
    ...overrides,
  };
}

describe("computeAutoSelectSummary", () => {
  it("counts mixed exact/near/relation unreviewed files", () => {
    const rows = [
      file({ id: "e1", type: "exact", groupId: "g1" }),
      file({ id: "n1", type: "near", groupId: "g2" }),
      file({ id: "r1", type: "relation", groupId: "g3" }),
    ];
    const summary = computeAutoSelectSummary(rows, {
      filteredCount: 3,
      loadedFileRowCount: 3,
    });
    expect(summary.unreviewedCount).toBe(3);
    expect(summary.exactCount).toBe(1);
    expect(summary.nearCount).toBe(1);
    expect(summary.relationCount).toBe(1);
    expect(summary.keeperCount).toBe(3);
    expect(summary.moveCandidateCount).toBe(0);
  });

  it("computes K/M for two files in one group", () => {
    const rows = [
      file({ id: "a", groupId: "g1", sizeBytes: 200 }),
      file({ id: "b", groupId: "g1", sizeBytes: 100 }),
    ];
    const summary = computeAutoSelectSummary(rows, {
      filteredCount: 2,
      loadedFileRowCount: 2,
    });
    expect(summary.unreviewedCount).toBe(2);
    expect(summary.keeperCount).toBe(1);
    expect(summary.moveCandidateCount).toBe(1);
  });

  it("sets capped when unreviewed > 500", () => {
    const rows = Array.from({ length: 501 }, (_, index) =>
      file({ id: `f${index}`, groupId: `g${index}` }),
    );
    const summary = computeAutoSelectSummary(rows, {
      filteredCount: 501,
      loadedFileRowCount: 501,
    });
    expect(summary.capped).toBe(true);
    expect(summary.mutationTargetCount).toBe(500);
  });

  it("sets partialLoad when loaded < filtered", () => {
    const summary = computeAutoSelectSummary([file()], {
      filteredCount: 10,
      loadedFileRowCount: 1,
    });
    expect(summary.partialLoad).toBe(true);
  });

  it("excludes conflict and group rows", () => {
    const rows = [
      file({ id: "ok" }),
      file({ id: "conf", status: "conflict" }),
      { ...file({ id: "grp" }), rowKind: "group" as const },
    ];
    const summary = computeAutoSelectSummary(rows, {
      filteredCount: 1,
      loadedFileRowCount: 2,
    });
    expect(summary.unreviewedCount).toBe(1);
  });
});
