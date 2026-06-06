import { describe, expect, it } from "vitest";
import {
  LARGE_LIBRARY_THRESHOLD,
  shouldLoadFirstPageOnly,
} from "./resolveLargeLibraryPolicy";

describe("resolveLargeLibraryPolicy", () => {
  it("uses 500 as the large-library threshold", () => {
    expect(LARGE_LIBRARY_THRESHOLD).toBe(500);
  });

  it("skips load-all preload when totalFiltered exceeds threshold", () => {
    expect(shouldLoadFirstPageOnly(501)).toBe(true);
    expect(shouldLoadFirstPageOnly(7000)).toBe(true);
  });

  it("allows load-all preload at or below threshold", () => {
    expect(shouldLoadFirstPageOnly(500)).toBe(false);
    expect(shouldLoadFirstPageOnly(120)).toBe(false);
  });
});
