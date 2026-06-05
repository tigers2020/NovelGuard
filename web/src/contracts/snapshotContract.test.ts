import { describe, expect, it } from "vitest";
import { validAppSnapshot } from "./fixtures";
import { SnapshotContractError, validateAppSnapshot } from "./snapshotContract";

describe("validateAppSnapshot", () => {
  it("accepts a valid snapshot", () => {
    expect(() => validateAppSnapshot(validAppSnapshot)).not.toThrow();
  });

  it.each([
    "fileList",
    "reviewRows",
    "rows",
    "reviewRowsPage",
    "fileRows",
  ])("rejects forbidden array key %s", (key) => {
    const bad = { ...validAppSnapshot, [key]: [{ id: "x" }] };
    expect(() => validateAppSnapshot(bad)).toThrow(SnapshotContractError);
  });

  it("rejects forbidden fileList array alongside valid summary", () => {
    const bad = {
      ...validAppSnapshot,
      fileList: [],
    };
    expect(() => validateAppSnapshot(bad)).toThrow(SnapshotContractError);
  });

  it("rejects resolve snapshot missing moveReadyCount", () => {
    const resolve = { ...validAppSnapshot.work.resolve };
    delete (resolve as { moveReadyCount?: number }).moveReadyCount;
    const bad = {
      ...validAppSnapshot,
      work: { ...validAppSnapshot.work, resolve },
    };
    expect(() => validateAppSnapshot(bad)).toThrow(SnapshotContractError);
  });

  it("rejects negative reviewSignalCount", () => {
    const bad = {
      ...validAppSnapshot,
      work: {
        ...validAppSnapshot.work,
        resolve: { ...validAppSnapshot.work.resolve, reviewSignalCount: -1 },
      },
    };
    expect(() => validateAppSnapshot(bad)).toThrow(SnapshotContractError);
  });
});
