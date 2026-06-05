import { describe, expect, it } from "vitest";
import { FORBIDDEN_PREVIEW_CTA_PHRASES, previewCtaLabel } from "./previewCtaCopy";

describe("previewCtaLabel", () => {
  it("uses count in exact filter label when n > 0", () => {
    expect(
      previewCtaLabel({ filter: "exact", executableCount: 1, moveReadyCount: 5 }),
    ).toBe("Exact 5건 이동 계획 미리보기");
  });

  it("uses generic exact label when n is 0", () => {
    expect(previewCtaLabel({ filter: "exact", executableCount: 0 })).toBe(
      "Exact 중복 이동 계획 미리보기",
    );
  });

  it("never uses forbidden destructive phrases", () => {
    const label = previewCtaLabel({ filter: "exact", executableCount: 3 });
    for (const phrase of FORBIDDEN_PREVIEW_CTA_PHRASES) {
      expect(label).not.toContain(phrase);
    }
  });
});
