import { describe, expect, it } from "vitest";
import { shouldClearRowsOnFetchFailure } from "./shellFileDockQueryPolicy";

describe("shellFileDockQueryPolicy", () => {
  it("preserves rows on timeout for initial and append fetches", () => {
    expect(shouldClearRowsOnFetchFailure(true, false)).toBe(false);
    expect(shouldClearRowsOnFetchFailure(true, true)).toBe(false);
  });

  it("clears rows only on non-timeout initial fetch failure", () => {
    expect(shouldClearRowsOnFetchFailure(false, false)).toBe(true);
    expect(shouldClearRowsOnFetchFailure(false, true)).toBe(false);
  });
});
