import { describe, expect, it } from "vitest";
import {
  resolveAutoApprovePhaseLabel,
  resolveAutoApproveStatusLabel,
} from "./resolveAutoApproveJobCopy";

describe("resolveAutoApproveJobCopy", () => {
  it("maps status labels", () => {
    expect(resolveAutoApproveStatusLabel("idle")).toContain("준비");
    expect(resolveAutoApproveStatusLabel("running")).toContain("진행");
    expect(resolveAutoApproveStatusLabel("complete")).toContain("완료");
    expect(resolveAutoApproveStatusLabel("error")).toContain("실패");
    expect(resolveAutoApproveStatusLabel("cancelled")).toContain("취소");
  });

  it("maps phase labels", () => {
    expect(resolveAutoApprovePhaseLabel("idle")).toBeNull();
    expect(resolveAutoApprovePhaseLabel("summarize")).toBe("summarize");
    expect(resolveAutoApprovePhaseLabel("persist")).toBe("persist");
  });
});
