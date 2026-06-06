import { describe, expect, it } from "vitest";
import {
  FORBIDDEN_ENGLISH_UI_FALLBACKS,
  UI_FALLBACK,
  collapsedFileDockSrSummary,
} from "./uiFallbackCopy";

describe("uiFallbackCopy", () => {
  it("uses Korean copy for bridge error fallbacks", () => {
    for (const value of Object.values(UI_FALLBACK)) {
      expect(value).toMatch(/[\uAC00-\uD7A3]/);
    }
    expect(collapsedFileDockSrSummary("1.2 MB", 3)).toMatch(/[\uAC00-\uD7A3]/);
  });

  it("never includes forbidden English fallback phrases", () => {
    const values = [...Object.values(UI_FALLBACK), collapsedFileDockSrSummary("1.2 MB", 3)];
    for (const value of values) {
      for (const phrase of FORBIDDEN_ENGLISH_UI_FALLBACKS) {
        expect(value).not.toContain(phrase);
      }
    }
  });
});
