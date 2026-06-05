import { describe, expect, it } from "vitest";
import { FORBIDDEN_PREVIEW_CTA_PHRASES, previewCtaLabel } from "./previewCtaCopy";

describe("previewCtaLabel", () => {
  it("uses Exact N건 label when executable count is positive on exact filter", () => {
    expect(previewCtaLabel({ filter: "exact", executableCount: 3 })).toBe(
      "Exact 3건 이동 계획 미리보기",
    );
  });

  it("prefers moveReadyCount over executableCount when both provided", () => {
    expect(
      previewCtaLabel({ filter: "exact", executableCount: 2, moveReadyCount: 5 }),
    ).toBe("Exact 5건 이동 계획 미리보기");
  });

  it("uses Exact 중복 label when exact filter has zero executables", () => {
    expect(previewCtaLabel({ filter: "exact", executableCount: 0 })).toBe(
      "Exact 중복 이동 계획 미리보기",
    );
  });

  it("uses generic label for non-exact filters (batch bar fallback)", () => {
    expect(previewCtaLabel({ filter: "near", executableCount: 3 })).toBe("이동 계획 미리보기");
    expect(previewCtaLabel({ filter: "all", executableCount: 3 })).toBe("이동 계획 미리보기");
  });

  it("never includes forbidden apply-ish phrases", () => {
    const filters = ["exact", "near", "relation", "all"] as const;
    for (const filter of filters) {
      const label = previewCtaLabel({ filter, executableCount: 2 });
      for (const phrase of FORBIDDEN_PREVIEW_CTA_PHRASES) {
        expect(label).not.toContain(phrase);
      }
    }
  });
});
