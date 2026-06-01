import { describe, expect, it } from "vitest";
import {
  maxRenderedRowSlots,
  isNearScrollEnd,
  filterPaginateLatencyBudgetMs,
} from "./virtualWindow";

describe("virtualWindow", () => {
  it("caps rendered slots to overscan window", () => {
    expect(maxRenderedRowSlots({ overscan: 8 })).toBe(19);
  });

  it("detects near-end scroll", () => {
    expect(
      isNearScrollEnd({ scrollTop: 880, clientHeight: 100, scrollHeight: 1000, threshold: 120 }),
    ).toBe(true);
    expect(
      isNearScrollEnd({ scrollTop: 100, clientHeight: 100, scrollHeight: 1000, threshold: 120 }),
    ).toBe(false);
  });

  it("documents filter+paginate budget", () => {
    expect(filterPaginateLatencyBudgetMs()).toBe(50);
  });
});
